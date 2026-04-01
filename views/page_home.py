"""FCPilot 홈 — 오늘의 할 일 대시보드"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from services.fp_reminder_service import get_bucketed, complete_reminder, cancel_reminder, update_reminder, purposes, create_reminder
from services.remind_trigger import check_and_send_daily_reminder
from utils.supabase_client import get_supabase_client
from utils.calendar_render import render_monthly_calendar

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
    overdue, today, this_week = buckets["overdue"], buckets["today"], buckets["this_week"]

    # 요약 메트릭
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오늘 예정", f"{len(today)}건")
    c2.metric("지연", f"{len(overdue)}건", delta=f"-{len(overdue)}" if overdue else None, delta_color="inverse")
    c3.metric("이번 주", f"{len(this_week)}건")
    c4.metric("전체 대기", f"{len(overdue)+len(today)+len(this_week)}건")

    with st.expander("📅 이번달 일정"):
        render_monthly_calendar(fc_id)

    # 리마인드 추가
    with st.expander("➕ 리마인드 추가"):
        _render_add_reminder_form(fc_id)

    st.divider()

    if overdue:
        st.subheader(f"🔴 지연 ({len(overdue)}건)")
        for r in overdue:
            _render_reminder_card(r, "overdue")
        st.divider()

    st.subheader(f"🟡 오늘 예정 ({len(today)}건)")
    for r in today:
        _render_reminder_card(r, "today")
    if not today:
        st.info("오늘 예정된 리마인드가 없습니다.")

    st.divider()
    st.subheader(f"🔵 이번 주 ({len(this_week)}건)")
    for r in this_week:
        _render_reminder_card(r, "week")
    if not this_week:
        st.info("이번 주 예정된 리마인드가 없습니다.")

    st.divider()
    _render_recent_activity(fc_id)


def _render_reminder_card(r: dict, bucket: str):
    rid = r["id"]
    client = r.get("clients") or {}
    name = client.get("name", "이름 없음")
    grade = client.get("prospect_grade", "")
    purpose = r.get("purpose", "")
    memo = r.get("memo", "")
    d = r.get("reminder_date", "")

    # 제안 상품 이름 조회
    prod_label = ""
    if r.get("product_ids"):
        try:
            sb = get_supabase_client()
            prods = (sb.table("fp_products").select("name")
                     .in_("id", r["product_ids"]).execute().data or [])
            prod_label = " | " + ", ".join(p["name"] for p in prods)
        except Exception:
            pass

    grade_badge = f" [{grade}]" if grade else ""
    edit_key = f"edit_reminder_{rid}"

    with st.container(border=True):
        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(f"**{name}**{grade_badge} — {purpose}{prod_label}")
            if memo:
                st.caption(memo)
            st.caption(f"예정일: {d}")
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
        r_date = st.date_input("예정일", value=date.today())
        r_purpose = st.selectbox("상담 목적", purposes())
        sel_prods = st.multiselect("제안 상품", list(prod_map.keys())) if products else []
        r_memo = st.text_input("메모", placeholder="선택 사항")
        if st.form_submit_button("등록", type="primary", use_container_width=True):
            pids = [prod_map[n] for n in sel_prods if n in prod_map] or None
            if create_reminder(fc_id, client_id, str(r_date), r_purpose, pids, r_memo):
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
        try:
            default_date = _date.fromisoformat(r.get("reminder_date", str(_date.today())))
        except Exception:
            default_date = _date.today()
        new_date = st.date_input("예정일", value=default_date)
        p_idx = purposes().index(r["purpose"]) if r.get("purpose") in purposes() else 0
        new_purpose = st.selectbox("상담 목적", purposes(), index=p_idx)
        new_prods = st.multiselect("제안 상품", list(prod_map.keys()), default=current_names) if products else []
        new_memo = st.text_input("메모", value=r.get("memo") or "")
        c1, c2 = st.columns(2)
        if c1.form_submit_button("저장", type="primary", use_container_width=True):
            pids = [prod_map[n] for n in new_prods if n in prod_map] or None
            fc_id = r.get("fc_id", "")
            if update_reminder(fc_id, rid, str(new_date), new_purpose, pids, new_memo):
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
