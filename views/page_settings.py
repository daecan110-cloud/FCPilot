"""설정 페이지"""
import streamlit as st
from auth import get_current_user_id, is_admin
from utils.supabase_client import get_supabase_client


def render():
    st.header("설정")

    sb = get_supabase_client()
    user_id = get_current_user_id()

    # 기존 설정 로드
    settings = _load_settings(sb, user_id)

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

    st.divider()

    # 상품 관리
    from views.page_settings_products import render_product_section
    render_product_section()

    st.divider()

    # 유입경로 카테고리 관리
    _render_source_categories(sb, user_id)

    st.divider()

    # 데이터 관리 (UX-05: CSV 가져오기/내보내기)
    with st.expander("데이터 관리"):
        st.caption("고객 데이터를 CSV로 가져오거나 내보낼 수 있습니다.")
        csv_file = st.file_uploader("CSV 가져오기", type=["csv"], key="settings_csv")
        if csv_file and st.button("가져오기 시작", type="primary"):
            from services.migration import migrate_clients_csv
            with st.spinner("마이그레이션 중..."):
                result = migrate_clients_csv(csv_file.read())
            st.success(f"{result['success']}명 가져오기 완료")
            if result["errors"]:
                with st.expander(f"오류 {len(result['errors'])}건"):
                    for e in result["errors"]:
                        st.caption(e)

    st.caption(f"FCPilot v1.0.0 | User ID: {user_id[:8]}... | 역할: {settings.get('role', 'user')}")

    # Admin 전용 섹션
    if is_admin():
        from views.page_settings_admin import render_admin_section
        render_admin_section(sb)


_DEFAULT_CATEGORIES = ["DB고객", "개인(지인)", "개척", "소개", "기타"]


def _render_source_categories(sb, user_id: str):
    """유입경로 카테고리 관리 — 순서 변경 가능, 고객관리 필터 자동 연동"""
    import pandas as pd
    st.subheader("유입경로 카테고리")
    st.caption("순서 숫자를 바꾸면 필터 순서도 변경 · 저장하면 고객관리 필터에 즉시 반영")

    try:
        res = sb.table("users_settings").select("source_categories").eq("id", user_id).execute()
        cats = (res.data[0].get("source_categories") if res.data else None) or list(_DEFAULT_CATEGORIES)
    except Exception:
        cats = list(_DEFAULT_CATEGORIES)

    df = pd.DataFrame({
        "순서": list(range(1, len(cats) + 1)),
        "유입경로": cats,
    })
    edited = st.data_editor(
        df, num_rows="dynamic", use_container_width=True,
        hide_index=True, key="source_cat_editor",
        column_config={
            "순서": st.column_config.NumberColumn("순서", min_value=1, step=1, width="small"),
            "유입경로": st.column_config.TextColumn("유입경로", width="large"),
        },
    )

    col1, col2 = st.columns(2)
    if col1.button("저장", type="primary", use_container_width=True):
        # 순서 기준 정렬 후 저장
        valid = edited.dropna(subset=["유입경로"])
        valid = valid[valid["유입경로"].str.strip() != ""]
        sorted_cats = valid.sort_values("순서")["유입경로"].str.strip().tolist()
        _save_categories(sb, user_id, sorted_cats)
        st.rerun()
    if col2.button("기본값 초기화", use_container_width=True):
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
        st.error(f"저장 실패: {e}")


def _load_settings(sb, user_id: str) -> dict:
    """사용자 설정 로드"""
    try:
        res = sb.table("users_settings").select("*").eq("id", user_id).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        st.warning(f"설정 로드 실패: {e}")
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
        st.success("설정이 저장되었습니다.")
    except Exception as e:
        st.error(f"저장 실패: {e}")
