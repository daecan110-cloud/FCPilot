"""고객관리 탭 — 목록/상세/등록/수정/상담기록"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.crypto import encrypt_phone, decrypt_phone, hash_phone_last4
from utils.helpers import safe_error

TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]
DEFAULT_SOURCE_OPTIONS = ["DB고객", "개인(지인)", "개척", "소개", "기타"]


def _get_source_categories(sb, fc_id: str) -> list:
    """유입경로 카테고리 — DB 설정 우선, 없으면 기본값"""
    cache_key = f"source_cats_{fc_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        res = sb.table("users_settings").select("source_categories").eq("id", fc_id).execute()
        if res.data and res.data[0].get("source_categories"):
            cats = res.data[0]["source_categories"]
            st.session_state[cache_key] = cats
            return cats
    except Exception:
        pass
    return DEFAULT_SOURCE_OPTIONS


def render():
    st.header("고객관리")

    view = st.session_state.get("clients_view", "list")

    if view == "detail":
        _render_detail()
    elif view == "new":
        _render_form()
    elif view == "edit":
        _render_form(edit=True)
    else:
        _render_list()


# ── 고객 목록 ──

_SORT_OPTIONS = ["등록일 최신순", "이름순", "등급순", "최근 상담순"]


def _load_sort_pref(sb, fc_id: str) -> str:
    """DB에서 정렬 설정 로드 (세션에 없을 때만)"""
    if "clients_sort_by" in st.session_state:
        return st.session_state.clients_sort_by
    try:
        res = sb.table("users_settings").select("clients_sort").eq("id", fc_id).execute()
        saved = (res.data[0].get("clients_sort") or _SORT_OPTIONS[0]) if res.data else _SORT_OPTIONS[0]
    except Exception:
        saved = _SORT_OPTIONS[0]
    st.session_state.clients_sort_by = saved
    return saved


def _save_sort_pref(sb, fc_id: str, sort_val: str):
    """정렬 설정 DB 저장"""
    try:
        sb.table("users_settings").upsert({"id": fc_id, "clients_sort": sort_val}).execute()
    except Exception:
        pass


def _render_list():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    source_options = _get_source_categories(sb, fc_id)
    _load_sort_pref(sb, fc_id)  # session_state.clients_sort_by 초기화

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search = st.text_input("검색 (이름)", placeholder="이름으로 검색", label_visibility="collapsed")
    with col2:
        grade_filter = st.selectbox("등급", ["전체", "VIP", "S", "A", "B", "C", "D"], label_visibility="collapsed")
    with col3:
        source_filter = st.selectbox("유입경로", ["전체"] + source_options, label_visibility="collapsed")
    with col4:
        sort_by = st.selectbox(
            "정렬", _SORT_OPTIONS,
            label_visibility="collapsed",
            key="clients_sort_by",
        )

    # 변경 시 DB에 즉시 저장
    if sort_by != st.session_state.get("_sort_pref_saved"):
        _save_sort_pref(sb, fc_id, sort_by)
        st.session_state._sort_pref_saved = sort_by

    with st.expander("상세 필터"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            age_filter = st.selectbox("나이대", ["전체", "20대", "30대", "40대", "50대", "60대 이상"])
        with col_b:
            region_filter = st.text_input("지역", placeholder="예: 수원")
        with col_c:
            contact_filter = st.selectbox("상담 기록", ["전체", "있음", "없음"])

    if st.button("고객 등록", use_container_width=True, type="primary"):
        st.session_state.clients_view = "new"
        st.rerun()

    query = sb.table("clients").select("*").eq("fc_id", fc_id)
    if search:
        query = query.ilike("name", f"%{search}%")
    if grade_filter != "전체":
        query = query.eq("prospect_grade", grade_filter)
    if source_filter != "전체":
        query = query.ilike("db_source", f"%{source_filter}%")
    if age_filter != "전체":
        query = query.ilike("age_group", f"%{age_filter}%")
    if region_filter:
        query = query.ilike("address", f"%{region_filter}%")

    GRADE_ORDER = {"VIP": 0, "S": 1, "A": 2, "B": 3, "C": 4, "D": 5}

    if sort_by == "이름순":
        query = query.order("name")
    elif sort_by != "등급순":
        query = query.order("created_at", desc=True)

    try:
        res = query.limit(200).execute()
        clients = res.data or []
    except Exception as e:
        st.error(safe_error("조회", e))
        return

    if sort_by == "등급순":
        clients.sort(key=lambda c: GRADE_ORDER.get(c.get("prospect_grade", "D"), 5))

    if contact_filter != "전체" or sort_by == "최근 상담순":
        try:
            logs_res = sb.table("contact_logs").select("client_id, created_at").eq("fc_id", fc_id).order("created_at", desc=True).execute()
            logs_data = logs_res.data or []
            has_logs = {r["client_id"] for r in logs_data}

            if contact_filter == "있음":
                clients = [c for c in clients if c["id"] in has_logs]
            elif contact_filter == "없음":
                clients = [c for c in clients if c["id"] not in has_logs]

            if sort_by == "최근 상담순":
                latest_contact = {}
                for log in logs_data:
                    cid = log["client_id"]
                    if cid not in latest_contact:
                        latest_contact[cid] = log["created_at"]
                clients.sort(key=lambda c: latest_contact.get(c["id"], ""), reverse=True)
        except Exception:
            pass

    if not clients:
        from utils.ui_components import empty_state
        empty_state("👥", "등록된 고객이 없습니다")
        return

    st.caption(f"{len(clients)}명")

    from utils.ui_components import grade_badge as _grade_badge
    for c in clients:
        grade = c.get("prospect_grade", "C")
        grade_html = _grade_badge(grade)
        source = c.get("db_source", "")
        age = c.get("age_group") or (f"{c['age']}세" if c.get("age") else "")
        meta = " · ".join(filter(None, [age, source]))
        with st.container(border=True):
            c_info, c_btn = st.columns([5, 1])
            with c_info:
                from utils.helpers import esc
                st.markdown(
                    f'**{esc(c["name"])}** {grade_html} &nbsp;'
                    f'<span style="color:#787774; font-size:13px;">{esc(meta)}</span>',
                    unsafe_allow_html=True,
                )
            with c_btn:
                if st.button("상세", key=f"detail_{c['id']}", use_container_width=True):
                    st.session_state.clients_view = "detail"
                    st.session_state.selected_client_id = c["id"]
                    st.rerun()


# ── 고객 상세 ──

def _render_detail():
    sb = get_supabase_client()
    client_id = st.session_state.get("selected_client_id")

    if st.button("← 목록으로"):
        st.session_state.clients_view = "list"
        st.rerun()

    fc_id = get_current_user_id()
    try:
        res = sb.table("clients").select("*").eq("id", client_id).eq("fc_id", fc_id).single().execute()
        client = res.data
    except Exception as e:
        st.error(safe_error("조회", e))
        return

    if not client:
        st.warning("고객 정보를 찾을 수 없습니다.")
        return

    st.subheader(client["name"])
    col1, col2, col3 = st.columns(3)
    col1.metric("등급", client.get("prospect_grade", "-"))
    age_display = client.get("age_group") or (f"{client['age']}세" if client.get("age") else "-")
    col2.metric("나이", age_display)
    col3.metric("성별", {"M": "남", "F": "여"}.get(client.get("gender"), "-"))

    phone = ""
    if client.get("phone_encrypted"):
        try:
            phone = decrypt_phone(client["phone_encrypted"])
        except Exception:
            phone = "(복호화 실패)"
    st.text(f"연락처: {phone if phone else '미등록'}")
    st.text(f"직업: {client.get('occupation', '-')}")
    st.text(f"주소: {client.get('address', '-')}")
    st.text(f"유입경로: {client.get('db_source', '-')}")
    if client.get("memo"):
        st.text(f"메모: {client['memo']}")

    if st.button("수정", use_container_width=True):
        st.session_state.clients_view = "edit"
        st.session_state.edit_client = client
        st.rerun()

    st.markdown("---")
    tab_contact, tab_remind, tab_analysis, tab_del = st.tabs(["📝 상담이력", "🔔 리마인드", "📊 보장분석", "🗑️ 삭제"])
    with tab_contact:
        _render_contact_logs(sb, client_id)
        _render_new_contact(sb, client_id)
    with tab_remind:
        _render_reminder_section(sb, fc_id=fc_id, client_id=client_id)
    with tab_analysis:
        _render_analysis_history(sb, fc_id, client["name"])
    with tab_del:
        _render_client_delete(sb, client_id)


def _render_analysis_history(sb, fc_id: str, client_name: str):
    st.subheader("보장분석 이력")
    try:
        records = (sb.table("analysis_records").select("*")
                   .eq("fc_id", fc_id).ilike("client_name", client_name)
                   .order("created_at", desc=True).limit(10).execute().data or [])
    except Exception:
        records = []
    if not records:
        col_info, col_btn = st.columns([3, 1])
        col_info.caption("보장분석 이력이 없습니다.")
        if col_btn.button("보장분석 하기", use_container_width=True):
            st.session_state._nav_to = "📊 보장분석"
            st.rerun()
        return
    for r in records:
        created = r.get("created_at", "")[:10]
        summary = r.get("result_summary") or {}
        contracts = r.get("contract_count", 0)
        gender = summary.get("성별", "")
        age = summary.get("나이", "")
        with st.expander(f"📊 {created} | 계약 {contracts}건 {('| '+gender) if gender else ''} {(str(age)+'세') if age else ''}"):
            st.caption(f"고객명: {r.get('client_name','')}")
            st.caption(f"분석일: {created}")
            if r.get("excel_path"):
                try:
                    from utils.db_admin import get_admin_client
                    excel_bytes = get_admin_client().storage.from_("analysis-excel").download(r["excel_path"])
                    st.download_button(
                        "📥 엑셀 다운로드",
                        data=excel_bytes,
                        file_name=f"보장분석_{r.get('client_name','')}_{created}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_analysis_{r['id']}",
                        use_container_width=True,
                    )
                except Exception:
                    pass
            if st.button("보장분석 다시 실행", key=f"rerun_analysis_{r['id']}", use_container_width=True):
                st.session_state._nav_to = "📊 보장분석"
                st.rerun()


def _render_client_delete(sb, client_id: str):
    """고객 삭제 (확인 후 contact_logs CASCADE 삭제)"""
    fc_id = get_current_user_id()
    confirm_key = f"confirm_del_client_{client_id}"
    if st.session_state.get(confirm_key):
        st.warning("고객 정보와 모든 상담 이력이 삭제됩니다. 계속하시겠습니까?")
        col_y, col_n = st.columns(2)
        if col_y.button("삭제 확인", type="primary", use_container_width=True):
            try:
                sb.table("contact_logs").delete().eq("client_id", client_id).eq("fc_id", fc_id).execute()
                sb.table("clients").delete().eq("id", client_id).eq("fc_id", fc_id).execute()
                st.session_state.pop(confirm_key, None)
                st.session_state.clients_view = "list"
                st.rerun()
            except Exception as e:
                st.error(safe_error("삭제", e))
        if col_n.button("취소", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    else:
        if st.button("고객 삭제", use_container_width=True):
            st.session_state[confirm_key] = True
            st.rerun()


def _render_contact_logs(sb, client_id: str):
    fc_id = get_current_user_id()
    st.subheader("상담 이력")
    try:
        res = sb.table("contact_logs").select("*").eq("client_id", client_id).order("created_at", desc=True).limit(50).execute()
        logs = res.data or []
    except Exception as e:
        st.error(safe_error("이력 조회", e))
        return

    if not logs:
        st.caption("상담 이력이 없습니다.")
        return

    for i, log in enumerate(logs):
        method = log.get("touch_method", "") or "기타"
        date_str = log.get("created_at", "")[:10]
        label = f"{date_str} | {method}"
        with st.expander(label, expanded=(i == 0)):
            st.write(log.get("memo", ""))
            if log.get("proposed_product_ids"):
                try:
                    from views.page_settings_products import get_active_products
                    fc_id = get_current_user_id()
                    all_prods = {p["id"]: p["name"] for p in get_active_products(sb, fc_id)}
                    names = [all_prods.get(pid, pid[:8]) for pid in log["proposed_product_ids"]]
                    st.caption(f"제안 상품: {', '.join(names)}")
                except Exception:
                    pass
            if log.get("next_action"):
                st.caption(f"다음 할 일: {log['next_action']}")
            if log.get("next_date"):
                st.caption(f"예정일: {log['next_date']}")

            edit_log_key = f"edit_log_{log['id']}"
            confirm_key = f"confirm_del_log_{log['id']}"
            if st.session_state.get(edit_log_key):
                with st.form(f"edit_log_form_{log['id']}"):
                    cur_method = log.get("touch_method", "") or "기타"
                    idx = TOUCH_OPTIONS.index(cur_method) if cur_method in TOUCH_OPTIONS else 0
                    new_method = st.selectbox("연락 방식", TOUCH_OPTIONS, index=idx)
                    new_memo = st.text_area("상담 내용", value=log.get("memo") or "")
                    ec1, ec2 = st.columns(2)
                    if ec1.form_submit_button("저장", type="primary", use_container_width=True):
                        try:
                            sb.table("contact_logs").update({
                                "touch_method": new_method, "memo": new_memo,
                            }).eq("id", log["id"]).eq("fc_id", fc_id).execute()
                            st.session_state.pop(edit_log_key, None)
                            st.rerun()
                        except Exception as e:
                            st.error(safe_error("저장", e))
                    if ec2.form_submit_button("취소", use_container_width=True):
                        st.session_state.pop(edit_log_key, None)
                        st.rerun()
            elif st.session_state.get(confirm_key):
                st.warning("이 상담 기록을 삭제하시겠습니까?")
                col_y, col_n = st.columns(2)
                if col_y.button("삭제 확인", key=f"log_del_yes_{log['id']}", type="primary"):
                    try:
                        sb.table("contact_logs").delete().eq("id", log["id"]).eq("fc_id", fc_id).execute()
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(safe_error("삭제", e))
                if col_n.button("취소", key=f"log_del_no_{log['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
            else:
                bc1, bc2 = st.columns(2)
                if bc1.button("수정", key=f"edit_log_btn_{log['id']}", use_container_width=True):
                    st.session_state[edit_log_key] = True
                    st.rerun()
                if bc2.button("삭제", key=f"del_log_{log['id']}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()


def _render_new_contact(sb, client_id: str):
    st.subheader("상담 기록 추가")
    fc_id = get_current_user_id()

    # 제안 상품 목록 로드
    try:
        from views.page_settings_products import get_active_products
        products = get_active_products(sb, fc_id)
    except Exception:
        products = []
    prod_map = {p["name"]: p["id"] for p in products}

    with st.form("new_contact"):
        touch_method = st.selectbox("연락 방식", TOUCH_OPTIONS)
        memo = st.text_area("상담 내용", placeholder="상담 내용을 입력하세요")
        if products:
            selected_prods = st.multiselect("제안 상품 (복수 선택 가능)", list(prod_map.keys()))
        else:
            selected_prods = []
            st.caption("등록된 상품이 없습니다. 설정 > 상품 관리에서 추가하세요.")
        next_action = st.text_input("다음 할 일", placeholder="선택 사항")
        next_date = st.date_input("예정일", value=None)

        if st.form_submit_button("저장", use_container_width=True, type="primary"):
            if not memo:
                st.error("상담 내용을 입력해주세요.")
            else:
                try:
                    prod_ids = [prod_map[n] for n in selected_prods if n in prod_map] or None
                    sb.table("contact_logs").insert({
                        "fc_id": fc_id,
                        "client_id": client_id,
                        "touch_method": touch_method,
                        "memo": memo,
                        "proposed_product_ids": prod_ids,
                        "next_action": next_action,
                        "next_date": str(next_date) if next_date else None,
                    }).execute()
                    st.success("저장되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(safe_error("저장", e))


# ── 고객 등록/수정 ──

def _render_form(edit=False):
    sb = get_supabase_client()
    fc_id = get_current_user_id()
    source_options = _get_source_categories(sb, fc_id)

    if st.button("← 목록으로"):
        st.session_state.clients_view = "list"
        st.rerun()

    client = st.session_state.get("edit_client", {}) if edit else {}
    st.subheader("고객 수정" if edit else "고객 등록")

    phone_display = ""
    if edit and client.get("phone_encrypted"):
        try:
            phone_display = decrypt_phone(client["phone_encrypted"])
        except Exception:
            pass

    with st.expander("💡 등급 기준 보기"):
        st.caption("**VIP**: 기계약자 중 계약 3건 이상 또는 월 납입 보험료 50만원 이상. 최우선 케어 대상, 추가 계약·소개 기대 고객")
        st.caption("**S**: 기계약자 (계약 1~2건 또는 월 납입 50만원 미만). 유지 관리 + 추가 니즈 발굴 대상")
        st.caption("**A**: 보험 니즈 확인 + 상담 의향 있음 (계약 가능성 높음)")
        st.caption("**B**: 관심은 있으나 구체적 니즈 미확인")
        st.caption("**C**: 접촉만 됨, 니즈/의향 미파악")
        st.caption("**D**: 거절 또는 연락 두절")

    with st.form("client_form"):
        name = st.text_input("이름 *", value=client.get("name", ""))
        phone = st.text_input("전화번호", value=phone_display, placeholder="010-1234-5678")
        col1, col2 = st.columns(2)
        with col1:
            age_group = st.text_input("나이대", value=client.get("age_group", ""), placeholder="예: 30대, 40대")
            gender_val = client.get("gender") or None
            gender = st.selectbox(
                "성별", [None, "M", "F"],
                format_func=lambda x: {"M": "남", "F": "여", None: "선택"}[x],
                index=[None, "M", "F"].index(gender_val if gender_val in ("M", "F") else None),
            )
        with col2:
            grade = st.selectbox(
                "등급", ["VIP", "S", "A", "B", "C", "D"],
                index=["VIP", "S", "A", "B", "C", "D"].index(
                    client.get("prospect_grade", "C")
                    if client.get("prospect_grade") in ("VIP", "S", "A", "B", "C", "D") else "C"
                ),
            )
            current_source = client.get("db_source", "")
            source_idx = source_options.index(current_source) if current_source in source_options else 0
            db_source = st.selectbox("유입경로", source_options, index=source_idx)
        occupation = st.text_input("직업", value=client.get("occupation", ""))
        address = st.text_input("주소", value=client.get("address", ""))
        memo = st.text_area("메모", value=client.get("memo", ""))

        if st.form_submit_button("저장", use_container_width=True, type="primary"):
            if not name:
                st.error("이름은 필수입니다.")
            else:
                data = {
                    "name": name.strip(),
                    "phone_encrypted": encrypt_phone(phone) if phone else "",
                    "phone_last4_hash": hash_phone_last4(phone) if phone else "",
                    "age_group": age_group.strip(),
                    "gender": gender,
                    "prospect_grade": grade,
                    "db_source": db_source,
                    "occupation": occupation.strip(),
                    "address": address.strip(),
                    "memo": memo.strip(),
                }
                try:
                    if edit:
                        sb.table("clients").update(data).eq("id", client["id"]).eq("fc_id", get_current_user_id()).execute()
                    else:
                        data["fc_id"] = get_current_user_id()
                        sb.table("clients").insert(data).execute()
                    st.success("저장되었습니다.")
                    st.session_state.clients_view = "list"
                    st.rerun()
                except Exception as e:
                    st.error(safe_error("저장", e))

def _render_reminder_section(sb, fc_id: str, client_id: str):
    """리마인드 등록 + 목록"""
    from services.fp_reminder_service import get_client_reminders, create_reminder, complete_reminder, cancel_reminder, purposes
    from views.page_settings_products import get_active_products

    st.subheader("리마인드")

    # 기존 리마인드 목록
    reminders = get_client_reminders(fc_id, client_id)
    pending = [r for r in reminders if r.get("status") == "pending"]
    if pending:
        for r in pending:
            icon = "🔴" if r["reminder_date"] < str(__import__("datetime").date.today()) else "🟡"
            col_r, col_done, col_cancel = st.columns([5, 1, 1])
            col_r.caption(f"{icon} {r['reminder_date']} | {r.get('purpose','')} | {(r.get('memo') or '')[:30]}")
            if col_done.button("완료", key=f"r_done_{r['id']}", use_container_width=True):
                complete_reminder(fc_id, r["id"])
                st.rerun()
            if col_cancel.button("취소", key=f"r_cancel_{r['id']}", use_container_width=True):
                cancel_reminder(fc_id, r["id"])
                st.rerun()

    # 등록 폼
    with st.expander("➕ 리마인드 등록"):
        with st.form("reminder_form"):
            r_date = st.date_input("예정일")
            r_purpose = st.selectbox("상담 목적", purposes())
            products = get_active_products(sb, fc_id)
            prod_map = {p["name"]: p["id"] for p in products}
            selected = st.multiselect("제안 상품", list(prod_map.keys())) if products else []
            r_memo = st.text_input("메모", placeholder="선택 사항")
            if st.form_submit_button("등록", type="primary", use_container_width=True):
                pid_list = [prod_map[n] for n in selected if n in prod_map] or None
                ok = create_reminder(fc_id, client_id, str(r_date), r_purpose, pid_list, r_memo)
                if ok:
                    st.success("리마인드가 등록되었습니다.")
                    st.rerun()
                else:
                    st.error("등록 실패")
