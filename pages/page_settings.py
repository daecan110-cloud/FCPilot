"""설정 페이지"""
import streamlit as st
from auth import get_current_user_id
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
    st.caption(f"FCPilot v1.0.0 | User ID: {user_id[:8]}...")


def _load_settings(sb, user_id: str) -> dict:
    """사용자 설정 로드"""
    try:
        res = sb.table("users_settings").select("*").eq("id", user_id).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
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
