"""고객 상세 — 기본 정보 + 탭 (상담이력/리마인드/보장분석/삭제)"""
import streamlit as st
from auth import get_current_user_id
from services.crypto import decrypt_phone
from utils.helpers import safe_error


def render_detail():
    sb = _sb()
    client_id = st.session_state.get("selected_client_id")

    if st.button("← 목록으로"):
        st.session_state.clients_view = "list"
        st.rerun()

    fc_id = get_current_user_id()
    try:
        res = sb.table("clients").select("*").eq("id", client_id).eq("fc_id", fc_id).single().execute()
        client = res.data
    except Exception as e:
        st.error(safe_error("조회", e))
        return

    if not client:
        st.warning("고객 정보를 찾을 수 없습니다.")
        return

    st.subheader(client["name"])
    col1, col2, col3 = st.columns(3)
    col1.metric("등급", client.get("prospect_grade", "-"))
    age_display = client.get("age_group") or (f"{client['age']}세" if client.get("age") else "-")
    col2.metric("나이", age_display)
    col3.metric("성별", {"M": "남", "F": "여"}.get(client.get("gender"), "-"))

    phone = ""
    if client.get("phone_encrypted"):
        try:
            phone = decrypt_phone(client["phone_encrypted"])
        except Exception:
            phone = "(복호화 실패)"
    st.text(f"연락처: {phone if phone else '미등록'}")
    st.text(f"직업: {client.get('occupation', '-')}")
    st.text(f"주소: {client.get('address', '-')}")
    st.text(f"유입경로: {client.get('db_source', '-')}")
    if client.get("memo"):
        st.text(f"메모: {client['memo']}")

    if st.button("수정", use_container_width=True):
        st.session_state.clients_view = "edit"
        st.session_state.edit_client = client
        st.rerun()

    st.markdown("---")

    from views.page_clients_contact import render_contact_logs, render_new_contact
    tab_contact, tab_remind, tab_analysis, tab_del = st.tabs(["📝 상담이력", "🔔 리마인드", "📊 보장분석", "🗑️ 삭제"])
    with tab_contact:
        render_contact_logs(sb, client_id)
        render_new_contact(sb, client_id)
    with tab_remind:
        _render_reminder_section(sb, fc_id=fc_id, client_id=client_id)
    with tab_analysis:
        _render_analysis_history(sb, fc_id, client["name"])
    with tab_del:
        _render_client_delete(sb, client_id)


def _render_analysis_history(sb, fc_id: str, client_name: str):
    st.subheader("보장분석 이력")
    try:
        records = (sb.table("analysis_records").select("*")
                   .eq("fc_id", fc_id).ilike("client_name", client_name)
                   .order("created_at", desc=True).limit(10).execute().data or [])
    except Exception:
        records = []
    if not records:
        col_info, col_btn = st.columns([3, 1])
        col_info.caption("보장분석 이력이 없습니다.")
        if col_btn.button("보장분석 하기", use_container_width=True):
            st.session_state._nav_to = "📊 보장분석"
            st.rerun()
        return
    for r in records:
        created = r.get("created_at", "")[:10]
        summary = r.get("result_summary") or {}
        contracts = r.get("contract_count", 0)
        gender = summary.get("성별", "")
        age = summary.get("나이", "")
        with st.expander(f"📊 {created} | 계약 {contracts}건 {('| '+gender) if gender else ''} {(str(age)+'세') if age else ''}"):
            st.caption(f"고객명: {r.get('client_name','')}")
            st.caption(f"분석일: {created}")
            if r.get("excel_path"):
                try:
                    from utils.db_admin import get_admin_client
                    excel_bytes = get_admin_client().storage.from_("analysis-excel").download(r["excel_path"])
                    st.download_button(
                        "📥 엑셀 다운로드",
                        data=excel_bytes,
                        file_name=f"보장분석_{r.get('client_name','')}_{created}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_analysis_{r['id']}",
                        use_container_width=True,
                    )
                except Exception:
                    pass
            if st.button("보장분석 다시 실행", key=f"rerun_analysis_{r['id']}", use_container_width=True):
                st.session_state._nav_to = "📊 보장분석"
                st.rerun()


def _render_client_delete(sb, client_id: str):
    fc_id = get_current_user_id()
    confirm_key = f"confirm_del_client_{client_id}"
    if st.session_state.get(confirm_key):
        st.warning("고객 정보와 모든 상담 이력이 삭제됩니다. 계속하시겠습니까?")
        col_y, col_n = st.columns(2)
        if col_y.button("삭제 확인", type="primary", use_container_width=True):
            try:
                sb.table("contact_logs").delete().eq("client_id", client_id).eq("fc_id", fc_id).execute()
                sb.table("clients").delete().eq("id", client_id).eq("fc_id", fc_id).execute()
                st.session_state.pop(confirm_key, None)
                st.session_state.clients_view = "list"
                st.rerun()
            except Exception as e:
                st.error(safe_error("삭제", e))
        if col_n.button("취소", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    else:
        if st.button("고객 삭제", use_container_width=True):
            st.session_state[confirm_key] = True
            st.rerun()


def _render_reminder_section(sb, fc_id: str, client_id: str):
    from services.fp_reminder_service import (
        get_client_reminders, create_reminder, complete_reminder,
        cancel_reminder, purposes, RESULT_OPTIONS, RESULT_MAP,
    )
    from views.page_settings_products import get_active_products

    st.subheader("리마인드")

    reminders = get_client_reminders(fc_id, client_id)
    pending = [r for r in reminders if r.get("status") == "pending"]
    done = [r for r in reminders if r.get("status") in ("completed", "cancelled")]

    tab_pending, tab_done = st.tabs([
        f"예정 ({len(pending)})",
        f"완료/취소 ({len(done)})",
    ])

    with tab_pending:
        if pending:
            for r in pending:
                rd = r.get("reminder_date") or ""
                icon = "🔴" if rd and rd < str(__import__("datetime").date.today()) else "🟡"
                complete_key = f"r_complete_{r['id']}"

                col_r, col_done, col_cancel = st.columns([5, 1, 1])
                col_r.caption(f"{icon} {rd or '미정'} | {r.get('purpose','')} | {(r.get('memo') or '')[:30]}")
                if col_done.button("완료", key=f"r_done_{r['id']}", use_container_width=True):
                    st.session_state[complete_key] = True
                    st.rerun()
                if col_cancel.button("취소", key=f"r_cancel_{r['id']}", use_container_width=True):
                    cancel_reminder(fc_id, r["id"])
                    st.rerun()

                if st.session_state.get(complete_key):
                    with st.form(f"client_complete_{r['id']}"):
                        result = st.selectbox(
                            "결과", [k for k, _ in RESULT_OPTIONS],
                            format_func=lambda x: RESULT_MAP.get(x, x),
                            key=f"cr_result_{r['id']}",
                        )
                        result_memo = st.text_area(
                            "FC 후기", placeholder="결과 메모, 실패 사유 등",
                            key=f"cr_memo_{r['id']}",
                        )
                        c1, c2 = st.columns(2)
                        if c1.form_submit_button("완료 저장", type="primary", use_container_width=True):
                            complete_reminder(fc_id, r["id"], result, result_memo)
                            st.session_state.pop(complete_key, None)
                            st.rerun()
                        if c2.form_submit_button("취소", use_container_width=True):
                            st.session_state.pop(complete_key, None)
                            st.rerun()
        else:
            st.caption("예정된 리마인드가 없습니다.")

        with st.expander("➕ 리마인드 등록"):
            with st.form("reminder_form"):
                r_date = st.date_input("예정일")
                r_purpose = st.selectbox("상담 목적", purposes())
                products = get_active_products(sb, fc_id)
                prod_map = {p["name"]: p["id"] for p in products}
                selected = st.multiselect("제안 상품", list(prod_map.keys())) if products else []
                r_memo = st.text_input("메모", placeholder="선택 사항")
                if st.form_submit_button("등록", type="primary", use_container_width=True):
                    pid_list = [prod_map[n] for n in selected if n in prod_map] or None
                    ok = create_reminder(fc_id, client_id, str(r_date), r_purpose, pid_list, r_memo)
                    if ok:
                        st.success("리마인드가 등록되었습니다.")
                        st.rerun()
                    else:
                        st.error("등록 실패")

    with tab_done:
        if done:
            for r in done:
                status_icon = "✅" if r.get("status") == "completed" else "❌"
                rd = r.get("reminder_date") or "미정"
                result_label = RESULT_MAP.get(r.get("result", ""), "")
                completed = (r.get("completed_at") or "")[:10]
                result_memo = r.get("result_memo", "")

                info = f"{status_icon} {rd} | {r.get('purpose','')}"
                if result_label:
                    info += f" | {result_label}"
                if completed:
                    info += f" | 완료: {completed}"
                st.caption(info)
                if result_memo:
                    st.caption(f"   FC 후기: {result_memo}")
        else:
            st.caption("완료/취소된 리마인드가 없습니다.")


def _sb():
    from utils.supabase_client import get_supabase_client
    return get_supabase_client()
