"""FCPilot — 메인 라우터 (로직 넣지 말 것)"""
import streamlit as st
from config import PAGE_CONFIG
from auth import is_logged_in, show_login_page, logout, check_session_timeout

st.set_page_config(**PAGE_CONFIG)

# 풋터 + 불필요한 UI 숨기기
st.markdown("""
<style>
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def main():
    if not is_logged_in():
        show_login_page()
        return

    check_session_timeout()

    with st.sidebar:
        st.title("FCPilot")
        user = st.session_state.get("user")
        if user:
            st.caption(user.email)

        tab = st.radio(
            "메뉴",
            ["홈", "보장분석", "고객관리", "개척지도", "동선기록", "통계", "설정"],
            label_visibility="collapsed",
        )

        st.divider()
        if st.button("로그아웃", use_container_width=True):
            logout()

    if tab == "홈":
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


if __name__ == "__main__":
    main()
