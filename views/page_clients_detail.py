"""고객 상세 — 기본 정보 + 탭 (상담이력/리마인드/보장분석)"""
import logging

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

    col_edit, col_del = st.columns(2)
    if col_edit.button("수정", use_container_width=True):
        st.session_state.clients_view = "edit"
        st.session_state.edit_client = client
        st.rerun()
    if col_del.button("고객 삭제", use_container_width=True):
        st.session_state[f"confirm_del_client_{client_id}"] = True
        st.rerun()

    # 삭제 확인 다이얼로그 (버튼 아래 인라인)
    if st.session_state.get(f"confirm_del_client_{client_id}"):
        _render_client_delete_confirm(sb, client_id, fc_id)

    st.markdown("---")

    from views.page_clients_contact import render_contact_logs, render_new_contact
    grade = client.get("prospect_grade", "")
    is_existing_client = grade in ("VIP", "S")

    if is_existing_client:
        tab_timeline, tab_contract, tab_contact, tab_remind, tab_analysis = st.tabs(
            ["⏳ 타임라인", "📄 계약정보", "📝 상담이력", "🔔 리마인드", "📊 보장분석"])
        with tab_contract:
            from views.page_clients_contracts import render_contracts
            render_contracts(sb, client_id)
    else:
        tab_timeline, tab_contact, tab_remind, tab_analysis = st.tabs(
            ["⏳ 타임라인", "📝 상담이력", "🔔 리마인드", "📊 보장분석"])

    with tab_timeline:
        from views.page_clients_timeline import render_timeline
        render_timeline(sb, client_id, client["name"])
    with tab_contact:
        render_contact_logs(sb, client_id)
        render_new_contact(sb, client_id)
    with tab_remind:
        from views.page_clients_remind import render_reminder_section
        render_reminder_section(sb, fc_id=fc_id, client_id=client_id)
    with tab_analysis:
        _render_analysis_history(sb, fc_id, client["name"])


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
                    from utils.security import validate_storage_path
                    if not validate_storage_path(r["excel_path"], fc_id):
                        continue
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


def _render_client_delete_confirm(sb, client_id: str, fc_id: str):
    """삭제 확인 다이얼로그. 고객 + FK 참조 레코드 순차 삭제.
    참조 테이블이 DB에 없는 경우(마이그레이션 미적용) PGRST205 에러는 무시하고 진행.
    """
    confirm_key = f"confirm_del_client_{client_id}"
    st.warning("고객 정보와 모든 상담 이력, 리마인드, 계약, 보장분석 이력이 삭제됩니다. 계속하시겠습니까?")
    col_y, col_n = st.columns(2)
    if col_y.button("삭제 확인", type="primary", use_container_width=True, key=f"del_yes_{client_id}"):
        # RPC 우선 — 트랜잭션 원자성 보장 (017 마이그레이션 적용 시)
        try:
            sb.rpc("delete_client", {
                "p_client_id": client_id,
                "p_fc_id": fc_id,
            }).execute()
        except Exception as rpc_err:
            # RPC 미등록/권한실패/참조테이블 미생성 → 직접 순차 delete로 폴백
            logging.warning("delete_client RPC 실패, 직접 삭제로 폴백")
            for tbl in ("fp_reminders", "client_contracts", "contact_logs"):
                _safe_table_delete(sb, tbl, "client_id", client_id, fc_id)
            # 마지막으로 clients 본체 삭제
            try:
                sb.table("clients").delete().eq("id", client_id).eq("fc_id", fc_id).execute()
            except Exception as e:
                logging.error("clients 삭제 오류: %s", type(e).__name__)
                st.error(safe_error("삭제", e))
                return
        st.session_state.pop(confirm_key, None)
        st.session_state.clients_view = "list"
        st.rerun()
    if col_n.button("취소", use_container_width=True, key=f"del_no_{client_id}"):
        st.session_state.pop(confirm_key, None)
        st.rerun()


def _safe_table_delete(sb, table: str, key_col: str, key_val: str, fc_id: str):
    """테이블 존재하면 삭제, 없으면(PGRST205) 무시."""
    try:
        sb.table(table).delete().eq(key_col, key_val).eq("fc_id", fc_id).execute()
    except Exception as e:
        err_str = str(e)
        if "PGRST205" in err_str or "Could not find the table" in err_str:
            logging.info("%s 미생성 — 건너뜀", table)
        else:
            # 다른 에러는 경고만 찍고 계속 (부분 삭제 허용)
            logging.warning("%s 삭제 실패 — 계속 진행: %s", table, type(e).__name__)



def _sb():
    from utils.supabase_client import get_supabase_client
    return get_supabase_client()
