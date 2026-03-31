"""고객관리 탭 — 목록/상세/등록/수정/상담기록"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.crypto import encrypt_phone, decrypt_phone, hash_phone_last4

TOUCH_OPTIONS = ["콜", "방문", "문자", "이메일", "기타"]
DB_SOURCE_OPTIONS = ["DB고객", "개인(지인)", "개척", "소개", "기타"]


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

def _render_list():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search = st.text_input("검색 (이름)", placeholder="이름으로 검색", label_visibility="collapsed")
    with col2:
        grade_filter = st.selectbox("등급", ["전체", "A", "B", "C", "D"], label_visibility="collapsed")
    with col3:
        source_filter = st.selectbox("유입경로", ["전체"] + DB_SOURCE_OPTIONS, label_visibility="collapsed")

    with st.expander("상세 필터"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            age_filter = st.selectbox("나이대", ["전체", "20대", "30대", "40대", "50대", "60대 이상"])
        with col_b:
            region_filter = st.text_input("지역", placeholder="예: 수원")
        with col_c:
            contact_filter = st.selectbox("상담 기록", ["전체", "있음", "없음"])
        sort_by = st.selectbox("정렬", ["등록일 최신순", "이름순", "등급순", "최근 상담순"])

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

    if sort_by == "이름순":
        query = query.order("name")
    elif sort_by == "등급순":
        query = query.order("prospect_grade")
    else:
        query = query.order("created_at", desc=True)

    try:
        res = query.limit(200).execute()
        clients = res.data or []
    except Exception as e:
        st.error(f"조회 실패: {e}")
        return

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
        st.info("등록된 고객이 없습니다.")
        return

    st.caption(f"{len(clients)}명")

    for c in clients:
        grade = c.get("prospect_grade", "C")
        grade_color = {"A": "red", "B": "orange", "C": "blue", "D": "gray"}.get(grade, "blue")
        col_name, col_info, col_detail, col_del = st.columns([3, 4, 1, 1])
        with col_name:
            st.markdown(f"**{c['name']}** :{grade_color}[{grade}]")
        with col_info:
            source = c.get("db_source", "")
            age = c.get("age_group") or (f"{c['age']}세" if c.get("age") else "")
            info = age
            if source:
                info += f" | {source}"
            if c.get("address"):
                info += f" | {c['address']}"
            st.caption(info)
        with col_detail:
            if st.button("상세", key=f"detail_{c['id']}"):
                st.session_state.clients_view = "detail"
                st.session_state.selected_client_id = c["id"]
                st.rerun()
        with col_del:
            confirm_key = f"confirm_del_list_{c['id']}"
            if st.session_state.get(confirm_key):
                if st.button("확인", key=f"del_confirm_{c['id']}", type="primary"):
                    try:
                        sb.table("contact_logs").delete().eq("client_id", c["id"]).execute()
                        sb.table("clients").delete().eq("id", c["id"]).execute()
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 실패: {e}")
            else:
                if st.button("삭제", key=f"del_{c['id']}"):
                    st.session_state[confirm_key] = True
                    st.rerun()


# ── 고객 상세 ──

def _render_detail():
    sb = get_supabase_client()
    client_id = st.session_state.get("selected_client_id")

    if st.button("← 목록으로"):
        st.session_state.clients_view = "list"
        st.rerun()

    try:
        res = sb.table("clients").select("*").eq("id", client_id).single().execute()
        client = res.data
    except Exception as e:
        st.error(f"조회 실패: {e}")
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

    st.divider()
    _render_contact_logs(sb, client_id)
    _render_new_contact(sb, client_id)

    st.divider()
    _render_client_delete(sb, client_id)


def _render_client_delete(sb, client_id: str):
    """고객 삭제 (확인 후 contact_logs CASCADE 삭제)"""
    confirm_key = f"confirm_del_client_{client_id}"
    if st.session_state.get(confirm_key):
        st.warning("고객 정보와 모든 상담 이력이 삭제됩니다. 계속하시겠습니까?")
        col_y, col_n = st.columns(2)
        if col_y.button("삭제 확인", type="primary", use_container_width=True):
            try:
                sb.table("contact_logs").delete().eq("client_id", client_id).execute()
                sb.table("clients").delete().eq("id", client_id).execute()
                st.session_state.pop(confirm_key, None)
                st.session_state.clients_view = "list"
                st.rerun()
            except Exception as e:
                st.error(f"삭제 실패: {e}")
        if col_n.button("취소", use_container_width=True):
            st.session_state.pop(confirm_key, None)
            st.rerun()
    else:
        if st.button("고객 삭제", use_container_width=True):
            st.session_state[confirm_key] = True
            st.rerun()


def _render_contact_logs(sb, client_id: str):
    st.subheader("상담 이력")
    try:
        res = sb.table("contact_logs").select("*").eq("client_id", client_id).order("created_at", desc=True).limit(50).execute()
        logs = res.data or []
    except Exception as e:
        st.error(f"이력 조회 실패: {e}")
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
            if log.get("next_action"):
                st.caption(f"다음 할 일: {log['next_action']}")
            if log.get("next_date"):
                st.caption(f"예정일: {log['next_date']}")

            confirm_key = f"confirm_del_log_{log['id']}"
            if st.session_state.get(confirm_key):
                st.warning("이 상담 기록을 삭제하시겠습니까?")
                col_y, col_n = st.columns(2)
                if col_y.button("삭제 확인", key=f"log_del_yes_{log['id']}", type="primary"):
                    try:
                        sb.table("contact_logs").delete().eq("id", log["id"]).execute()
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 실패: {e}")
                if col_n.button("취소", key=f"log_del_no_{log['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
            else:
                if st.button("삭제", key=f"del_log_{log['id']}"):
                    st.session_state[confirm_key] = True
                    st.rerun()


def _render_new_contact(sb, client_id: str):
    st.subheader("상담 기록 추가")
    with st.form("new_contact"):
        touch_method = st.selectbox("방식", TOUCH_OPTIONS)
        memo = st.text_area("상담 내용", placeholder="상담 내용을 입력하세요")
        next_action = st.text_input("다음 할 일", placeholder="선택 사항")
        next_date = st.date_input("예정일", value=None)

        if st.form_submit_button("저장", use_container_width=True, type="primary"):
            if not memo:
                st.error("상담 내용을 입력해주세요.")
            else:
                try:
                    sb.table("contact_logs").insert({
                        "fc_id": get_current_user_id(),
                        "client_id": client_id,
                        "touch_method": touch_method,
                        "memo": memo,
                        "next_action": next_action,
                        "next_date": str(next_date) if next_date else None,
                    }).execute()
                    st.success("저장되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")


# ── 고객 등록/수정 ──

def _render_form(edit=False):
    sb = get_supabase_client()

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
                "등급", ["A", "B", "C", "D"],
                index=["A", "B", "C", "D"].index(client.get("prospect_grade", "C")),
            )
            current_source = client.get("db_source", "")
            source_idx = DB_SOURCE_OPTIONS.index(current_source) if current_source in DB_SOURCE_OPTIONS else 0
            db_source = st.selectbox("유입경로", DB_SOURCE_OPTIONS, index=source_idx)
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
                        sb.table("clients").update(data).eq("id", client["id"]).execute()
                    else:
                        data["fc_id"] = get_current_user_id()
                        sb.table("clients").insert(data).execute()
                    st.success("저장되었습니다.")
                    st.session_state.clients_view = "list"
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")
