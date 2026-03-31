"""보장분석 탭 UI"""
import streamlit as st
from config import MAX_FILE_SIZE_MB
from services.analysis_engine import analyze_and_generate
from services.yakwan_engine import analyze_yakwan, format_display
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client


def render():
    st.header("보장분석")
    st.caption("보험 계약 PDF를 업로드하면 자동으로 보장분석표를 생성합니다.")

    uploaded_file = st.file_uploader(
        "보험 계약서 PDF 업로드",
        type=["pdf"],
        help=f"최대 {MAX_FILE_SIZE_MB}MB",
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        client_name = st.text_input(
            "고객명 (선택 - 엑셀에만 표시)",
            placeholder="예: 홍길동",
        )
    with col2:
        include_review = st.toggle("상세 보장내역 포함", value=False,
                                    help="갱신구분/보험료변화/리뷰 섹션 포함")

    if uploaded_file is None:
        st.info("PDF 파일을 업로드해주세요.")
        return

    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"파일 크기가 {MAX_FILE_SIZE_MB}MB를 초과합니다.")
        return

    pdf_bytes = uploaded_file.read()

    if st.button("보장분석 시작", use_container_width=True, type="primary"):
        with st.spinner("PDF에서 보장 내역을 추출하고 있습니다..."):
            try:
                data, excel_files = analyze_and_generate(
                    pdf_bytes, include_review=include_review,
                )
            except Exception as e:
                st.error(f"분석 실패: {e}")
                return

        if client_name:
            data["고객명"] = client_name
            try:
                _, excel_files = analyze_and_generate(
                    pdf_bytes, include_review=include_review,
                )
            except Exception as e:
                st.error(f"엑셀 재생성 실패: {e}")
                return

        st.session_state.analysis_data = data
        st.session_state.excel_files = excel_files
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.include_review = include_review
        st.session_state.pop("yakwan_results", None)

        # 자동 저장 (버튼 클릭 불필요)
        _save_to_db(data, silent=True)

    data = st.session_state.get("analysis_data")
    if data is None:
        return

    _show_result(data)

    warnings = data.get("_warnings", [])
    if warnings:
        with st.expander(f"검증 경고 ({len(warnings)}건)"):
            for w in warnings:
                st.warning(w)

    # 엑셀 다운로드
    excel_files = st.session_state.get("excel_files", [])
    for filename, excel_bytes in excel_files:
        st.download_button(
            label=f"다운로드: {filename}",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.divider()
    _render_yakwan_section(data)


def _show_result(data: dict):
    st.subheader("분석 결과")
    col1, col2, col3 = st.columns(3)
    col1.metric("고객명", data.get("고객명", "-"))
    col2.metric("성별", data.get("성별", "-"))
    col3.metric("나이", f"{data.get('나이', 0)}세")

    st.divider()
    contracts = data.get("_all_contracts", data.get("계약", []))
    if contracts:
        st.subheader(f"계약 현황 ({len(contracts)}건)")
        for c in contracts:
            prem = c.get("월보험료", 0)
            st.markdown(
                f"- **{c.get('보험사', '')}** | "
                f"{c.get('상품명', '')[:30]} | "
                f"월 {prem:,}원 | "
                f"{c.get('보장나이', '')}"
            )


def _save_to_db(data: dict, silent: bool = False):
    save_data = {
        "고객명": data.get("고객명", ""),
        "성별": data.get("성별", ""),
        "나이": data.get("나이", 0),
        "계약수": len(data.get("_all_contracts", [])),
    }
    try:
        sb = get_supabase_client()
        sb.table("analysis_records").insert({
            "fc_id": get_current_user_id(),
            "client_name": data.get("고객명", ""),
            "analysis_result": save_data,
            "pdf_filename": "",
        }).execute()
        if not silent:
            st.success("분석 기록이 저장되었습니다.")
    except Exception as e:
        if not silent:
            st.error(f"저장 실패: {e}")


# ── 약관 분석 섹션 ──

def _render_yakwan_section(data: dict):
    st.subheader("약관 분석")
    st.caption("계약을 선택하고 약관 PDF를 업로드하면 면책/특이사항을 분석합니다.")
    st.caption("분석 결과는 보장분석표 K열(특이사항)에 자동 반영됩니다.")

    contracts = data.get("_all_contracts", data.get("계약", []))
    if not contracts:
        return

    options = [
        f"[{i+1}] {c.get('보험사', '')} - {c.get('상품명', '')[:25]}"
        for i, c in enumerate(contracts)
    ]
    selected = st.selectbox("분석할 계약 선택", options, index=None,
                             placeholder="계약을 선택하세요")

    yakwan_pdf = st.file_uploader("약관 PDF 업로드", type=["pdf"], key="yakwan_pdf")

    if selected and yakwan_pdf:
        idx = int(selected.split("]")[0].replace("[", "")) - 1
        contract = contracts[idx]

        if st.button("약관 분석 시작", use_container_width=True):
            yakwan_bytes = yakwan_pdf.read()
            with st.spinner(f"{contract.get('상품명', '')[:20]} 약관 분석 중..."):
                try:
                    result = analyze_yakwan(
                        yakwan_bytes,
                        contract.get("보험사", ""),
                        contract.get("상품명", ""),
                    )
                except Exception as e:
                    st.error(f"약관 분석 실패: {e}")
                    return

            if "yakwan_results" not in st.session_state:
                st.session_state.yakwan_results = {}
            st.session_state.yakwan_results[idx] = result

            # DB 저장
            _save_yakwan_to_db(idx, contract, result)

    # 분석 결과 표시
    yakwan_results = st.session_state.get("yakwan_results", {})
    if not yakwan_results:
        return

    for idx, result in yakwan_results.items():
        contract = contracts[idx] if idx < len(contracts) else {}
        with st.expander(
            f"{contract.get('보험사', '')} - {contract.get('상품명', '')[:25]}",
            expanded=True,
        ):
            st.markdown(format_display(result))
            k_text = result.get("k_column", "")
            if k_text:
                st.info(f"K열 반영: {k_text}")

    # 엑셀 재생성 (K열 반영)
    if st.button("약관 분석 결과 반영하여 엑셀 재생성", use_container_width=True, type="primary"):
        _regenerate_excel_with_yakwan(data, yakwan_results)


def _regenerate_excel_with_yakwan(data: dict, yakwan_results: dict):
    """약관 분석 K열 텍스트를 data에 주입 후 엑셀 재생성"""
    # K열 데이터 주입
    k_column_data = {}
    for idx, result in yakwan_results.items():
        k_text = result.get("k_column", "")
        if k_text:
            k_column_data[idx] = k_text
    data["_k_column"] = k_column_data

    pdf_bytes = st.session_state.get("pdf_bytes")
    include_review = st.session_state.get("include_review", False)

    if pdf_bytes:
        try:
            _, excel_files = analyze_and_generate(
                pdf_bytes,
                include_review=include_review,
                k_column_data=k_column_data,
            )
            st.session_state.excel_files = excel_files
            st.success("약관 분석 결과가 반영된 엑셀이 생성되었습니다. 위에서 다운로드하세요.")
            st.rerun()
        except Exception as e:
            st.error(f"재생성 실패: {e}")


def _save_yakwan_to_db(idx: int, contract: dict, result: dict):
    """약관 분석 결과를 Supabase에 저장"""
    try:
        sb = get_supabase_client()
        sb.table("yakwan_records").insert({
            "fc_id": get_current_user_id(),
            "contract_index": idx,
            "company": contract.get("보험사", ""),
            "product": contract.get("상품명", ""),
            "yakwan_result": result,
            "k_column_text": result.get("k_column", ""),
        }).execute()
    except Exception:
        pass  # 저장 실패해도 UI 흐름 차단하지 않음
