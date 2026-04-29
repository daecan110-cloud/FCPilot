"""FCPilot — 메인 라우터 (로직 넣지 말 것)"""
import streamlit as st
from config import PAGE_CONFIG
from auth import init_auth, is_logged_in, show_login_page, logout, check_session_timeout, get_user_status, is_admin

st.set_page_config(**PAGE_CONFIG)

# 글로벌 Notion 스타일 CSS
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #1a1a2e;
    }
    input, button, textarea, select, label {
        font-family: inherit !important;
    }

    /* expander 아이콘 숨김 */
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stExpander"] details > summary svg,
    [data-testid="stExpander"] summary > div > span:first-child {
        display: none !important;
        font-size: 0 !important;
    }

    .stApp { background-color: #f8f9fc; }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: none;
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 8px 12px;
        border-radius: 8px;
        transition: background 0.15s;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] .stRadio label[data-checked="true"],
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.1);
        border: 1px solid rgba(255,255,255,0.15);
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.18);
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1);
    }

    /* 타이포그래피 */
    h1 { font-weight: 700; font-size: 26px; color: #1a1a2e; margin-bottom: 4px; }
    h2 { font-weight: 600; font-size: 20px; color: #1a1a2e; margin-top: 20px; }
    h3 { font-weight: 600; font-size: 16px; color: #1a1a2e; }

    /* 메트릭 카드 */
    [data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        border: 1px solid #eef0f4;
    }
    [data-testid="stMetricLabel"] {
        color: #6b7280 !important;
    }
    [data-testid="stMetricValue"] {
        color: #1a1a2e !important;
        font-weight: 700 !important;
    }

    /* 컨테이너/카드 */
    [data-testid="stExpander"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div[data-testid="stVerticalBlock"][data-has-border="true"]) {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #eef0f4;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }

    .notion-card {
        background: #ffffff;
        border: 1px solid #eef0f4;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: box-shadow 0.15s, transform 0.15s;
    }
    .notion-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transform: translateY(-1px);
    }

    /* 버튼 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        font-size: 14px;
        transition: all 0.15s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5, #6366f1);
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4338ca, #4f46e5);
        box-shadow: 0 4px 12px rgba(79,70,229,0.3);
    }

    /* 인풋 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        font-size: 14px;
        background: #ffffff;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
    }

    hr { border-color: #eef0f4; margin: 24px 0; }

    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        font-weight: 500;
        color: #9ca3af;
        border-radius: 8px;
    }
    .stTabs [aria-selected="true"] {
        color: #4f46e5;
        font-weight: 600;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Streamlit Cloud "앱 관리"(stStatusWidget) / Deploy / Share 등 기본 숨김 — admin은 main()에서 다시 노출 */
    [data-testid="stStatusWidget"],
    [data-testid="stDeployButton"],
    .stDeployButton,
    .viewerBadge_container__1QSob,
    .viewerBadge_link__1S137,
    .styles_viewerBadge__1yB5_,
    div[class*="viewerBadge"],
    div[class*="_terminalButton_"],
    a[href*="streamlit.io/cloud"],
    a[href*="share.streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
    }
    /* 툴바 내 액션 버튼(Share/Fork/Source) 숨김 — 사이드바 토글은 유지 */
    [data-testid="stToolbarActions"] {
        display: none !important;
    }

    /* 사이드바 토글 버튼은 반드시 보이게 */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[kind="headerNoPadding"] {
        visibility: visible !important;
        display: flex !important;
        opacity: 1 !important;
    }

    @media (max-width: 768px) {
        .stButton > button { width: 100%; }
        h1 { font-size: 20px; }
    }
</style>
""", unsafe_allow_html=True)


def main():
    from utils.db_migrate import run_auto_migrations
    run_auto_migrations()
    init_auth()  # 새로고침 시 쿠키에서 세션 복원

    if not is_logged_in():
        show_login_page()
        return

    # 승인 전 차단
    status = get_user_status()
    if status == "pending":
        st.warning("관리자 승인 대기 중입니다. 승인 후 이용 가능합니다.")
        if st.button("로그아웃"):
            logout()
        return
    if status == "rejected":
        st.error("계정이 비활성화되었습니다. 관리자에게 문의해주세요.")
        if st.button("로그아웃"):
            logout()
        return

    check_session_timeout()

    # admin 전용: Streamlit Cloud "앱 관리"(stStatusWidget) 버튼 노출 (리부트 가능)
    if is_admin():
        st.markdown(
            "<style>"
            "[data-testid='stStatusWidget'] {"
            "display: block !important; visibility: visible !important;"
            "}"
            "</style>",
            unsafe_allow_html=True,
        )

    with st.sidebar:
        st.markdown(
            '<div style="text-align:center; padding:12px 0 4px;">'
            '<span style="font-size:22px; font-weight:700; color:#ffffff !important;">🛡️ FCPilot</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        user = st.session_state.get("user")
        if user:
            from utils.helpers import esc
            st.markdown(
                f'<div style="text-align:center; padding-bottom:8px;">'
                f'<span style="font-size:12px; color:#94a3b8 !important;">{esc(str(user.email))}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")

        # UX-04: 영업 모드에 따라 탭 순서 변경
        mode = _get_sales_mode()
        if mode == "pioneer":
            menu = ["📋 오늘의 할일", "🗺️ 개척지도", "📍 동선기록", "👥 고객관리", "📊 보장분석", "📈 통계", "⚙️ 설정"]
        elif mode == "referral":
            menu = ["📋 오늘의 할일", "👥 고객관리", "📊 보장분석", "📈 통계", "🗺️ 개척지도", "📍 동선기록", "⚙️ 설정"]
        else:
            menu = ["📋 오늘의 할일", "📊 보장분석", "👥 고객관리", "🗺️ 개척지도", "📍 동선기록", "📈 통계", "⚙️ 설정"]

        if "_nav_to" in st.session_state:
            nav_target = st.session_state.pop("_nav_to")
            if nav_target in menu:
                st.session_state["main_nav"] = nav_target
        tab = st.radio("메뉴", menu, label_visibility="collapsed", key="main_nav")

        st.markdown("---")
        st.caption("v1.0")
        if st.button("로그아웃", use_container_width=True):
            logout()

    if tab == "📋 오늘의 할일":
        from views.page_home import render
        render()
    elif tab == "📊 보장분석":
        from views.page_analysis import render
        render()
    elif tab == "👥 고객관리":
        from views.page_clients import render
        render()
    elif tab == "🗺️ 개척지도":
        from views.page_pioneer_map import render
        render()
    elif tab == "📍 동선기록":
        from views.page_pioneer_route import render
        render()
    elif tab == "📈 통계":
        from views.page_stats import render
        render()
    elif tab == "⚙️ 설정":
        from views.page_settings import render
        render()


def _get_sales_mode() -> str:
    if "cached_sales_mode" in st.session_state:
        return st.session_state.cached_sales_mode
    try:
        from auth import get_current_user_id
        from utils.supabase_client import get_supabase_client
        user_id = get_current_user_id()
        if not user_id:
            return "both"
        sb = get_supabase_client()
        res = sb.table("users_settings").select("mode").eq("id", user_id).execute()
        if res.data:
            mode = res.data[0].get("mode", "both")
            st.session_state.cached_sales_mode = mode
            return mode
    except Exception as e:
        import logging
        logging.warning(f"sales_mode 조회 실패: {type(e).__name__}")
    return "both"


if __name__ == "__main__":
    main()
