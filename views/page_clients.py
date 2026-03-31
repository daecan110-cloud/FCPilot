"""고객관리 탭 — 목록/상세/등록/수정/상담기록"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.crypto import encrypt_phone, decrypt_phone, hash_phone_last4
from utils.helpers import mask_phone


def render():
    st.header("고객관리")

    view = st.session_state.get("clients_view", "list")

    if view == "detail":
        _render_detail()
    elif view == "new":
        _render_form()
    elif view == "edit":
        _render_form(edit=True)
    elif view == "migrate":
        _render_migrate()
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
        source_filter = st.text_input("출처", placeholder="출처 필터", label_visibility="collapsed")

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("고객 등록", use_container_width=True, type="primary"):
            st.session_state.clients_view = "new"
            st.rerun()
    with btn_col2:
        if st.button("CSV 가져오기", use_container_width=True):
            st.session_state.clients_view = "migrate"
            st.rerun()

    # 데이터 조회
    query = sb.table("clients").select("*").eq("fc_id", fc_id).order("created_at", desc=True)
    if search:
        query = query.ilike("name", f"%{search}%")
    if grade_filter != "전체":
        query = query.eq("prospect_grade", grade_filter)
    if source_filter:
        query = query.ilike("source", f"%{source_filter}%")

    try:
        res = query.limit(100).execute()
        clients = res.data or []
    except Exception as e:
        st.error(f"조회 실패: {e}")
        return

    if not clients:
        st.info("등록된 고객이 없습니다.")
        return

    st.caption(f"{len(clients)}명")

    for c in clients:
        grade = c.get("prospect_grade", "C")
        grade_color = {"A": "red", "B": "orange", "C": "blue", "D": "gray"}.get(grade, "blue")
        col_name, col_info, col_btn = st.columns([3, 4, 1])
        with col_name:
            st.markdown(f"**{c['name']}** :{grade_color}[{grade}]")
        with col_info:
            source = c.get("source", "")
            age = c.get("age", "")
            info = f"{age}세" if age else ""
            if source:
                info += f" | {source}"
            st.caption(info)
        with col_btn:
            if st.button("상세", key=f"detail_{c['id']}"):
                st.session_state.clients_view = "detail"
                st.session_state.selected_client_id = c["id"]
                st.rerun()


# ── 고객 상세 ──

def _render_detail():
    sb = get_supabase_client()
    client_id = st.session_state.get("selected_client_id")

    if st.button("목록으로"):
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

    # 기본 정보
    st.subheader(client["name"])
    col1, col2, col3 = st.columns(3)
    col1.metric("등급", client.get("prospect_grade", "-"))
    col2.metric("나이", f"{client.get('age', '-')}세" if client.get("age") else "-")
    col3.metric("성별", {"M": "남", "F": "여"}.get(client.get("gender"), "-"))

    phone = ""
    if client.get("phone_encrypted"):
        try:
            phone = decrypt_phone(client["phone_encrypted"])
        except Exception:
            phone = "(복호화 실패)"
    st.text(f"연락처: {phone or '미등록'}")
    st.text(f"직업: {client.get('occupation', '-')}")
    st.text(f"주소: {client.get('address', '-')}")
    st.text(f"출처: {client.get('source', '-')}")
    if client.get("memo"):
        st.text(f"메모: {client['memo']}")

    col_edit, col_del = st.columns(2)
    with col_edit:
        if st.button("수정", use_container_width=True):
            st.session_state.clients_view = "edit"
            st.session_state.edit_client = client
            st.rerun()

    st.divider()

    # 상담 이력
    _render_contact_logs(sb, client_id)

    # 새 상담 기록
    _render_new_contact(sb, client_id)


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

    type_labels = {"visit": "방문", "call": "전화", "message": "문자", "email": "이메일", "other": "기타"}

    for log in logs:
        t = type_labels.get(log.get("contact_type", ""), "기타")
        date = log.get("created_at", "")[:10]
        with st.expander(f"{date} | {t}", expanded=False):
            st.write(log.get("content", ""))
            if log.get("next_action"):
                st.caption(f"다음 할 일: {log['next_action']}")
            if log.get("next_date"):
                st.caption(f"예정일: {log['next_date']}")


def _render_new_contact(sb, client_id: str):
    st.subheader("상담 기록 추가")
    with st.form("new_contact"):
        contact_type = st.selectbox(
            "방식",
            ["visit", "call", "message", "email", "other"],
            format_func=lambda x: {"visit": "방문", "call": "전화", "message": "문자", "email": "이메일", "other": "기타"}[x],
        )
        content = st.text_area("상담 내용", placeholder="상담 내용을 입력하세요")
        next_action = st.text_input("다음 할 일", placeholder="선택 사항")
        next_date = st.date_input("예정일", value=None)

        if st.form_submit_button("저장", use_container_width=True, type="primary"):
            if not content:
                st.error("상담 내용을 입력해주세요.")
            else:
                try:
                    sb.table("contact_logs").insert({
                        "fc_id": get_current_user_id(),
                        "client_id": client_id,
                        "contact_type": contact_type,
                        "content": content,
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

    if st.button("목록으로"):
        st.session_state.clients_view = "list"
        st.rerun()

    client = st.session_state.get("edit_client", {}) if edit else {}
    title = "고객 수정" if edit else "고객 등록"
    st.subheader(title)

    phone_display = ""
    if edit and client.get("phone_encrypted"):
        try:
            phone_display = decrypt_phone(client["phone_encrypted"])
        except Exception:
            pass

    with st.form("client_form"):
        name = st.text_input("이름 *", value=client.get("name", ""))
        phone = st.text_input("전화번호", value=phone_display, placeholder="010-1234-5678")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("나이", value=client.get("age") or 0, min_value=0, max_value=120)
            gender = st.selectbox("성별", [None, "M", "F"],
                                   format_func=lambda x: {"M": "남", "F": "여", None: "선택"}[x],
                                   index=[None, "M", "F"].index(client.get("gender")))
        with col2:
            grade = st.selectbox("등급", ["A", "B", "C", "D"],
                                  index=["A", "B", "C", "D"].index(client.get("prospect_grade", "C")))
            source = st.text_input("출처 (DB종류)", value=client.get("source", ""))
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
                    "age": age if age > 0 else None,
                    "gender": gender,
                    "prospect_grade": grade,
                    "source": source.strip(),
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


# ── CSV 마이그레이션 ──

def _render_migrate():
    if st.button("목록으로"):
        st.session_state.clients_view = "list"
        st.rerun()

    st.subheader("CSV 가져오기")
    st.caption("구글시트에서 CSV로 내보낸 파일을 업로드하세요.")
    st.caption("컬럼: 이름, 전화번호, 나이, 성별, 직업, 주소, 등급, 출처, 메모")

    csv_file = st.file_uploader("CSV 파일", type=["csv"])
    if csv_file and st.button("가져오기 시작", type="primary"):
        from services.migration import migrate_clients_csv
        with st.spinner("마이그레이션 중..."):
            result = migrate_clients_csv(csv_file.read())
        st.success(f"{result['success']}명 가져오기 완료")
        if result["errors"]:
            with st.expander(f"오류 {len(result['errors'])}건"):
                for e in result["errors"]:
                    st.caption(e)
