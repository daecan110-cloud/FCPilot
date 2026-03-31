"""FCPilot — 메인 라우터 (로직 넣지 말 것)"""
import streamlit as st
from config import PAGE_CONFIG
from auth import init_auth, is_logged_in, show_login_page, logout, check_session_timeout, get_user_status

st.set_page_config(**PAGE_CONFIG)

# 풋터 + 불필요한 UI 숨기기
st.markdown("""
<style>
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def main():
    init_auth()  # 새로고침 시 쿠키에서 세션 복원

    if not is_logged_in():
        show_login_page()
        return

    # 승인 상태 체크
    status = get_user_status()
    if status == "pending":
        st.warning("회원가입 승인 대기 중입니다. 관리자 승인 후 이용 가능합니다.")
        if st.button("로그아웃"):
            logout()
        return
    if status == "rejected":
        st.error("회원가입이 거절되었습니다. 관리자에게 문의해주세요.")
        if st.button("로그아웃"):
            logout()
        return

    check_session_timeout()

    with st.sidebar:
        st.title("FCPilot")
        user = st.session_state.get("user")
        if user:
            st.caption(user.email)

        # UX-04: 영업 모드에 따라 탭 순서 변경
        mode = _get_sales_mode()
        if mode == "pioneer":
            menu = ["오늘의 할일", "개척지도", "동선기록", "고객관리", "보장분석", "통계", "설정"]
        elif mode == "referral":
            menu = ["오늘의 할일", "고객관리", "보장분석", "통계", "개척지도", "동선기록", "설정"]
        else:
            menu = ["오늘의 할일", "보장분석", "고객관리", "개척지도", "동선기록", "통계", "설정"]

        if "_nav_to" in st.session_state:
            nav_target = st.session_state.pop("_nav_to")
            if nav_target in menu:
                st.session_state["main_nav"] = nav_target
        tab = st.radio("메뉴", menu, label_visibility="collapsed", key="main_nav")

        st.divider()
        if st.button("로그아웃", use_container_width=True):
            logout()

    if tab == "오늘의 할일":
        from views.page_home import render
        render()
    elif tab == "보장분석":
        from views.page_analysis import render
        render()
    elif tab == "고객관리":
        from views.page_clients import render
        render()
    elif tab == "개척지도":
        from views.page_pioneer_map import render
        render()
    elif tab == "동선기록":
        from views.page_pioneer_route import render
        render()
    elif tab == "통계":
        from views.page_stats import render
        render()
    elif tab == "설정":
        from views.page_settings import render
        render()


def _get_sales_mode() -> str:
    try:
        from auth import get_current_user_id
        from utils.supabase_client import get_supabase_client
        user_id = get_current_user_id()
        if not user_id:
            return "both"
        sb = get_supabase_client()
        res = sb.table("users_settings").select("mode").eq("id", user_id).execute()
        if res.data:
            return res.data[0].get("mode", "both")
    except Exception:
        pass
    return "both"


if __name__ == "__main__":
    main()
