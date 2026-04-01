"""FCPilot 공통 UI 컴포넌트"""
import streamlit as st

GRADE_COLORS = {
    "VIP": "#7c3aed", "S": "#059669", "A": "#ef4444",
    "B": "#f59e0b", "C": "#3b82f6", "D": "#9ca3af"
}


def grade_badge(grade: str) -> str:
    """등급 색상 뱃지 HTML 반환"""
    color = GRADE_COLORS.get(grade, "#9ca3af")
    return (
        f'<span style="background:{color}; color:white; padding:2px 10px; '
        f'border-radius:6px; font-size:11px; font-weight:600; letter-spacing:0.5px;">{grade}</span>'
    )


def empty_state(icon: str, message: str):
    """빈 상태 중앙 표시"""
    st.markdown(
        f'<div style="text-align:center; padding:40px; color:#9ca3af;">'
        f'<div style="font-size:36px; margin-bottom:8px;">{icon}</div>'
        f'<div style="font-size:14px;">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = ""):
    """섹션 헤더"""
    st.markdown(
        f'<div style="margin-top:28px; margin-bottom:12px;">'
        f'<span style="font-size:16px; font-weight:600; color:#1a1a2e;">{title}</span>'
        + (
            f'<span style="font-size:13px; color:#9ca3af; margin-left:8px;">{subtitle}</span>'
            if subtitle else ""
        )
        + '</div>',
        unsafe_allow_html=True,
    )
