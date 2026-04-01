"""Supabase 클라이언트 초기화"""
import streamlit as st
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """세션별 Supabase 클라이언트 — 사용자 JWT 자동 주입.
    클라이언트 객체는 session_state에 보관해 재생성 오버헤드 제거.
    set_session은 매번 호출해 토큰을 최신 상태로 유지.
    """
    if "sb_client" not in st.session_state:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        st.session_state.sb_client = create_client(url, key)
    client = st.session_state.sb_client
    session = st.session_state.get("session")
    if session:
        try:
            client.auth.set_session(session.access_token, session.refresh_token)
        except Exception:
            pass
    return client
