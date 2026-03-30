"""보장분석 탭 UI"""
import streamlit as st
from config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE_MB
from services.analysis_engine import analyze_pdf
from services.excel_generator import generate_analysis_excel
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client


def render():
    st.header("📊 보장분석")
    st.caption("보험 계약 PDF를 업로드하면 AI가 보장 내역을 분석합니다.")

    # PDF 업로드
    uploaded_file = st.file_uploader(
        "보험 계약서 PDF 업로드",
        type=["pdf"],
        help=f"최대 {MAX_FILE_SIZE_MB}MB",
    )

    client_name = st.text_input(
        "고객명 (선택 — 엑셀에만 표시, AI에 전송하지 않음)",
        placeholder="예: 홍길동",
    )

    if uploaded_file is None:
        st.info("PDF 파일을 업로드해주세요.")
        return

    # 파일 크기 검증
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"파일 크기가 {MAX_FILE_SIZE_MB}MB를 초과합니다.")
        return

    pdf_bytes = uploaded_file.read()

    if st.button("🔍 보장분석 시작", use_container_width=True, type="primary"):
        with st.spinner("AI가 보장 내역을 분석하고 있습니다..."):
            try:
                result = analyze_pdf(pdf_bytes, uploaded_file.name)
            except Exception as e:
                st.error(f"분석 실패: {e}")
                return

        if "error" in result:
            st.error(f"분석 오류: {result['error']}")
            if "raw_response" in result:
                with st.expander("원본 응답"):
                    st.code(result["raw_response"])
            return

        # 결과 세션에 저장
        st.session_state.analysis_result = result
        st.session_state.analysis_filename = uploaded_file.name

    # 결과 표시
    result = st.session_state.get("analysis_result")
    if result is None:
        return

    _show_result(result, client_name)

    # 엑셀 다운로드
    excel_bytes = generate_analysis_excel(result, client_name)
    st.download_button(
        label="📥 엑셀 다운로드",
        data=excel_bytes,
        file_name=f"보장분석_{client_name or '결과'}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    # DB 저장
    if st.button("💾 분석 기록 저장", use_container_width=True):
        _save_to_db(result, client_name)


def _show_result(result: dict, client_name: str):
    """분석 결과 표시"""
    st.subheader("분석 결과")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("보험사", result.get("insurance_company", "-"))
        st.metric("계약일", result.get("contract_date", "-"))
        st.metric("납입기간", result.get("payment_period", "-"))
    with col2:
        st.metric("상품명", result.get("product_name", "-"))
        st.metric("만기일", result.get("expiry_date", "-"))
        premium = result.get("monthly_premium")
        st.metric("월 보험료", f"{premium:,}원" if premium else "-")

    st.divider()

    # 보장 내역 테이블
    coverages = result.get("coverages", [])
    if coverages:
        st.subheader(f"보장 내역 ({len(coverages)}건)")
        for cov in coverages:
            amount = cov.get("coverage_amount")
            amount_str = f"{amount:,}원" if amount else "-"
            st.markdown(
                f"- **{cov.get('rider_name', '-')}** | "
                f"{cov.get('coverage_type', '-')} | "
                f"{amount_str} | "
                f"{cov.get('coverage_period', '-')}"
            )
    else:
        st.warning("추출된 보장 내역이 없습니다.")


def _save_to_db(result: dict, client_name: str):
    """분석 결과를 Supabase에 저장"""
    try:
        sb = get_supabase_client()
        sb.table("fp_analysis_records").insert({
            "fc_id": get_current_user_id(),
            "client_name": client_name,
            "analysis_result": result,
            "pdf_filename": st.session_state.get("analysis_filename", ""),
        }).execute()
        st.success("분석 기록이 저장되었습니다.")
    except Exception as e:
        st.error(f"저장 실패: {e}")
