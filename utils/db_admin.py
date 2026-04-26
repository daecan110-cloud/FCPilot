"""Supabase DB 관리 유틸 — service_role 클라이언트"""
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_admin_client() -> Client:
    """service_role_key 기반 클라이언트 (RLS 우회, 싱글턴)"""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)
