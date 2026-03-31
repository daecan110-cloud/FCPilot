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
        _render_admin_section(sb)


def _render_admin_section(sb):
    """Admin 전용 — DB 관리 / 시스템 설정"""
    st.divider()
    st.subheader("🔧 Admin 관리")

    with st.expander("사용자 역할 관리"):
        try:
            res = sb.table("users_settings").select("id, display_name, role").execute()
            users = res.data or []
            for u in users:
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.text(u.get("display_name") or u["id"][:8])
                with col2:
                    st.text(u.get("role", "user"))
                with col3:
                    new_role = st.selectbox(
                        "역할",
                        ["user", "admin"],
                        index=0 if u.get("role") != "admin" else 1,
                        key=f"role_{u['id']}",
                        label_visibility="collapsed",
                    )
                if st.button("변경", key=f"btn_{u['id']}"):
                    try:
                        sb.table("users_settings").update({"role": new_role}).eq("id", u["id"]).execute()
                        st.success("역할 변경 완료")
                        st.rerun()
                    except Exception as e:
                        st.error(f"변경 실패: {e}")
        except Exception as e:
            st.error(f"사용자 조회 실패: {e}")

    with st.expander("DB 통계"):
        try:
            tables = ["clients", "contact_logs", "pioneer_shops", "pioneer_visits",
                      "analysis_records", "yakwan_records", "command_queue"]
            for t in tables:
                res = sb.table(t).select("id", count="exact").execute()
                st.text(f"{t}: {res.count}건")
        except Exception as e:
            st.error(f"통계 조회 실패: {e}")


_DEFAULT_CATEGORIES = ["DB고객", "개인(지인)", "개척", "소개", "기타"]


def _render_source_categories(sb, user_id: str):
    """유입경로 카테고리 관리"""
    st.subheader("유입경로 카테고리")
    st.caption("고객 등록·수정 시 표시되는 유입경로 항목을 관리합니다.")

    try:
        res = sb.table("users_settings").select("source_categories").eq("id", user_id).execute()
        cats = (res.data[0].get("source_categories") if res.data else None) or _DEFAULT_CATEGORIES
    except Exception:
        cats = _DEFAULT_CATEGORIES

    # 현재 목록 + 삭제 버튼
    for i, cat in enumerate(cats):
        col1, col2 = st.columns([5, 1])
        col1.text(cat)
        if col2.button("삭제", key=f"del_cat_{i}"):
            new_cats = [c for j, c in enumerate(cats) if j != i]
            _save_categories(sb, user_id, new_cats)
            st.rerun()

    # 새 카테고리 추가
    with st.form("add_category_form"):
        new_cat = st.text_input("새 카테고리 추가", placeholder="예: 온라인DB, 법인, 세미나")
        if st.form_submit_button("추가"):
            stripped = new_cat.strip()
            if stripped and stripped not in cats:
                _save_categories(sb, user_id, cats + [stripped])
                st.rerun()
            elif stripped in cats:
                st.warning("이미 존재하는 카테고리입니다.")

    # 기본값 복원
    if st.button("기본값으로 초기화"):
        _save_categories(sb, user_id, _DEFAULT_CATEGORIES)
        st.rerun()


def _save_categories(sb, user_id: str, categories: list):
    try:
        sb.table("users_settings").upsert({
            "id": user_id,
            "source_categories": categories,
        }).execute()
        st.session_state.pop(f"source_cats_{user_id}", None)  # 캐시 무효화
        st.success("저장됨")
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
