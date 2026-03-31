"""상품 관리 섹션 — 설정 탭에서 호출 (이름 + 카테고리만)"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client

_CATEGORIES = ["종신보험", "건강보험", "연금보험", "저축보험", "변액보험", "기타"]


def get_active_products(sb, fc_id: str) -> list[dict]:
    """활성 상품 목록 반환 — 다른 탭에서도 호출 가능"""
    try:
        return sb.table("fp_products").select("id, name, category").eq("fc_id", fc_id).eq("is_active", True).order("name").execute().data or []
    except Exception:
        return []


def render_product_section():
    st.subheader("상품 관리")
    st.caption("상담 기록 시 '제안 상품' 드롭다운에 표시됩니다.")

    sb = get_supabase_client()
    fc_id = get_current_user_id()

    try:
        products = sb.table("fp_products").select("*").eq("fc_id", fc_id).order("name").execute().data or []
    except Exception as e:
        st.error(f"조회 실패: {e}")
        products = []

    for p in products:
        _render_card(sb, p)
    if not products:
        st.caption("등록된 상품이 없습니다.")

    st.divider()
    _render_add_form(sb, fc_id)


def _render_card(sb, p: dict):
    pid = p["id"]
    edit_key = f"prod_edit_{pid}"
    del_key = f"prod_del_{pid}"
    icon = "🟢" if p.get("is_active", True) else "⚫"

    col_name, col_cat, col_e, col_d = st.columns([3, 2, 1, 1])
    col_name.markdown(f"{icon} **{p['name']}**")
    col_cat.caption(p.get("category", "기타"))

    if col_e.button("수정", key=f"e_{pid}", use_container_width=True):
        st.session_state[edit_key] = not st.session_state.get(edit_key, False)
        st.rerun()

    if st.session_state.get(del_key):
        c1, c2 = st.columns(2)
        if c1.button("삭제 확인", key=f"dok_{pid}", type="primary", use_container_width=True):
            try:
                sb.table("fp_products").delete().eq("id", pid).execute()
                st.session_state.pop(del_key, None)
                st.session_state.pop(edit_key, None)
                st.rerun()
            except Exception as e:
                st.error(f"삭제 실패: {e}")
        if c2.button("취소", key=f"dno_{pid}", use_container_width=True):
            st.session_state.pop(del_key, None)
            st.rerun()
    else:
        if col_d.button("삭제", key=f"d_{pid}", use_container_width=True):
            st.session_state[del_key] = True
            st.rerun()

    if st.session_state.get(edit_key):
        with st.form(f"edit_{pid}"):
            name = st.text_input("상품명", value=p.get("name", ""))
            cat_idx = _CATEGORIES.index(p["category"]) if p.get("category") in _CATEGORIES else len(_CATEGORIES) - 1
            category = st.selectbox("카테고리", _CATEGORIES, index=cat_idx)
            is_active = st.checkbox("활성 상품", value=p.get("is_active", True))
            if st.form_submit_button("저장", use_container_width=True, type="primary"):
                if not name.strip():
                    st.error("상품명을 입력하세요.")
                    return
                try:
                    sb.table("fp_products").update({
                        "name": name.strip(), "category": category,
                        "is_active": is_active, "updated_at": "now()",
                    }).eq("id", pid).execute()
                    st.session_state.pop(edit_key, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")


def _render_add_form(sb, fc_id: str):
    st.markdown("**새 상품 추가**")
    with st.form("add_product"):
        name = st.text_input("상품명", placeholder="예: 신한 THE건강보험")
        category = st.selectbox("카테고리", _CATEGORIES)
        if st.form_submit_button("추가", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("상품명을 입력하세요.")
                return
            try:
                sb.table("fp_products").insert({
                    "fc_id": fc_id, "name": name.strip(),
                    "category": category, "is_active": True,
                }).execute()
                st.rerun()
            except Exception as e:
                st.error(f"등록 실패: {e}")
