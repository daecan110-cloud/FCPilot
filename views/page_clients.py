"""고객관리 탭 — 라우터 + 목록 + 등록/수정 폼"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.crypto import encrypt_phone, decrypt_phone, hash_phone_last4
from utils.helpers import safe_error

TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]
from config import DEFAULT_SOURCE_CATEGORIES as DEFAULT_SOURCE_OPTIONS


def _get_source_categories(sb, fc_id: str) -> list:
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
        from views.page_clients_detail import render_detail
        render_detail()
    elif view == "new":
        _render_form()
    elif view == "edit":
        _render_form(edit=True)
    else:
        _render_list()


# ── 고객 목록 ──

_SORT_OPTIONS = ["등록일 최신순", "이름순", "등급순", "최근 상담순"]


def _load_sort_pref(sb, fc_id: str) -> str:
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
    try:
        sb.table("users_settings").upsert({"id": fc_id, "clients_sort": sort_val}).execute()
    except Exception:
        pass


def _render_list():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    source_options = _get_source_categories(sb, fc_id)
    _load_sort_pref(sb, fc_id)

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search = st.text_input("검색 (이름)", placeholder="이름으로 검색", label_visibility="collapsed")
    with col2:
        grade_filter = st.selectbox("등급", ["전체", "VIP", "S", "A", "B", "C", "D"], label_visibility="collapsed")
    with col3:
        source_filter = st.selectbox("유입경로", ["전체"] + source_options, label_visibility="collapsed")
    with col4:
        sort_by = st.selectbox("정렬", _SORT_OPTIONS, label_visibility="collapsed", key="clients_sort_by")

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
    from utils.helpers import esc
    for c in clients:
        grade = c.get("prospect_grade", "C")
        grade_html = _grade_badge(grade)
        source = c.get("db_source", "")
        age = c.get("age_group") or (f"{c['age']}세" if c.get("age") else "")
        meta = " · ".join(filter(None, [age, source]))
        with st.container(border=True):
            c_info, c_btn = st.columns([5, 1])
            with c_info:
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
        st.caption("**VIP**: 기계약자 중 계약 3건 이상 또는 월 납입 보험료 50만원 이상")
        st.caption("**S**: 기계약자 (계약 1~2건 또는 월 납입 50만원 미만)")
        st.caption("**A**: 보험 니즈 확인 + 상담 의향 있음")
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
                with st.spinner("저장 중..."):
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
