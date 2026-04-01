"""Supabase 클라이언트 초기화"""
import streamlit as st
from supabase import create_client, Client


def get_supabase_client() -> Client:
    """세션별 Supabase 클라이언트 — 사용자 JWT 자동 주입.
    @st.cache_resource 제거: 공유 클라이언트가 set_session()으로
    다른 사용자의 auth 토큰을 덮어쓰는 race condition 방지.
    """
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    client = create_client(url, key)
    session = st.session_state.get("session")
    if session:
        try:
            client.auth.set_session(session.access_token, session.refresh_token)
        except Exception:
            pass
    return client
