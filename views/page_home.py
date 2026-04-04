"""FCPilot 홈 — 오늘의 할 일 대시보드"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from services.fp_reminder_service import (
    get_bucketed, complete_reminder, cancel_reminder, update_reminder,
    purposes, create_reminder, get_past_reminders, RESULT_OPTIONS, RESULT_MAP,
)
from services.remind_trigger import check_and_send_daily_reminder
from utils.calendar_render import render_monthly_calendar
from utils.supabase_client import get_supabase_client
from utils.ui_components import grade_badge as _grade_badge, empty_state

_TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]


def render():
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(
            f'<div style="margin-bottom:4px;">'
            f'<span style="font-size:26px; font-weight:700; color:#1a1a2e;">오늘의 할 일</span>'
            f'</div>'
            f'<span style="font-size:14px; color:#9ca3af;">{date.today().strftime("%Y년 %m월 %d일")}</span>',
            unsafe_allow_html=True,
        )

    fc_id = get_current_user_id()
    if not fc_id:
        st.warning("로그인이 필요합니다.")
        return

    check_and_send_daily_reminder()

    buckets = get_bucketed(fc_id)
    today, this_week, this_month, no_date = (
        buckets["today"], buckets["this_week"],
        buckets["this_month"], buckets["no_date"],
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 오늘", f"{len(today)}건")
    c2.metric("🟡 이번 주", f"{len(this_week)}건")
    c3.metric("🔵 이번달", f"{len(this_month)}건")
    c4.metric("⚪ 미정", f"{len(no_date)}건")

    _sb = get_supabase_client()
    from views.page_settings_products import get_active_products
    _products_map = {p["id"]: p["name"] for p in get_active_products(_sb, fc_id)}

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.expander("이번달 일정"):
        render_monthly_calendar(fc_id)

    with st.expander("리마인드 추가"):
        from views.page_home_forms import render_add_reminder_form
        render_add_reminder_form(fc_id)

    # 탭 방식 리마인드
    past = get_past_reminders(fc_id)
    tab_today, tab_week, tab_month, tab_nodate, tab_past = st.tabs([
        f"🔴 오늘 ({len(today)})",
        f"🟡 이번 주 ({len(this_week)})",
        f"🔵 이번달 ({len(this_month)})",
        f"⚪ 미정 ({len(no_date)})",
        f"✅ 지난 리마인드 ({len(past)})",
    ])
    with tab_today:
        for r in today:
            _render_reminder_card(r, "today", _products_map)
        if not today:
            empty_state("📋", "오늘 예정된 리마인드가 없습니다")
    with tab_week:
        for r in this_week:
            _render_reminder_card(r, "week", _products_map)
        if not this_week:
            empty_state("📅", "이번 주 예정된 리마인드가 없습니다")
    with tab_month:
        for r in this_month:
            _render_reminder_card(r, "month", _products_map)
        if not this_month:
            empty_state("📅", "이번달 추가 예정이 없습니다")
    with tab_nodate:
        for r in no_date:
            _render_reminder_card(r, "nodate", _products_map)
        if not no_date:
            empty_state("📌", "기간 없는 리마인드가 없습니다")
    with tab_past:
        from views.page_home_forms import render_past_card
        for r in past:
            render_past_card(r, _products_map)
        if not past:
            empty_state("📋", "완료/취소된 리마인드가 없습니다")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    from views.page_home_forms import render_recent_activity
    render_recent_activity(fc_id)


def _render_reminder_card(r: dict, bucket: str, products_map: dict = None):
    rid = r["id"]
    client = r.get("clients") or {}
    name = client.get("name", "이름 없음")
    grade = client.get("prospect_grade", "")
    purpose = r.get("purpose", "")
    memo = r.get("memo", "")
    d = r.get("reminder_date", "")

    prod_label = ""
    if r.get("product_ids") and products_map:
        names = [products_map[pid] for pid in r["product_ids"] if pid in products_map]
        if names:
            prod_label = " | " + ", ".join(names)

    grade_html = _grade_badge(grade) if grade else ""
    edit_key = f"edit_reminder_{rid}"
    complete_key = f"complete_reminder_{rid}"

    fc_id = r.get("fc_id") or get_current_user_id()

    with st.container(border=True):
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            from utils.helpers import esc
            st.markdown(f"**{esc(name)}** {grade_html} — {esc(purpose)}{esc(prod_label)}", unsafe_allow_html=True)
            if memo:
                st.caption(memo)
            st.caption(f"예정일: {d}" if d else "예정일: 미정")
        with col_btn:
            def _toggle(key):
                st.session_state[key] = not st.session_state.get(key, False)

            st.button(
                "완료", key=f"done_{rid}_{bucket}", type="primary",
                use_container_width=True,
                on_click=_toggle, args=(complete_key,),
            )
            st.button(
                "수정", key=f"edit_{rid}_{bucket}",
                use_container_width=True,
                on_click=_toggle, args=(edit_key,),
            )
            st.button(
                "삭제", key=f"del_{rid}_{bucket}",
                use_container_width=True,
                on_click=cancel_reminder, args=(fc_id, rid),
            )

        # 완료 결과 입력 폼
        if st.session_state.get(complete_key):
            _render_complete_form(r, complete_key)

        if st.session_state.get(edit_key):
            from views.page_home_forms import render_edit_form
            render_edit_form(r, edit_key)


def _render_complete_form(r: dict, complete_key: str):
    """완료 시 결과 + FC 후기 입력"""
    rid = r["id"]
    fc_id = r.get("fc_id") or get_current_user_id()
    with st.form(f"complete_form_{rid}"):
        st.caption("결과를 기록하세요")
        result = st.selectbox(
            "결과",
            [k for k, _ in RESULT_OPTIONS],
            format_func=lambda x: RESULT_MAP.get(x, x),
        )
        result_memo = st.text_area(
            "FC 후기 / 메모",
            placeholder="왜 실패했나요? 다음에 어떻게 접근할까요? 계약 후기 등",
            height=100,
        )
        c1, c2 = st.columns(2)
        if c1.form_submit_button("완료 저장", type="primary", use_container_width=True):
            res = complete_reminder(fc_id, rid, result, result_memo)
            if res is True:
                st.session_state.pop(complete_key, None)
                st.rerun()
            else:
                st.error(f"저장 실패: {res}")
        if c2.form_submit_button("취소", use_container_width=True):
            st.session_state.pop(complete_key, None)
            st.rerun()


