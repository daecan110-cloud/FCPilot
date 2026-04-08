"""보장분석 탭 UI"""
import streamlit as st
from config import MAX_FILE_SIZE_MB
from services.analysis_engine import analyze_and_generate
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.helpers import safe_error
from utils.ui_components import section_header


def render():
    st.header("보장분석")

    section_header("Step 1. PDF 업로드")
    uploaded_file = st.file_uploader(
        "보험 계약서 PDF 업로드",
        type=["pdf"],
        help=f"최대 {MAX_FILE_SIZE_MB}MB",
        label_visibility="collapsed",
    )

    section_header("Step 2. 옵션 설정")
    client_name = st.text_input(
        "고객명 (선택 - 엑셀에만 표시)",
        placeholder="예: 홍길동",
    )

    if uploaded_file is None:
        st.info("PDF 파일을 업로드해주세요.")
        return

    from utils.helpers import validate_file
    file_err = validate_file(uploaded_file, ["pdf"], MAX_FILE_SIZE_MB)
    if file_err:
        st.error(file_err)
        return

    pdf_bytes = uploaded_file.read()

    if st.button("보장분석 시작", use_container_width=True, type="primary"):
        with st.spinner("PDF에서 보장 내역을 추출하고 있습니다..."):
            try:
                data, excel_files = analyze_and_generate(pdf_bytes)
            except Exception as e:
                st.error(safe_error("분석", e))
                return

        if client_name:
            data["고객명"] = client_name
            try:
                from services.analysis_engine import regenerate_excel
                excel_files = regenerate_excel(data)
            except Exception as e:
                st.error(safe_error("엑셀 재생성", e))
                return

        st.session_state.analysis_data = data
        st.session_state.excel_files = excel_files
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pop("yakwan_results", None)
        st.session_state.pop("yakwan_selected_idx", None)

        _save_to_db(data, silent=True)

    data = st.session_state.get("analysis_data")
    if data is None:
        return

    tab_result, tab_yakwan = st.tabs(["보장분석 결과", "약관 분석 + AI 상담"])

    with tab_result:
        _show_result(data)

        warnings = data.get("_warnings", [])
        if warnings:
            with st.expander(f"검증 경고 ({len(warnings)}건)"):
                for w in warnings:
                    st.warning(w)

        excel_files = st.session_state.get("excel_files", [])
        for idx, (filename, excel_bytes) in enumerate(excel_files):
            st.download_button(
                label=f"다운로드: {filename}",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"dl_{idx}_{filename}",
            )

    with tab_yakwan:
        from views.page_analysis_yakwan import render_yakwan_section
        render_yakwan_section(data)


def _show_result(data: dict):
    st.subheader("분석 결과")
    col1, col2, col3 = st.columns(3)
    col1.metric("고객명", data.get("고객명", "-"))
    col2.metric("성별", data.get("성별", "-"))
    col3.metric("나이", f"{data.get('나이', 0)}세")

    st.divider()
    contracts = data.get("_all_contracts", data.get("계약", []))
    if contracts:
        with st.expander(f"계약 목록 ({len(contracts)}건)", expanded=True):
            for c in contracts:
                prem = c.get("월보험료", 0)
                st.markdown(
                    f"- **{c.get('보험사', '')}** | "
                    f"{c.get('상품명', '')[:30]} | "
                    f"월 {prem:,}원 | "
                    f"{c.get('보장나이', '')}"
                )


def _save_to_db(data: dict, silent: bool = False):
    try:
        sb = get_supabase_client()
        fc_id = get_current_user_id()
        contracts = data.get("_all_contracts", [])
        res = sb.table("analysis_records").insert({
            "fc_id": fc_id,
            "client_name": data.get("고객명", ""),
            "contract_count": len(contracts),
            "result_summary": {"성별": data.get("성별", ""), "나이": data.get("나이", 0)},
        }).execute()
        record_id = res.data[0]["id"] if res.data else None

        if record_id:
            excel_files = st.session_state.get("excel_files", [])
            if excel_files:
                _, excel_bytes = excel_files[0]
                path = f"{fc_id}/{record_id}.xlsx"
                try:
                    from utils.db_admin import get_admin_client
                    admin_sb = get_admin_client()
                    admin_sb.storage.from_("analysis-excel").upload(
                        path, excel_bytes,
                        {"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
                    )
                    sb.table("analysis_records").update({"excel_path": path}).eq("id", record_id).eq("fc_id", fc_id).execute()
                except Exception:
                    pass  # 업로드 실패해도 분석 기록은 유지

        if not silent:
            st.success("분석 기록이 저장되었습니다.")
    except Exception as e:
        if not silent:
            st.error(safe_error("저장", e))
