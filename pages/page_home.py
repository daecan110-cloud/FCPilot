"""FCPilot 홈 — 오늘의 할 일 대시보드"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from services.reminder import get_all_reminders
from services.remind_trigger import check_and_send_daily_reminder
from utils.supabase_client import get_supabase_client


def render():
    st.header("오늘의 할 일")
    st.caption(f"{date.today().strftime('%Y년 %m월 %d일')}")

    fc_id = get_current_user_id()
    if not fc_id:
        st.warning("로그인이 필요합니다.")
        return

    check_and_send_daily_reminder()
    reminders = get_all_reminders(fc_id)
    _render_summary(reminders)
    st.divider()
    _render_contact_reminders(reminders.get("contacts", []))
    st.divider()
    _render_pioneer_reminders(reminders.get("pioneers", []))
    st.divider()
    _render_recent_activity(fc_id)


def _render_summary(reminders: dict):
    """상단 요약 메트릭"""
    contacts = reminders.get("contacts", [])
    pioneers = reminders.get("pioneers", [])
    total = reminders.get("total", 0)

    overdue_contacts = sum(1 for c in contacts if c.get("overdue"))
    overdue_pioneers = sum(1 for p in pioneers if p.get("overdue"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오늘 할 일", f"{total}건")
    c2.metric("상담 리마인드", f"{len(contacts)}건",
              delta=f"-{overdue_contacts} 지연" if overdue_contacts else None,
              delta_color="inverse")
    c3.metric("개척 팔로업", f"{len(pioneers)}건",
              delta=f"-{overdue_pioneers} 지연" if overdue_pioneers else None,
              delta_color="inverse")
    c4.metric("총 지연", f"{overdue_contacts + overdue_pioneers}건",
              delta_color="inverse")


def _render_contact_reminders(contacts: list[dict]):
    """상담 리마인드 목록"""
    st.subheader("상담 리마인드")

    if not contacts:
        st.success("예정된 상담 리마인드가 없습니다.")
        return

    for c in contacts:
        overdue_icon = "🔴" if c.get("overdue") else "🟡"
        grade = c.get("grade", "")
        grade_badge = f"[{grade}등급]" if grade else ""
        name = c.get("client_name", "이름 없음")
        action = c.get("next_action", "연락 예정")
        next_date = c.get("next_date", "")

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"{overdue_icon} **{name}** {grade_badge} — {action}")
            col2.caption(f"예정일: {next_date}")


def _render_pioneer_reminders(pioneers: list[dict]):
    """개척 팔로업 목록"""
    st.subheader("개척 팔로업")

    if not pioneers:
        st.success("예정된 개척 팔로업이 없습니다.")
        return

    for p in pioneers:
        priority = p.get("priority", "low")
        icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(priority, "🟡")
        name = p.get("shop_name", "")
        action = p.get("action", "")
        days = p.get("days_left", 0)
        label = f"D{days:+d}" if days != 0 else "오늘"

        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"{icon} **{name}** — {action}")
            col2.caption(label)


def _render_recent_activity(fc_id: str):
    """최근 활동 요약 (최근 5건 상담 기록)"""
    st.subheader("최근 활동")

    sb = get_supabase_client()
    try:
        res = sb.table("contact_logs").select(
            "*, fp_clients(name)"
        ).eq("fc_id", fc_id).order(
            "created_at", desc=True
        ).limit(5).execute()
        logs = res.data or []
    except Exception:
        logs = []

    if not logs:
        st.info("최근 활동 기록이 없습니다.")
        return

    for log in logs:
        client = log.get("clients", {}) or {}
        name = client.get("name", "")
        method = log.get("touch_method", "")
        memo = log.get("memo", "")
        created = log.get("created_at", "")[:10]

        st.caption(f"{created} | {name} | {method} | {memo[:30]}")
