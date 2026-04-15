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

    # --- 신규 상품 제안 ---
    use_proposal = st.toggle("신규 상품 제안 포함", value=False)
    proposal_file = None
    if use_proposal:
        proposal_file = st.file_uploader(
            "상품제안서 PDF 업로드",
            type=["pdf"],
            help="보험사 상품설명서(제안서) PDF — 특약 목록을 자동으로 읽어옵니다",
            key="proposal_pdf",
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

        # 상품제안서 파싱
        proposal_data = None
        if use_proposal and proposal_file is not None:
            from services.proposal_parser import parse_proposal
            try:
                proposal_data = parse_proposal(proposal_file.read())
                st.session_state.proposal_data = proposal_data
            except Exception as e:
                st.warning(safe_error("제안서 파싱", e))
                st.session_state.pop("proposal_data", None)
        else:
            st.session_state.pop("proposal_data", None)

        # 고객명/제안 옵션 → 엑셀 재생성
        needs_regen = client_name or (proposal_data and proposal_data.get("특약목록"))
        if needs_regen:
            try:
                from services.analysis_engine import regenerate_excel
                excel_files = regenerate_excel(data, proposal=proposal_data)
            except Exception as e:
                st.warning(safe_error("엑셀 재생성", e))

        st.session_state.analysis_data = data
        st.session_state.excel_files = excel_files
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pop("yakwan_results", None)
        st.session_state.pop("yakwan_selected_idx", None)

        _save_to_db(data, silent=True)

    data = st.session_state.get("analysis_data")
    if data is None:
        return

    proposal = st.session_state.get("proposal_data")
    tab_names = ["보장분석 결과", "약관 분석 + AI 상담"]
    if proposal:
        tab_names.append("신규 상품 제안")

    tabs = st.tabs(tab_names)

    with tabs[0]:
        _show_result(data)

        warnings = data.get("_warnings", [])
        if warnings:
            with st.expander(f"검증 경고 ({len(warnings)}건)"):
                for w in warnings:
                    st.warning(w)

        # 리뷰 통합 토글 — 엑셀 2개 이상일 때만 표시
        all_contracts = data.get("_all_contracts", data.get("계약", []))
        if len(all_contracts) > 7:
            review_last = st.toggle(
                "리뷰/갱신을 마지막 엑셀에 통합",
                value=st.session_state.get("_review_last", False),
                help="갱신구분·보험리뷰를 마지막 엑셀에 전체 계약 기준으로 통합합니다",
                key="review_last_toggle",
            )
            if review_last != st.session_state.get("_review_last", False):
                st.session_state._review_last = review_last
                from services.analysis_engine import regenerate_excel
                proposal_d = st.session_state.get("proposal_data")
                try:
                    st.session_state.excel_files = regenerate_excel(
                        data, proposal=proposal_d, review_last=review_last,
                    )
                except Exception as e:
                    st.warning(safe_error("엑셀 재생성", e))
                st.rerun()

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

    with tabs[1]:
        from views.page_analysis_yakwan import render_yakwan_section
        render_yakwan_section(data)

    if proposal and len(tabs) > 2:
        with tabs[2]:
            _show_proposal(proposal)


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


def _show_proposal(proposal: dict):
    """신규 상품 제안 특약 목록 표시"""
    st.subheader("제안 상품")
    st.markdown(f"**{proposal.get('상품명', '-')}**")
    if proposal.get("보험료합계"):
        st.metric("월 보험료 합계", f"{proposal['보험료합계']:,}원")

    riders = proposal.get("특약목록", [])
    if not riders:
        st.warning("특약을 찾지 못했습니다.")
        return

    st.markdown(f"**특약 {len(riders)}개**")
    for r in riders:
        갱신 = " (갱신형)" if r.get("갱신형") else ""
        st.markdown(
            f"- {r['번호']} **{r['특약명'][:50]}**{갱신}  \n"
            f"  대표지급: **{r['대표지급금액']:,}만원** | "
            f"{r['보험기간']} | {r['납입기간']} | "
            f"월 {r['보험료']:,}원"
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
