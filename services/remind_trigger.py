"""리마인드 발송 트리거 — 하루 1회 텔레그램 알림"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from utils.telegram import notify_reminder


def check_and_send_daily_reminder():
    """홈 로드 시 호출 — 당일 미발송이면 텔레그램 알림

    session_state["remind_sent_date"]로 중복 방지.
    """
    today = str(date.today())
    if st.session_state.get("remind_sent_date") == today:
        return

    fc_id = get_current_user_id()
    if not fc_id:
        return

    # fp_reminders: 지연 + 오늘 예정
    from services.fp_reminder_service import get_bucketed
    buckets = get_bucketed(fc_id)
    due_reminders = buckets["overdue"] + buckets["today"]

    # 개척 팔로업: 기한 초과 매장
    from services.followup import get_followup_list
    pioneers = [f for f in get_followup_list(fc_id) if f.get("overdue")]

    if not due_reminders and not pioneers:
        st.session_state.remind_sent_date = today
        return

    notify_reminder(due_reminders, pioneers)
    st.session_state.remind_sent_date = today
