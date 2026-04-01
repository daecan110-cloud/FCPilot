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

    # 월 이동 버튼 — ◀ [오늘] 2026년 4월 ▶
    c1, c2, c3, c4 = st.columns([1, 1, 4, 1])
    if c1.button("◀", key="cal_prev", use_container_width=True):
        if month == 1:
            st.session_state.cal_year -= 1
            st.session_state.cal_month = 12
        else:
            st.session_state.cal_month -= 1
        st.session_state.pop("cal_selected_date", None)
        st.rerun()
    is_current = year == today.year and month == today.month
    if c2.button("오늘", key="cal_today", use_container_width=True, disabled=is_current):
        st.session_state.cal_year = today.year
        st.session_state.cal_month = today.month
        st.session_state.pop("cal_selected_date", None)
        st.rerun()
    c3.markdown(
        f"<div style='text-align:center;font-size:16px;font-weight:700;"
        f"color:#1a1a2e;padding:6px 0;'>{year}년 {month}월</div>",
        unsafe_allow_html=True,
    )
    if c4.button("▶", key="cal_next", use_container_width=True):
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

    # HTML 캘린더 렌더링
    html = _build_calendar_html(cal_matrix, year, month, today_str, date_map, selected)
    st.markdown(html, unsafe_allow_html=True)

    # 날짜 선택 (버튼 그리드 — 투명 오버레이)
    for week in cal_matrix:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
                continue
            day_str = f"{year}-{month:02d}-{day:02d}"
            if cols[i].button(str(day), key=f"cal_{day_str}", use_container_width=True):
                if selected == day_str:
                    st.session_state.pop("cal_selected_date", None)
                else:
                    st.session_state.cal_selected_date = day_str
                st.rerun()

    # 선택된 날짜 상세
    if selected and selected.startswith(f"{year}-{month:02d}"):
        day_rows = [r for r in rows if r.get("reminder_date") == selected]
        st.markdown(
            f"<div style='margin-top:12px; padding:12px 16px; background:#ffffff; "
            f"border-radius:10px; border:1px solid #eef0f4;'>"
            f"<span style='font-weight:600; color:#1a1a2e;'>{selected} 일정</span></div>",
            unsafe_allow_html=True,
        )
        if day_rows:
            for r in day_rows:
                client = r.get("clients") or {}
                name = client.get("name", "")
                status_icon = {"pending": "🟡", "completed": "✅", "cancelled": "❌"}.get(r.get("status", ""), "")
                memo_part = f" | {r['memo'][:20]}" if r.get("memo") else ""
                st.markdown(f"{status_icon} **{name}** — {r.get('purpose', '')}{memo_part}")
        else:
            st.caption("일정 없음")

    # 월간 요약
    if rows:
        pending_total = sum(d.get("pending", 0) for d in date_map.values())
        done_total = sum(d.get("completed", 0) for d in date_map.values())
        st.markdown(
            f"<div style='text-align:center; padding:8px; color:#9ca3af; font-size:13px;'>"
            f"대기 <b style=\"color:#f59e0b\">{pending_total}</b>건 · "
            f"완료 <b style=\"color:#059669\">{done_total}</b>건"
            f"</div>",
            unsafe_allow_html=True,
        )


def _build_calendar_html(
    cal_matrix: list, year: int, month: int,
    today_str: str, date_map: dict, selected: str | None,
) -> str:
    """HTML 캘린더 그리드 생성"""
    days = ["월", "화", "수", "목", "금", "토", "일"]
    header = "".join(
        f"<div style='flex:1;text-align:center;font-size:12px;font-weight:600;"
        f"color:{"#ef4444" if i >= 5 else "#9ca3af"};padding:8px 0;'>{d}</div>"
        for i, d in enumerate(days)
    )

    weeks_html = ""
    for week in cal_matrix:
        cells = ""
        for i, day in enumerate(week):
            if day == 0:
                cells += "<div style='flex:1;padding:6px;min-height:36px;'></div>"
                continue

            day_str = f"{year}-{month:02d}-{day:02d}"
            info = date_map.get(day_str, {})
            pending = info.get("pending", 0)
            done = info.get("completed", 0)
            is_today = day_str == today_str
            is_selected = day_str == selected
            is_weekend = i >= 5

            # 스타일 결정
            bg = "#4f46e5" if is_today else "#eef2ff" if is_selected else "transparent"
            color = "#ffffff" if is_today else "#ef4444" if is_weekend else "#1a1a2e"
            border = "2px solid #4f46e5" if is_selected and not is_today else "none"
            font_weight = "700" if is_today or pending else "400"

            # 뱃지
            badge = ""
            if pending:
                badge = f"<div style='width:6px;height:6px;border-radius:50%;background:#f59e0b;margin:2px auto 0;'></div>"
            elif done:
                badge = f"<div style='width:6px;height:6px;border-radius:50%;background:#059669;margin:2px auto 0;'></div>"

            cells += (
                f"<div style='flex:1;text-align:center;padding:4px 0;'>"
                f"<div style='display:inline-flex;flex-direction:column;align-items:center;"
                f"width:32px;height:40px;justify-content:center;"
                f"background:{bg};border-radius:10px;border:{border};"
                f"color:{color};font-size:14px;font-weight:{font_weight};'>"
                f"{day}{badge}</div></div>"
            )
        weeks_html += f"<div style='display:flex;'>{cells}</div>"

    return (
        f"<div style='background:#ffffff;border-radius:12px;padding:12px 8px;"
        f"border:1px solid #eef0f4;'>"
        f"<div style='display:flex;border-bottom:1px solid #eef0f4;margin-bottom:4px;'>{header}</div>"
        f"{weeks_html}</div>"
    )
