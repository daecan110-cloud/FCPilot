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
        st.rerun()
    c2.markdown(f"<div style='text-align:center;font-weight:bold'>{year}년 {month}월</div>",
                unsafe_allow_html=True)
    if c3.button("▶", key="cal_next", use_container_width=True):
        if month == 12:
            st.session_state.cal_year += 1
            st.session_state.cal_month = 1
        else:
            st.session_state.cal_month += 1
        st.rerun()

    # 해당 월 리마인드 조회
    _, last_day = calendar.monthrange(year, month)
    month_start = f"{year}-{month:02d}-01"
    month_end = f"{year}-{month:02d}-{last_day:02d}"
    try:
        rows = (get_supabase_client().table("fp_reminders")
                .select("reminder_date, status, purpose, clients(name)")
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

    # HTML 캘린더 테이블
    today_str = str(today)
    cal_matrix = calendar.monthcalendar(year, month)

    html = '<table style="width:100%;text-align:center;border-collapse:separate;border-spacing:2px;font-size:13px">'
    html += '<tr>' + ''.join(
        f'<th style="padding:4px 0;color:#888;font-weight:600">{h}</th>'
        for h in ['월', '화', '수', '목', '금', '토', '일']
    ) + '</tr>'

    for week in cal_matrix:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td></td>'
                continue
            day_str = f"{year}-{month:02d}-{day:02d}"
            info = date_map.get(day_str, {})
            pending = info.get("pending", 0)
            done = info.get("completed", 0)
            is_today = day_str == today_str

            if is_today:
                bg, fg = "#1E88E5", "white"
            elif pending:
                bg, fg = "#fff3e0", "inherit"
            else:
                bg, fg = "transparent", "inherit"

            day_html = f"<b>{day}</b>" if is_today else str(day)
            badge = ""
            if pending:
                badge += f'<br><span style="font-size:10px;color:{"#fff" if is_today else "#e53935"}">●{pending}</span>'
            if done:
                badge += f'<br><span style="font-size:10px;color:{"#cce" if is_today else "#43a047"}">✓{done}</span>'

            html += (f'<td style="padding:5px 2px;border-radius:8px;background:{bg};'
                     f'color:{fg};min-width:30px;vertical-align:top">'
                     f'{day_html}{badge}</td>')
        html += '</tr>'

    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)

    if rows:
        pending_total = sum(d.get("pending", 0) for d in date_map.values())
        done_total = sum(d.get("completed", 0) for d in date_map.values())
        st.caption(f"{year}년 {month}월: 대기 {pending_total}건 · 완료 {done_total}건")

    # 날짜별 상세 보기
    import datetime as _dt
    default_sel = today if (today.year == year and today.month == month) else _dt.date(year, month, 1)
    try:
        default_sel = _dt.date.fromisoformat(default_sel if isinstance(default_sel, str) else str(default_sel))
    except Exception:
        default_sel = today
    sel = st.date_input("날짜 선택하여 상세 보기", value=default_sel, key=f"cal_detail_{year}_{month}")
    sel_str = str(sel)
    day_rows = [r for r in rows if r.get("reminder_date") == sel_str]
    if day_rows:
        for r in day_rows:
            client = r.get("clients") or {}
            name = client.get("name", "")
            status_icon = {"pending": "🟡", "completed": "✅", "cancelled": "❌"}.get(r.get("status", ""), "")
            st.markdown(f"{status_icon} **{name}** — {r.get('purpose','')} {('| ' + (r.get('memo') or '')[:20]) if r.get('memo') else ''}")
    else:
        st.caption(f"{sel} 일정 없음")
