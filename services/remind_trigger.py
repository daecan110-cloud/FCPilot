"""리마인드 발송 트리거 — 하루 1회 텔레그램 알림"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from services.reminder import get_all_reminders
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

    reminders = get_all_reminders(fc_id)
    if reminders["total"] == 0:
        st.session_state.remind_sent_date = today
        return

    # 텔레그램 알림 구성
    items = []
    for c in reminders["contacts"]:
        items.append({
            "client_name": c.get("client_name", ""),
            "action": c.get("next_action", "상담 예정"),
            "overdue": c.get("overdue", False),
        })
    for p in reminders["pioneers"]:
        items.append({
            "shop_name": p.get("shop_name", ""),
            "action": p.get("action", "팔로업"),
            "overdue": p.get("overdue", False),
        })

    notify_reminder(items)
    st.session_state.remind_sent_date = today
