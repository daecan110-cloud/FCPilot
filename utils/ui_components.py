"""FCPilot 공통 UI 컴포넌트 — Notion 스타일"""
import streamlit as st

GRADE_COLORS = {
    "VIP": "#9B59B6", "S": "#27AE60", "A": "#EB5757",
    "B": "#F2994A", "C": "#2F80ED", "D": "#828282"
}


def grade_badge(grade: str) -> str:
    """등급 색상 뱃지 HTML 반환"""
    color = GRADE_COLORS.get(grade, "#828282")
    return (
        f'<span style="background:{color}; color:white; padding:2px 8px; '
        f'border-radius:4px; font-size:12px; font-weight:500;">{grade}</span>'
    )


def empty_state(icon: str, message: str):
    """빈 상태 중앙 표시"""
    st.markdown(
        f'<div style="text-align:center; padding:40px; color:#787774;">'
        f'<div style="font-size:36px; margin-bottom:8px;">{icon}</div>'
        f'<div style="font-size:14px;">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = ""):
    """섹션 헤더 — 여백으로만 구분"""
    st.markdown(
        f'<div style="margin-top:24px; margin-bottom:8px;">'
        f'<span style="font-size:16px; font-weight:600; color:#37352F;">{title}</span>'
        + (
            f'<span style="font-size:13px; color:#787774; margin-left:8px;">{subtitle}</span>'
            if subtitle else ""
        )
        + '</div>',
        unsafe_allow_html=True,
    )
