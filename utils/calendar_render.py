"""홈 탭 월간 캘린더 렌더러"""
import calendar
from datetime import date

import streamlit as st

from utils.supabase_client import get_supabase_client


def render_monthly_calendar(fc_id: str):
    today = date.today()

    if "cal_year" not in st.session_state:
        st.session_state.cal_year = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month

    year = st.session_state.cal_year
    month = st.session_state.cal_month

    # 월 이동 버튼
    c1, c2, c3 = st.columns([1, 4, 1])
    if c1.button("◀", key="cal_prev", use_container_width=True):
        if month == 1:
            st.session_state.cal_year -= 1
            st.session_state.cal_month = 12
        else:
            st.session_state.cal_month -= 1
        st.session_state.pop("cal_selected_date", None)
        st.rerun()
    c2.markdown(f"<div style='text-align:center;font-weight:bold'>{year}년 {month}월</div>",
                unsafe_allow_html=True)
    if c3.button("▶", key="cal_next", use_container_width=True):
        if month == 12:
            st.session_state.cal_year += 1
            st.session_state.cal_month = 1
        else:
            st.session_state.cal_month += 1
        st.session_state.pop("cal_selected_date", None)
        st.rerun()

    # 해당 월 리마인드 조회
    _, last_day = calendar.monthrange(year, month)
    month_start = f"{year}-{month:02d}-01"
    month_end = f"{year}-{month:02d}-{last_day:02d}"
    try:
        rows = (get_supabase_client().table("fp_reminders")
                .select("reminder_date, status, purpose, memo, clients(name)")
                .eq("fc_id", fc_id)
                .gte("reminder_date", month_start)
                .lte("reminder_date", month_end)
                .execute().data or [])
    except Exception:
        rows = []

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
    header_cols = st.columns(7)
    for i, h in enumerate(["월", "화", "수", "목", "금", "토", "일"]):
        header_cols[i].markdown(
            f"<div style='text-align:center;font-size:12px;color:#888;font-weight:600;padding-bottom:2px'>{h}</div>",
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
            is_today = day_str == today_str

            # 버튼 라벨: 오늘은 [n], 이벤트 있으면 ● / ✓ 표시
            if is_today:
                lbl = f"[{day}]"
            else:
                lbl = str(day)
            if pending:
                lbl += f" ●{pending}"
            elif done:
                lbl += f" ✓"

            if cols[i].button(lbl, key=f"cal_{day_str}", use_container_width=True):
                if selected == day_str:
                    st.session_state.pop("cal_selected_date", None)
                else:
                    st.session_state.cal_selected_date = day_str
                st.rerun()

    # 선택된 날짜 상세
    if selected and selected.startswith(f"{year}-{month:02d}"):
        day_rows = [r for r in rows if r.get("reminder_date") == selected]
        st.markdown(f"**{selected} 일정**")
        if day_rows:
            for r in day_rows:
                client = r.get("clients") or {}
                name = client.get("name", "")
                status_icon = {"pending": "🟡", "completed": "✅", "cancelled": "❌"}.get(r.get("status", ""), "")
                memo_part = f" | {r['memo'][:20]}" if r.get("memo") else ""
                st.markdown(f"{status_icon} **{name}** — {r.get('purpose', '')}{memo_part}")
        else:
            st.caption(f"{selected} 일정 없음")

    if rows:
        pending_total = sum(d.get("pending", 0) for d in date_map.values())
        done_total = sum(d.get("completed", 0) for d in date_map.values())
        st.caption(f"{year}년 {month}월: 대기 {pending_total}건 · 완료 {done_total}건")
