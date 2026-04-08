"""고객 등록/수정 폼 (page_clients에서 분리)"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.crypto import encrypt_phone, decrypt_phone, hash_phone_last4
from utils.helpers import safe_error


def render_form(edit=False, source_options=None):
    sb = get_supabase_client()
    fc_id = get_current_user_id()
    if source_options is None:
        from views.page_clients import _get_source_categories
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
