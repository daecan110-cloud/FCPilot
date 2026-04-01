"""FCPilot 홈 — 오늘의 할 일 대시보드"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from services.fp_reminder_service import get_bucketed, complete_reminder, cancel_reminder, update_reminder, purposes, create_reminder
from services.remind_trigger import check_and_send_daily_reminder
from utils.calendar_render import render_monthly_calendar
from utils.supabase_client import get_supabase_client
from utils.ui_components import grade_badge as _grade_badge, empty_state, section_header

_TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]


def render():
    st.header("오늘의 할 일")
    st.caption(f"{date.today().strftime('%Y년 %m월 %d일')}")

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

    # 요약 메트릭
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오늘 예정", f"{len(today)}건")
    c2.metric("이번 주", f"{len(this_week)}건")
    c3.metric("이번달", f"{len(this_month)}건")
    c4.metric("기간 없음", f"{len(no_date)}건")

    # 상품 맵 한 번만 로드 (N+1 방지)
    _sb = get_supabase_client()
    from views.page_settings_products import get_active_products
    _products_map = {p["id"]: p["name"] for p in get_active_products(_sb, fc_id)}

    with st.expander("📅 이번달 일정"):
        render_monthly_calendar(fc_id)

    # 리마인드 추가
    with st.expander("➕ 리마인드 추가"):
        _render_add_reminder_form(fc_id)

    st.divider()

    section_header("🟡 오늘 예정", f"{len(today)}건")
    for r in today:
        _render_reminder_card(r, "today", _products_map)
    if not today:
        empty_state("📋", "오늘 예정된 리마인드가 없습니다")

    st.divider()
    section_header("🔵 이번 주", f"{len(this_week)}건")
    for r in this_week:
        _render_reminder_card(r, "week", _products_map)
    if not this_week:
        empty_state("📅", "이번 주 예정된 리마인드가 없습니다")

    st.divider()
    section_header("📅 이번달", f"{len(this_month)}건")
    for r in this_month:
        _render_reminder_card(r, "month", _products_map)
    if not this_month:
        empty_state("📅", "이번달 추가 예정이 없습니다")

    st.divider()
    section_header("📌 기간 없음", f"{len(no_date)}건")
    for r in no_date:
        _render_reminder_card(r, "nodate", _products_map)
    if not no_date:
        empty_state("📌", "기간 없는 리마인드가 없습니다")

    st.divider()
    _render_recent_activity(fc_id)


def _render_reminder_card(r: dict, bucket: str, products_map: dict = None):
    rid = r["id"]
    client = r.get("clients") or {}
    name = client.get("name", "이름 없음")
    grade = client.get("prospect_grade", "")
    purpose = r.get("purpose", "")
    memo = r.get("memo", "")
    d = r.get("reminder_date", "")

    # 제안 상품 이름 — 미리 로드된 맵 사용 (쿼리 없음)
    prod_label = ""
    if r.get("product_ids") and products_map:
        names = [products_map[pid] for pid in r["product_ids"] if pid in products_map]
        if names:
            prod_label = " | " + ", ".join(names)

    grade_html = _grade_badge(grade) if grade else ""
    edit_key = f"edit_reminder_{rid}"

    with st.container(border=True):
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(f"**{name}** {grade_html} — {purpose}{prod_label}", unsafe_allow_html=True)
            if memo:
                st.caption(memo)
            st.caption(f"예정일: {d}" if d else "예정일: 미정")
        with col_btn:
            fc_id = r.get("fc_id", "")
            if st.button("완료", key=f"done_{rid}_{bucket}", type="primary", use_container_width=True):
                complete_reminder(fc_id, rid)
                st.rerun()
            if st.button("수정", key=f"edit_{rid}_{bucket}", use_container_width=True):
                st.session_state[edit_key] = not st.session_state.get(edit_key, False)
                st.rerun()
            if st.button("고객", key=f"goto_{rid}_{bucket}", use_container_width=True):
                st.session_state.clients_view = "detail"
                st.session_state.selected_client_id = r.get("client_id")
                st.session_state._nav_to = "👥 고객관리"
                st.rerun()

        if st.session_state.get(edit_key):
            _render_edit_form(r, edit_key)


def _render_add_reminder_form(fc_id: str):
    from views.page_settings_products import get_active_products
    sb = get_supabase_client()

    search = st.text_input("고객 이름 검색", placeholder="이름 입력 후 선택", key="home_remind_search")
    client_id = client_label = None
    if search.strip():
        try:
            results = (sb.table("clients").select("id, name, prospect_grade")
                       .eq("fc_id", fc_id).ilike("name", f"%{search.strip()}%")
                       .limit(10).execute().data or [])
        except Exception:
            results = []
        if results:
            opts = {f"{r['name']} [{r.get('prospect_grade','')}]": r["id"] for r in results}
            lbl = st.selectbox("고객 선택", list(opts.keys()), key="home_remind_client")
            client_id, client_label = opts[lbl], lbl
        else:
            st.caption("검색 결과가 없습니다.")

    if not client_id:
        return

    products = get_active_products(sb, fc_id)
    prod_map = {p["name"]: p["id"] for p in products}
    with st.form("home_add_reminder"):
        no_date = st.checkbox("날짜 없음 (언제 연락할지 미정)")
        r_date = None if no_date else st.date_input("예정일", value=date.today())
        r_purpose = st.selectbox("상담 목적", purposes())
        sel_prods = st.multiselect("제안 상품", list(prod_map.keys())) if products else []
        r_memo = st.text_input("메모", placeholder="선택 사항")
        if st.form_submit_button("등록", type="primary", use_container_width=True):
            pids = [prod_map[n] for n in sel_prods if n in prod_map] or None
            r_date_str = str(r_date) if r_date else None
            if create_reminder(fc_id, client_id, r_date_str, r_purpose, pids, r_memo):
                st.session_state.pop("home_remind_search", None)
                st.session_state.pop("home_remind_client", None)
                st.rerun()
            else:
                st.error("등록 실패")


def _render_edit_form(r: dict, edit_key: str):
    from datetime import date as _date
    from views.page_settings_products import get_active_products
    rid = r["id"]
    sb = get_supabase_client()
    fc_id = r.get("fc_id", "")
    products = get_active_products(sb, fc_id)
    prod_map = {p["name"]: p["id"] for p in products}
    id_to_name = {p["id"]: p["name"] for p in products}
    current_names = [id_to_name[pid] for pid in (r.get("product_ids") or []) if pid in id_to_name]
    with st.form(f"edit_form_{rid}"):
        has_date = bool(r.get("reminder_date"))
        no_date = st.checkbox("날짜 없음", value=not has_date)
        if not no_date:
            try:
                default_date = _date.fromisoformat(r.get("reminder_date") or str(_date.today()))
            except Exception:
                default_date = _date.today()
            new_date = st.date_input("예정일", value=default_date)
        else:
            new_date = None
        p_idx = purposes().index(r["purpose"]) if r.get("purpose") in purposes() else 0
        new_purpose = st.selectbox("상담 목적", purposes(), index=p_idx)
        new_prods = st.multiselect("제안 상품", list(prod_map.keys()), default=current_names) if products else []
        new_memo = st.text_input("메모", value=r.get("memo") or "")
        c1, c2 = st.columns(2)
        if c1.form_submit_button("저장", type="primary", use_container_width=True):
            pids = [prod_map[n] for n in new_prods if n in prod_map] or None
            fc_id = r.get("fc_id", "")
            new_date_str = str(new_date) if new_date else None
            if update_reminder(fc_id, rid, new_date_str, new_purpose, pids, new_memo):
                st.session_state.pop(edit_key, None)
                st.rerun()
            else:
                st.error("저장 실패")
        if c2.form_submit_button("취소", use_container_width=True):
            st.session_state.pop(edit_key, None)
            st.rerun()


def _render_recent_activity(fc_id: str):
    sb = get_supabase_client()
    col_title, col_new, col_act = st.columns([3, 1, 1])
    col_title.subheader("최근 활동")
    if col_new.button("👤 고객 추가", use_container_width=True):
        st.session_state._nav_to = "👥 고객관리"
        st.session_state.clients_view = "new"
        st.rerun()
    if col_act.button("📝 활동 추가", use_container_width=True):
        st.session_state.home_act_open = not st.session_state.get("home_act_open", False)
        st.rerun()

    if st.session_state.get("home_act_open"):
        _render_quick_activity(fc_id, sb)

    try:
        logs = (sb.table("contact_logs").select("*, clients(name)")
                .eq("fc_id", fc_id).order("created_at", desc=True)
                .limit(5).execute().data or [])
    except Exception:
        logs = []
    if not logs:
        st.info("최근 활동 기록이 없습니다.")
        return
    for log in logs:
        c = log.get("clients") or {}
        st.caption(f"{log.get('created_at','')[:10]} | {c.get('name','')} | {log.get('touch_method','')} | {(log.get('memo') or '')[:30]}")


def _render_quick_activity(fc_id: str, sb):
    search = st.text_input("고객 검색", key="home_act_search", placeholder="이름 입력")
    client_id = None
    if search.strip():
        try:
            results = (sb.table("clients").select("id, name").eq("fc_id", fc_id)
                       .ilike("name", f"%{search.strip()}%").limit(5).execute().data or [])
        except Exception:
            results = []
        if results:
            opts = {r["name"]: r["id"] for r in results}
            sel = st.selectbox("고객 선택", list(opts.keys()), key="home_act_client")
            client_id = opts[sel]
        else:
            st.caption("검색 결과 없음")
    if client_id:
        with st.form("home_quick_act"):
            method = st.selectbox("연락 방식", _TOUCH_OPTIONS)
            memo = st.text_input("내용")
            if st.form_submit_button("등록", type="primary", use_container_width=True):
                try:
                    sb.table("contact_logs").insert({
                        "fc_id": fc_id, "client_id": client_id,
                        "touch_method": method, "memo": memo,
                    }).execute()
                    for k in ("home_act_open", "home_act_search", "home_act_client"):
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"등록 실패: {e}")
