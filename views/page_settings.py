"""설정 페이지"""
import streamlit as st
from auth import get_current_user_id, is_admin
from utils.helpers import safe_error
from utils.supabase_client import get_supabase_client


def render():
    st.header("설정")

    sb = get_supabase_client()
    user_id = get_current_user_id()
    settings = _load_settings(sb, user_id)

    with st.expander("프로필 설정", expanded=True):
        with st.form("settings_form"):
            display_name = st.text_input(
                "이름",
                value=settings.get("display_name", ""),
            )
            company = st.text_input(
                "소속",
                value=settings.get("company", "신한라이프"),
            )
            mode = st.selectbox(
                "영업 모드",
                options=["pioneer", "referral", "both"],
                format_func=lambda x: {"pioneer": "개척", "referral": "소개", "both": "병행"}[x],
                index=["pioneer", "referral", "both"].index(settings.get("mode", "pioneer")),
            )
            if st.form_submit_button("저장", use_container_width=True, type="primary"):
                _save_settings(sb, user_id, display_name, company, mode)

    with st.expander("📦 상품 관리"):
        from views.page_settings_products import render_product_section
        render_product_section()

    with st.expander("유입경로 관리"):
        _render_source_categories(sb, user_id)

    with st.expander("💾 데이터 관리"):
        st.caption("고객 데이터를 CSV로 가져오거나 내보낼 수 있습니다.")
        csv_file = st.file_uploader("CSV 가져오기", type=["csv"], key="settings_csv")
        if csv_file and csv_file.size > 10 * 1024 * 1024:
            st.error("파일 크기는 10MB 이하만 가능합니다.")
            csv_file = None
        if csv_file and st.button("가져오기 시작", type="primary"):
            from services.migration import migrate_clients_csv
            with st.spinner("마이그레이션 중..."):
                result = migrate_clients_csv(csv_file.read())
            st.success(f"{result['success']}명 가져오기 완료")
            if result["errors"]:
                with st.expander(f"오류 {len(result['errors'])}건"):
                    for e in result["errors"]:
                        st.caption(e)

    if is_admin():
        st.markdown("---")
        from views.page_settings_admin import render_admin_section
        render_admin_section(sb)

    st.markdown("---")
    st.caption(f"FCPilot v1.0.0 · {user_id[:8]}... · 역할: {settings.get('role', 'user')}")


_DEFAULT_CATEGORIES = ["DB고객", "개인(지인)", "개척", "소개", "기타"]


def _render_source_categories(sb, user_id: str):
    """유입경로 카테고리 관리 — 드래그로 순서 변경, 고객관리 필터 자동 연동"""
    from streamlit_sortables import sort_items
    st.subheader("유입경로 카테고리")
    st.caption("드래그로 순서 변경 · 저장하면 고객관리 필터에 즉시 반영")

    try:
        res = sb.table("users_settings").select("source_categories").eq("id", user_id).execute()
        cats = (res.data[0].get("source_categories") if res.data else None) or list(_DEFAULT_CATEGORIES)
    except Exception:
        cats = list(_DEFAULT_CATEGORIES)

    sorted_cats = sort_items(cats, direction="vertical", key="source_cat_sort")

    # 항목 추가/삭제
    with st.form("cat_add_del"):
        col_add, col_del = st.columns(2)
        with col_add:
            new_cat = st.text_input("추가", placeholder="새 항목 입력")
        with col_del:
            del_cat = st.selectbox("삭제", ["(선택)"] + sorted_cats, label_visibility="visible")
        c1, c2, c3 = st.columns(3)
        save = c1.form_submit_button("저장", type="primary", use_container_width=True)
        add = c2.form_submit_button("항목 추가", use_container_width=True)
        delete = c3.form_submit_button("항목 삭제", use_container_width=True)

    if save:
        _save_categories(sb, user_id, sorted_cats)
        st.rerun()
    if add and new_cat.strip():
        if new_cat.strip() not in sorted_cats:
            _save_categories(sb, user_id, sorted_cats + [new_cat.strip()])
        else:
            st.warning("이미 존재하는 항목입니다.")
        st.rerun()
    if delete and del_cat != "(선택)":
        _save_categories(sb, user_id, [c for c in sorted_cats if c != del_cat])
        st.rerun()

    if st.button("기본값 초기화", use_container_width=True):
        _save_categories(sb, user_id, list(_DEFAULT_CATEGORIES))
        st.rerun()


def _save_categories(sb, user_id: str, categories: list):
    try:
        sb.table("users_settings").upsert({
            "id": user_id,
            "source_categories": categories,
        }).execute()
        st.session_state.pop(f"source_cats_{user_id}", None)  # 고객관리 필터 캐시 무효화
        st.success("저장됨 — 고객관리 필터에 즉시 반영됩니다.")
    except Exception as e:
        st.error(safe_error("저장", e))


def _load_settings(sb, user_id: str) -> dict:
    """사용자 설정 로드"""
    try:
        res = sb.table("users_settings").select("*").eq("id", user_id).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        st.warning(safe_error("설정 로드", e))
    return {}


def _save_settings(sb, user_id: str, display_name: str, company: str, mode: str):
    """사용자 설정 저장"""
    try:
        sb.table("users_settings").upsert({
            "id": user_id,
            "display_name": display_name,
            "company": company,
            "mode": mode,
        }).execute()
        st.session_state.pop("cached_sales_mode", None)  # 영업 모드 캐시 무효화
        st.success("설정이 저장되었습니다.")
    except Exception as e:
        st.error(safe_error("저장", e))
