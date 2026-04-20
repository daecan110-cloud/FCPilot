"""기계약자 계약 정보 관리 — S/VIP 등급 전용"""
import streamlit as st
from auth import get_current_user_id
from config import INSURANCE_CATEGORIES as _CATEGORIES, INSURANCE_CAT_ICON as _CAT_ICON
from utils.helpers import safe_error


def render_contracts(sb, client_id: str):
    """계약 정보 섹션 렌더링"""
    fc_id = get_current_user_id()

    try:
        rows = (sb.table("client_contracts")
                .select("*").eq("client_id", client_id).eq("fc_id", fc_id)
                .order("created_at", desc=True).execute().data or [])
    except Exception as e:
        st.error(safe_error("조회", e))
        return

    # 요약 메트릭
    total_premium = sum(r.get("monthly_premium", 0) for r in rows)
    st.caption(f"계약 {len(rows)}건 · 월 납입 합계 {total_premium:,}원")

    # 기존 계약 목록
    for r in rows:
        icon = _CAT_ICON.get(r.get("category", "기타"), "⚪")
        premium = r.get("monthly_premium", 0)
        label = f"{icon} {r.get('company','')} — {r.get('product_name','')} | 월 {premium:,}원"
        with st.expander(label):
            _render_contract_detail(r)
            _render_contract_actions(sb, fc_id, r)

    # 추가 방법 선택
    st.markdown("---")
    add_method = st.radio(
        "계약 추가", ["직접 입력", "상품설계서 PDF 업로드"],
        horizontal=True, label_visibility="collapsed",
    )
    if add_method == "직접 입력":
        _render_manual_form(sb, fc_id, client_id)
    else:
        _render_pdf_upload(sb, fc_id, client_id)


def _render_contract_detail(r: dict):
    """계약 상세 표시"""
    col1, col2 = st.columns(2)
    col1.text(f"보험사: {r.get('company', '-')}")
    col1.text(f"상품명: {r.get('product_name', '-')}")
    col1.text(f"카테고리: {r.get('category', '-')}")
    col2.text(f"월 보험료: {r.get('monthly_premium', 0):,}원")
    col2.text(f"계약일: {str(r.get('contract_date', '-'))[:10]}")

    main_cov = r.get("main_coverage", "")
    if main_cov:
        st.caption(f"**주계약**: {main_cov}")

    riders = r.get("riders") or []
    if riders:
        st.caption("**특약**:")
        for rider in riders:
            name = rider.get("name", "")
            amount = rider.get("amount", "")
            st.caption(f"  · {name} {f'({amount})' if amount else ''}")

    if r.get("memo"):
        st.caption(f"메모: {r['memo']}")


def _render_contract_actions(sb, fc_id: str, r: dict):
    """수정/삭제 버튼"""
    edit_key = f"edit_contract_{r['id']}"
    del_key = f"del_contract_{r['id']}"

    if st.session_state.get(edit_key):
        _render_edit_form(sb, fc_id, r)
    elif st.session_state.get(del_key):
        st.warning("이 계약 정보를 삭제하시겠습니까?")
        c1, c2 = st.columns(2)
        if c1.button("삭제 확인", key=f"cdel_y_{r['id']}", type="primary"):
            try:
                sb.table("client_contracts").delete().eq("id", r["id"]).eq("fc_id", fc_id).execute()
                st.session_state.pop(del_key, None)
                st.rerun()
            except Exception as e:
                st.error(safe_error("삭제", e))
        if c2.button("취소", key=f"cdel_n_{r['id']}"):
            st.session_state.pop(del_key, None)
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        if c1.button("수정", key=f"cedit_btn_{r['id']}", use_container_width=True):
            st.session_state[edit_key] = True
            st.rerun()
        if c2.button("삭제", key=f"cdel_btn_{r['id']}", use_container_width=True):
            st.session_state[del_key] = True
            st.rerun()


def _render_edit_form(sb, fc_id: str, r: dict):
    """계약 수정 폼"""
    with st.form(f"edit_contract_form_{r['id']}"):
        company = st.text_input("보험사", value=r.get("company", ""))
        product_name = st.text_input("상품명", value=r.get("product_name", ""))
        category = st.selectbox("카테고리", _CATEGORIES,
                                index=_CATEGORIES.index(r.get("category", "기타"))
                                if r.get("category") in _CATEGORIES else 5)
        monthly_premium = st.number_input("월 보험료", value=r.get("monthly_premium", 0),
                                          min_value=0, step=10000)
        contract_date = st.date_input("계약일", value=r.get("contract_date"))
        main_coverage = st.text_area("주계약", value=r.get("main_coverage", ""))
        riders_text = st.text_area(
            "특약 (줄바꿈으로 구분)",
            value="\n".join(rd.get("name", "") for rd in (r.get("riders") or [])),
        )
        memo = st.text_input("메모", value=r.get("memo", ""))

        c1, c2 = st.columns(2)
        if c1.form_submit_button("저장", type="primary", use_container_width=True):
            riders = [{"name": line.strip(), "amount": ""}
                      for line in riders_text.split("\n") if line.strip()]
            try:
                sb.table("client_contracts").update({
                    "company": company.strip(),
                    "product_name": product_name.strip(),
                    "category": category,
                    "monthly_premium": monthly_premium,
                    "contract_date": str(contract_date) if contract_date else None,
                    "main_coverage": main_coverage.strip(),
                    "riders": riders,
                    "memo": memo.strip(),
                }).eq("id", r["id"]).eq("fc_id", fc_id).execute()
                st.session_state.pop(f"edit_contract_{r['id']}", None)
                st.success("저장되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(safe_error("저장", e))
        if c2.form_submit_button("취소", use_container_width=True):
            st.session_state.pop(f"edit_contract_{r['id']}", None)
            st.rerun()


def _render_manual_form(sb, fc_id: str, client_id: str):
    """직접 입력 폼"""
    st.subheader("계약 직접 입력")
    with st.form("new_contract_form"):
        company = st.text_input("보험사", placeholder="예: 신한라이프")
        product_name = st.text_input("상품명", placeholder="예: 무배당 건강보험")
        category = st.selectbox("카테고리", _CATEGORIES)
        monthly_premium = st.number_input("월 보험료 (원)", min_value=0, step=10000)
        contract_date = st.date_input("계약일", value=None)
        main_coverage = st.text_area("주계약", placeholder="주계약 내용")
        riders_text = st.text_area("특약 (줄바꿈으로 구분)", placeholder="특약1\n특약2")
        memo = st.text_input("메모", placeholder="선택 사항")

        if st.form_submit_button("저장", type="primary", use_container_width=True):
            if not product_name.strip():
                st.error("상품명은 필수입니다.")
            else:
                riders = [{"name": line.strip(), "amount": ""}
                          for line in riders_text.split("\n") if line.strip()]
                try:
                    sb.table("client_contracts").insert({
                        "fc_id": fc_id,
                        "client_id": client_id,
                        "company": company.strip(),
                        "product_name": product_name.strip(),
                        "category": category,
                        "monthly_premium": monthly_premium,
                        "contract_date": str(contract_date) if contract_date else None,
                        "main_coverage": main_coverage.strip(),
                        "riders": riders,
                        "memo": memo.strip(),
                    }).execute()
                    st.success("계약 정보가 저장되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(safe_error("저장", e))


def _render_pdf_upload(sb, fc_id: str, client_id: str):
    """상품설계서 PDF 업로드 → 자동 파싱"""
    st.subheader("상품설계서 PDF 업로드")
    st.caption("상품설계서 PDF를 업로드하면 주계약·특약을 자동으로 추출합니다.")

    pdf_file = st.file_uploader("PDF 파일", type=["pdf"], key="contract_pdf_upload")
    if pdf_file and pdf_file.size > 10 * 1024 * 1024:
        st.error("파일 크기는 10MB 이하만 가능합니다.")
        return

    if pdf_file and st.button("분석 시작", type="primary", use_container_width=True):
        with st.spinner("상품설계서 분석 중..."):
            try:
                from services.contract_extractor import extract_from_pdf
                result = extract_from_pdf(pdf_file.read())
            except Exception as e:
                st.error(safe_error("PDF 분석", e))
                return

        if not result:
            st.warning("추출된 계약 정보가 없습니다. 직접 입력해주세요.")
            return

        st.success(f"{len(result)}건의 계약 정보를 추출했습니다.")
        _render_extracted_preview(sb, fc_id, client_id, result)


def _render_extracted_preview(sb, fc_id: str, client_id: str, contracts: list):
    """추출된 계약 정보 미리보기 + 저장"""
    for i, c in enumerate(contracts):
        with st.expander(f"📋 {c.get('company','')} — {c.get('product_name','')}", expanded=True):
            st.text(f"보험사: {c.get('company', '-')}")
            st.text(f"상품명: {c.get('product_name', '-')}")
            st.text(f"월 보험료: {c.get('monthly_premium', 0):,}원")
            if c.get("main_coverage"):
                st.caption(f"**주계약**: {c['main_coverage']}")
            riders = c.get("riders", [])
            if riders:
                st.caption("**특약**:")
                for rd in riders:
                    st.caption(f"  · {rd.get('name', '')}")

    if st.button("전체 저장", type="primary", use_container_width=True, key="save_extracted"):
        saved = 0
        for c in contracts:
            try:
                sb.table("client_contracts").insert({
                    "fc_id": fc_id,
                    "client_id": client_id,
                    "company": c.get("company", ""),
                    "product_name": c.get("product_name", ""),
                    "category": c.get("category", "기타"),
                    "monthly_premium": c.get("monthly_premium", 0),
                    "main_coverage": c.get("main_coverage", ""),
                    "riders": c.get("riders", []),
                }).execute()
                saved += 1
            except Exception as e:
                st.error(safe_error(f"저장 ({c.get('product_name', '')})", e))
        if saved:
            st.success(f"{saved}건 저장 완료")
            st.rerun()
