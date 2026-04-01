"""상담이력 CRUD + 새 상담 기록"""
import streamlit as st
from auth import get_current_user_id
from utils.helpers import safe_error

TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]


def render_contact_logs(sb, client_id: str):
    fc_id = get_current_user_id()
    st.subheader("상담 이력")
    try:
        res = sb.table("contact_logs").select("*").eq("client_id", client_id).eq("fc_id", fc_id).order("created_at", desc=True).limit(50).execute()
        logs = res.data or []
    except Exception as e:
        st.error(safe_error("이력 조회", e))
        return

    if not logs:
        st.caption("상담 이력이 없습니다.")
        return

    for i, log in enumerate(logs):
        method = log.get("touch_method", "") or "기타"
        date_str = log.get("created_at", "")[:10]
        label = f"{date_str} | {method}"
        with st.expander(label, expanded=(i == 0)):
            st.write(log.get("memo", ""))
            if log.get("proposed_product_ids"):
                try:
                    from views.page_settings_products import get_active_products
                    all_prods = {p["id"]: p["name"] for p in get_active_products(sb, fc_id)}
                    names = [all_prods.get(pid, pid[:8]) for pid in log["proposed_product_ids"]]
                    st.caption(f"제안 상품: {', '.join(names)}")
                except Exception:
                    pass
            if log.get("next_action"):
                st.caption(f"다음 할 일: {log['next_action']}")
            if log.get("next_date"):
                st.caption(f"예정일: {log['next_date']}")

            edit_log_key = f"edit_log_{log['id']}"
            confirm_key = f"confirm_del_log_{log['id']}"
            if st.session_state.get(edit_log_key):
                with st.form(f"edit_log_form_{log['id']}"):
                    cur_method = log.get("touch_method", "") or "기타"
                    idx = TOUCH_OPTIONS.index(cur_method) if cur_method in TOUCH_OPTIONS else 0
                    new_method = st.selectbox("연락 방식", TOUCH_OPTIONS, index=idx)
                    new_memo = st.text_area("상담 내용", value=log.get("memo") or "")
                    ec1, ec2 = st.columns(2)
                    if ec1.form_submit_button("저장", type="primary", use_container_width=True):
                        try:
                            sb.table("contact_logs").update({
                                "touch_method": new_method, "memo": new_memo,
                            }).eq("id", log["id"]).eq("fc_id", fc_id).execute()
                            st.session_state.pop(edit_log_key, None)
                            st.rerun()
                        except Exception as e:
                            st.error(safe_error("저장", e))
                    if ec2.form_submit_button("취소", use_container_width=True):
                        st.session_state.pop(edit_log_key, None)
                        st.rerun()
            elif st.session_state.get(confirm_key):
                st.warning("이 상담 기록을 삭제하시겠습니까?")
                col_y, col_n = st.columns(2)
                if col_y.button("삭제 확인", key=f"log_del_yes_{log['id']}", type="primary"):
                    try:
                        sb.table("contact_logs").delete().eq("id", log["id"]).eq("fc_id", fc_id).execute()
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(safe_error("삭제", e))
                if col_n.button("취소", key=f"log_del_no_{log['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
            else:
                bc1, bc2 = st.columns(2)
                if bc1.button("수정", key=f"edit_log_btn_{log['id']}", use_container_width=True):
                    st.session_state[edit_log_key] = True
                    st.rerun()
                if bc2.button("삭제", key=f"del_log_{log['id']}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()


def render_new_contact(sb, client_id: str):
    st.subheader("상담 기록 추가")
    fc_id = get_current_user_id()

    try:
        from views.page_settings_products import get_active_products
        products = get_active_products(sb, fc_id)
    except Exception:
        products = []
    prod_map = {p["name"]: p["id"] for p in products}

    with st.form("new_contact"):
        touch_method = st.selectbox("연락 방식", TOUCH_OPTIONS)
        memo = st.text_area("상담 내용", placeholder="상담 내용을 입력하세요")
        if products:
            selected_prods = st.multiselect("제안 상품 (복수 선택 가능)", list(prod_map.keys()))
        else:
            selected_prods = []
            st.caption("등록된 상품이 없습니다. 설정 > 상품 관리에서 추가하세요.")
        next_action = st.text_input("다음 할 일", placeholder="선택 사항")
        next_date = st.date_input("예정일", value=None)

        if st.form_submit_button("저장", use_container_width=True, type="primary"):
            if not memo:
                st.error("상담 내용을 입력해주세요.")
            else:
                try:
                    prod_ids = [prod_map[n] for n in selected_prods if n in prod_map] or None
                    sb.table("contact_logs").insert({
                        "fc_id": fc_id,
                        "client_id": client_id,
                        "touch_method": touch_method,
                        "memo": memo,
                        "proposed_product_ids": prod_ids,
                        "next_action": next_action,
                        "next_date": str(next_date) if next_date else None,
                    }).execute()
                    st.success("저장되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(safe_error("저장", e))
