"""Supabase 클라이언트 초기화"""
import time
import streamlit as st
from supabase import create_client, Client

_SESSION_REFRESH_INTERVAL = 300  # 5분


def get_supabase_client() -> Client:
    """세션별 Supabase 클라이언트 — 사용자 JWT 자동 주입.
    클라이언트 객체는 session_state에 보관해 재생성 오버헤드 제거.
    set_session은 5분 간격으로만 호출해 불필요한 네트워크 왕복 제거.
    """
    if "sb_client" not in st.session_state:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        st.session_state.sb_client = create_client(url, key)
    client = st.session_state.sb_client
    session = st.session_state.get("session")
    if session:
        now = time.time()
        last_refresh = st.session_state.get("_sb_last_refresh", 0)
        if now - last_refresh >= _SESSION_REFRESH_INTERVAL:
            try:
                res = client.auth.set_session(session.access_token, session.refresh_token)
                st.session_state._sb_last_refresh = now
                if res and res.session:
                    st.session_state.session = res.session
            except Exception:
                st.session_state.pop("session", None)
                st.session_state.pop("user", None)
    return client
