"""고객 상세 — 리마인드 섹션 (예정/완료 탭 + 등록)"""
import streamlit as st


def render_reminder_section(sb, fc_id: str, client_id: str):
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
                            res = complete_reminder(fc_id, r["id"], result, result_memo)
                            if res is True:
                                st.session_state.pop(complete_key, None)
                                st.rerun()
                            else:
                                st.error(f"저장 실패: {res}")
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
            from services.fp_reminder_service import delete_reminder
            for r in done:
                status_icon = "✅" if r.get("status") == "completed" else "❌"
                rd = r.get("reminder_date") or "미정"
                result_label = RESULT_MAP.get(r.get("result", ""), "")
                completed = (r.get("completed_at") or "")[:10]
                result_memo = r.get("result_memo", "")

                col_info, col_del = st.columns([5, 1])
                info = f"{status_icon} {rd} | {r.get('purpose','')}"
                if result_label:
                    info += f" | {result_label}"
                if completed:
                    info += f" | 완료: {completed}"
                col_info.caption(info)
                if result_memo:
                    col_info.caption(f"   FC 후기: {result_memo}")
                del_key = f"del_client_{r['id']}"
                if st.session_state.get(del_key):
                    c1, c2 = col_del.columns(2)
                    if c1.button("확인", key=f"cdc_y_{r['id']}", use_container_width=True):
                        delete_reminder(fc_id, r["id"])
                        st.session_state.pop(del_key, None)
                        st.rerun()
                    if c2.button("취소", key=f"cdc_n_{r['id']}", use_container_width=True):
                        st.session_state.pop(del_key, None)
                        st.rerun()
                else:
                    def _tog_del(dk):
                        st.session_state[dk] = True
                    col_del.button("삭제", key=f"cd_del_{r['id']}",
                                   use_container_width=True, on_click=_tog_del, args=(del_key,))
        else:
            st.caption("완료/취소된 리마인드가 없습니다.")
