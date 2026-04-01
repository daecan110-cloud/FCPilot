"""리마인드 발송 트리거 — 하루 1회 텔레그램 알림"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.telegram import notify_reminder


def _already_sent_today(fc_id: str, today: str) -> bool:
    """DB에서 오늘 발송 여부 확인 (users_settings.last_remind_date)"""
    try:
        res = (get_supabase_client().table("users_settings")
               .select("last_remind_date")
               .eq("id", fc_id)
               .execute())
        if res.data and res.data[0].get("last_remind_date") == today:
            return True
    except Exception:
        pass
    return False


def _mark_sent(fc_id: str, today: str):
    """DB에 발송일 기록"""
    try:
        get_supabase_client().table("users_settings").update(
            {"last_remind_date": today}
        ).eq("id", fc_id).execute()
    except Exception:
        pass


def check_and_send_daily_reminder():
    """홈 로드 시 호출 — 당일 미발송이면 텔레그램 알림

    session_state + DB 이중 체크로 중복 방지.
    """
    today = str(date.today())
    if st.session_state.get("remind_sent_date") == today:
        return

    fc_id = get_current_user_id()
    if not fc_id:
        return

    # DB 체크 — 다른 세션에서 이미 보냈으면 스킵
    if _already_sent_today(fc_id, today):
        st.session_state.remind_sent_date = today
        return

    # fp_reminders: 지연 + 오늘 예정
    from services.fp_reminder_service import get_bucketed
    buckets = get_bucketed(fc_id)
    due_reminders = buckets["today"]

    # 개척 팔로업: 기한 초과 매장
    from services.followup import get_followup_list
    pioneers = [f for f in get_followup_list(fc_id) if f.get("overdue")]

    if not due_reminders and not pioneers:
        st.session_state.remind_sent_date = today
        _mark_sent(fc_id, today)
        return

    notify_reminder(due_reminders, pioneers)
    st.session_state.remind_sent_date = today
    _mark_sent(fc_id, today)
