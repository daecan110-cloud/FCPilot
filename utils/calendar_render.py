"""홈 탭 월간 캘린더 렌더러"""
import calendar
from datetime import date

import streamlit as st

from utils.helpers import esc
from utils.supabase_client import get_supabase_client


def _nav_prev():
    if st.session_state.cal_month == 1:
        st.session_state.cal_year -= 1
        st.session_state.cal_month = 12
    else:
        st.session_state.cal_month -= 1
    st.session_state.pop("cal_selected_date", None)


def _nav_next():
    if st.session_state.cal_month == 12:
        st.session_state.cal_year += 1
        st.session_state.cal_month = 1
    else:
        st.session_state.cal_month += 1
    st.session_state.pop("cal_selected_date", None)


def _nav_today():
    t = date.today()
    st.session_state.cal_year = t.year
    st.session_state.cal_month = t.month
    st.session_state.pop("cal_selected_date", None)


def _select_date(day_str):
    if st.session_state.get("cal_selected_date") == day_str:
        st.session_state.pop("cal_selected_date", None)
    else:
        st.session_state.cal_selected_date = day_str


@st.cache_data(ttl=60, show_spinner=False)
def _load_month_reminders(fc_id: str, month_start: str, month_end: str) -> list[dict]:
    """월간 리마인드 조회 (60초 캐싱)"""
    try:
        return (get_supabase_client().table("fp_reminders")
                .select("reminder_date, status, purpose, memo, clients(name)")
                .eq("fc_id", fc_id)
                .gte("reminder_date", month_start)
                .lte("reminder_date", month_end)
                .execute().data or [])
    except Exception:
        return []


def render_monthly_calendar(fc_id: str):
    today = date.today()

    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month

    year = st.session_state.cal_year
    month = st.session_state.cal_month

    # 월 이동
    c1, c2, c3, c4 = st.columns([1, 1, 4, 1])
    c1.button("◀", key="cal_prev", use_container_width=True, on_click=_nav_prev)
    is_current = year == today.year and month == today.month
    c2.button("오늘", key="cal_today", use_container_width=True,
              disabled=is_current, on_click=_nav_today)
    c3.markdown(
        f"<div style='text-align:center;font-size:16px;font-weight:700;"
        f"color:#1a1a2e;padding:6px 0;'>{year}년 {month}월</div>",
        unsafe_allow_html=True,
    )
    c4.button("▶", key="cal_next", use_container_width=True, on_click=_nav_next)

    # 해당 월 리마인드 조회 (캐싱)
    _, last_day = calendar.monthrange(year, month)
    month_start = f"{year}-{month:02d}-01"
    month_end = f"{year}-{month:02d}-{last_day:02d}"
    rows = _load_month_reminders(fc_id, month_start, month_end)

    # 날짜별 카운트
    date_map: dict = {}
    for r in rows:
        d = r.get("reminder_date", "")
        s = r.get("status", "")
        if not d:
            continue
        date_map.setdefault(d, {"pending": 0, "completed": 0})
        if s == "pending":
            date_map[d]["pending"] += 1
        elif s == "completed":
            date_map[d]["completed"] += 1

    today_str = str(today)
    cal_matrix = calendar.monthcalendar(year, month)
    selected = st.session_state.get("cal_selected_date")

    # 요일 헤더
    day_labels = ["월", "화", "수", "목", "금", "토", "일"]
    hdr_cols = st.columns(7)
    for i, lbl in enumerate(day_labels):
        color = "#ef4444" if i >= 5 else "#9ca3af"
        hdr_cols[i].markdown(
            f"<div style='text-align:center;font-size:12px;font-weight:600;"
            f"color:{color};'>{lbl}</div>",
            unsafe_allow_html=True,
        )

    # 날짜 버튼 그리드
    for week in cal_matrix:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
                continue
            day_str = f"{year}-{month:02d}-{day:02d}"
            info = date_map.get(day_str, {})
            pending = info.get("pending", 0)
            done = info.get("completed", 0)

            label = str(day)
            if pending:
                label += " 🟡"
            elif done:
                label += " ✅"

            btn_type = "primary" if day_str == today_str else "secondary"
            cols[i].button(
                label, key=f"cal_{day_str}",
                use_container_width=True, type=btn_type,
                on_click=_select_date, args=(day_str,),
            )

    # 선택된 날짜 상세
    if selected and selected.startswith(f"{year}-{month:02d}"):
        day_rows = [r for r in rows if r.get("reminder_date") == selected]
        st.markdown(
            f"<div style='margin-top:8px; padding:10px 14px; background:#f8f9fb; "
            f"border-radius:8px; border:1px solid #eef0f4;'>"
            f"<b>{esc(selected)} 일정</b></div>",
            unsafe_allow_html=True,
        )
        if day_rows:
            for r in day_rows:
                client = r.get("clients") or {}
                name = client.get("name", "")
                status_icon = {"pending": "🟡", "completed": "✅",
                               "cancelled": "❌"}.get(r.get("status", ""), "")
                memo_part = f" | {esc(r['memo'][:20])}" if r.get("memo") else ""
                st.markdown(f"{status_icon} **{esc(name)}** — {esc(r.get('purpose', ''))}{memo_part}")
        else:
            st.caption("일정 없음")
