"""홈 — 리마인드 추가/수정/완료 폼 + 최근 활동 + 지난 카드"""
from datetime import date
import streamlit as st

from auth import get_current_user_id
from services.fp_reminder_service import (
    update_reminder, purposes, create_reminder, RESULT_OPTIONS, RESULT_MAP,
)
from utils.helpers import safe_error
from utils.supabase_client import get_supabase_client

_TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]


def _search_client(sb, fc_id, search, key_prefix="home_remind"):
    if not search.strip():
        return None
    try:
        results = (sb.table("clients").select("id, name, prospect_grade")
                   .eq("fc_id", fc_id).ilike("name", f"%{search.strip()}%")
                   .limit(10).execute().data or [])
    except Exception:
        results = []
    if results:
        opts = {f"{r['name']} [{r.get('prospect_grade','')}]": r["id"] for r in results}
        lbl = st.selectbox("고객 선택", list(opts.keys()), key=f"{key_prefix}_client")
        return opts[lbl]
    st.caption("검색 결과 없음")
    return None


def render_add_reminder_form(fc_id: str):
    from views.page_settings_products import get_active_products
    sb = get_supabase_client()

    search = st.text_input("고객 이름 검색", placeholder="이름 입력 후 선택", key="home_remind_search")
    client_id = _search_client(sb, fc_id, search)
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
                st.error("리마인드 등록에 실패했습니다.")


def render_edit_form(r: dict, edit_key: str):
    from datetime import date as _date
    from views.page_settings_products import get_active_products
    rid = r["id"]
    sb = get_supabase_client()
    fc_id = r.get("fc_id") or get_current_user_id()
    products = get_active_products(sb, fc_id)
    prod_map = {p["name"]: p["id"] for p in products}
    id_to_name = {p["id"]: p["name"] for p in products}
    current_names = [id_to_name[pid] for pid in (r.get("product_ids") or []) if pid in id_to_name]
    is_done = r.get("status") in ("completed", "cancelled")

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

        # 완료된 리마인드는 결과/후기도 수정 가능
        new_result = new_result_memo = None
        if is_done:
            result_keys = [k for k, _ in RESULT_OPTIONS]
            cur_result = r.get("result", "")
            r_idx = result_keys.index(cur_result) if cur_result in result_keys else 0
            new_result = st.selectbox("결과", result_keys,
                                      index=r_idx, format_func=lambda x: RESULT_MAP.get(x, x))
            new_result_memo = st.text_input("FC 후기", value=r.get("result_memo") or "")

        c1, c2 = st.columns(2)
        if c1.form_submit_button("저장", type="primary", use_container_width=True):
            pids = [prod_map[n] for n in new_prods if n in prod_map] or None
            new_date_str = str(new_date) if new_date else None
            res = update_reminder(fc_id, rid, new_date_str, new_purpose, pids, new_memo,
                                  result=new_result, result_memo=new_result_memo)
            if res is True:
                st.session_state.pop(edit_key, None)
                st.rerun()
            else:
                st.error(f"저장 실패: {res}")
        if c2.form_submit_button("취소", use_container_width=True):
            st.session_state.pop(edit_key, None)
            st.rerun()


def render_past_card(r: dict, products_map: dict = None):
    """완료/취소된 리마인드 카드 — 수정 가능"""
    from utils.ui_components import grade_badge as _grade_badge

    rid = r["id"]
    client = r.get("clients") or {}
    name = client.get("name", "이름 없음")
    grade = client.get("prospect_grade", "")
    purpose = r.get("purpose", "")
    status = r.get("status", "")
    result = r.get("result", "")
    result_memo = r.get("result_memo", "")
    memo = r.get("memo", "")
    d = r.get("reminder_date", "")
    completed_at = (r.get("completed_at") or "")[:10]

    prod_label = ""
    if r.get("product_ids") and products_map:
        names = [products_map[pid] for pid in r["product_ids"] if pid in products_map]
        if names:
            prod_label = " | " + ", ".join(names)

    grade_html = _grade_badge(grade) if grade else ""
    status_icon = "✅" if status == "completed" else "❌"
    result_label = RESULT_MAP.get(result, "") if result else ""
    edit_key = f"edit_past_{rid}"

    with st.container(border=True):
        col_info, col_btn = st.columns([5, 1])
        with col_info:
            from utils.helpers import esc
            header = f"{status_icon} **{esc(name)}** {grade_html} — {esc(purpose)}{esc(prod_label)}"
            st.markdown(header, unsafe_allow_html=True)
            info_parts = []
            if d:
                info_parts.append(f"예정: {d}")
            if completed_at:
                info_parts.append(f"완료: {completed_at}")
            if result_label:
                info_parts.append(f"결과: {result_label}")
            st.caption(" | ".join(info_parts))
            if result_memo:
                st.caption(f"FC 후기: {result_memo}")
            elif memo:
                st.caption(f"메모: {memo}")
        with col_btn:
            def _toggle_edit(ek):
                st.session_state[ek] = not st.session_state.get(ek, False)
            st.button("수정", key=f"edit_past_btn_{rid}",
                      use_container_width=True, on_click=_toggle_edit, args=(edit_key,))

        if st.session_state.get(edit_key):
            render_edit_form(r, edit_key)


def render_recent_activity(fc_id: str):
    sb = get_supabase_client()
    col_title, col_new, col_act = st.columns([3, 1, 1])
    col_title.subheader("최근 활동")
    if col_new.button("고객 추가", use_container_width=True):
        st.session_state._nav_to = "고객관리"
        st.session_state.clients_view = "new"
        st.rerun()
    if col_act.button("활동 추가", use_container_width=True):
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
    client_id = _search_client(sb, fc_id, search, key_prefix="home_act")
    if client_id:
        with st.form("home_quick_act"):
            method = st.selectbox("연락 방식", _TOUCH_OPTIONS)
            memo = st.text_input("내용")
            if st.form_submit_button("등록", type="primary", use_container_width=True):
                with st.spinner("등록 중..."):
                    try:
                        sb.table("contact_logs").insert({
                            "fc_id": fc_id, "client_id": client_id,
                            "touch_method": method, "memo": memo,
                        }).execute()
                        for k in ("home_act_open", "home_act_search", "home_act_client"):
                            st.session_state.pop(k, None)
                        st.rerun()
                    except Exception as e:
                        st.error(safe_error("등록", e))
