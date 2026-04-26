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
    proposal_files = None
    proposal_format = "보장분석표에 포함"
    if use_proposal:
        proposal_files = st.file_uploader(
            "상품제안서 PDF 업로드 (복수 가능)",
            type=["pdf"],
            accept_multiple_files=True,
            help="보험사 상품설명서(제안서) PDF — 2개 이상 넣으면 비교표 생성",
            key="proposal_pdf",
        )
        proposal_format = st.selectbox(
            "제안서 출력 형식",
            ["보장분석표에 포함", "별도 비교표 파일"],
            help="'보장분석표에 포함': 기존 엑셀 M/N열에 추가 | '별도 비교표 파일': 독립 비교표 엑셀 생성",
            key="proposal_format",
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

        # 상품제안서 파싱 (복수 지원)
        proposal_data = None
        proposal_list = []
        if use_proposal and proposal_files:
            from services.proposal_parser import parse_proposal
            for pf in proposal_files:
                try:
                    pd = parse_proposal(pf.read())
                    if pd and pd.get("특약목록"):
                        proposal_list.append(pd)
                except Exception as e:
                    st.warning(safe_error(f"제안서 파싱({pf.name})", e))
            if proposal_list:
                proposal_data = proposal_list[0]  # 첫 번째를 기본 제안으로
                st.session_state.proposal_data = proposal_data
                st.session_state.proposal_list = proposal_list
            else:
                st.session_state.pop("proposal_data", None)
                st.session_state.pop("proposal_list", None)
        else:
            st.session_state.pop("proposal_data", None)
            st.session_state.pop("proposal_list", None)

        # 제안서 출력 형식에 따라 분기
        # "보장분석표에 포함" → 기존 엑셀 M/N열에 제안 추가
        # "별도 비교표 파일" → 제안 데이터를 별도 비교표로만 생성 (분석표에는 미포함)
        use_integrated = (proposal_format == "보장분석표에 포함")
        integrated_proposal = proposal_data if use_integrated else None

        needs_regen = client_name or (integrated_proposal and integrated_proposal.get("특약목록"))
        if needs_regen:
            try:
                from services.analysis_engine import regenerate_excel
                excel_files = regenerate_excel(data, proposal=integrated_proposal)
            except Exception as e:
                st.warning(safe_error("엑셀 재생성", e))

        # "별도 비교표 파일" + 제안서 있음 → 비교표 자동 생성
        if not use_integrated and proposal_list:
            from services.comparison_generator import generate_comparison_excel
            try:
                fname, fbytes = generate_comparison_excel(
                    data, proposal_list, list(range(len(proposal_list))))
                if fbytes:
                    st.session_state.comparison_file = (fname, fbytes)
            except Exception as e:
                st.warning(safe_error("비교표 생성", e))

        st.session_state.analysis_data = data
        st.session_state.excel_files = excel_files
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.proposal_format_used = proposal_format
        st.session_state.pop("yakwan_results", None)
        st.session_state.pop("yakwan_selected_idx", None)
        # 계약 선택 초기화 (전체 선택)
        all_c = data.get("_all_contracts", data.get("계약", []))
        st.session_state.selected_contract_idxs = [c["_idx"] for c in all_c]
        for c in all_c:
            st.session_state[f"ct_sel_{c['_idx']}"] = True

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

        # 리뷰 통합 토글 — 선택된 계약이 8개 초과일 때만 표시
        selected = st.session_state.get("selected_contract_idxs", [])
        all_contracts = data.get("_all_contracts", data.get("계약", []))
        sel_contracts = [c for c in all_contracts if c["_idx"] in selected] if selected else all_contracts
        if len(sel_contracts) > 8:
            if "review_last_toggle" not in st.session_state:
                st.session_state.review_last_toggle = False

            def _on_review_toggle():
                rl = st.session_state.review_last_toggle
                d = st.session_state.get("analysis_data", {})
                _sel = st.session_state.get("selected_contract_idxs", [])
                _all = d.get("_all_contracts", d.get("계약", []))
                _filtered = [c for c in _all if c["_idx"] in _sel] if _sel else _all
                _cov = d.get("_coverage_raw", {})
                _fcov = {k: v for k, v in _cov.items() if k in _sel} if _sel else _cov
                fd = {"고객명": d.get("고객명", "고객"), "성별": d.get("성별", ""),
                      "나이": d.get("나이", 0), "_all_contracts": _filtered, "_coverage_raw": _fcov}
                from services.analysis_engine import regenerate_excel
                _fmt = st.session_state.get("proposal_format_used", "보장분석표에 포함")
                _prop = st.session_state.get("proposal_data") if _fmt == "보장분석표에 포함" else None
                try:
                    st.session_state.excel_files = regenerate_excel(
                        fd, proposal=_prop, review_last=rl,
                    )
                except Exception:
                    pass

            st.toggle(
                "리뷰/갱신을 마지막 엑셀에 통합",
                help="갱신구분·보험리뷰를 마지막 엑셀에 전체 계약 기준으로 통합합니다",
                key="review_last_toggle",
                on_change=_on_review_toggle,
            )

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

        # 비교표 다운로드 영역
        prop_list = st.session_state.get("proposal_list", [])
        fmt_used = st.session_state.get("proposal_format_used", "보장분석표에 포함")

        # "별도 비교표 파일" 선택 시 → 자동 생성된 비교표 바로 표시
        if fmt_used == "별도 비교표 파일" and prop_list:
            comp = st.session_state.get("comparison_file")
            if comp:
                st.divider()
                st.markdown("**보장 비교표**")
                fname, fbytes = comp
                st.download_button(
                    label=f"다운로드: {fname}",
                    data=fbytes,
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="dl_comparison",
                )

        # 2개 이상 제안서 → 선택 후 비교표 재생성 가능
        if len(prop_list) >= 2:
            st.divider()
            st.markdown("**제안서 비교표 (선택 재생성)**")
            options = [f"{chr(65+i)}안: {p.get('상품명', f'제안{i+1}')[:20]}" for i, p in enumerate(prop_list)]
            selected_props = st.multiselect(
                "비교할 제안서 선택",
                options=options,
                default=options,
                key="comparison_select",
            )
            min_sel = 1 if fmt_used == "별도 비교표 파일" else 2
            if len(selected_props) >= min_sel:
                sel_indices = [options.index(s) for s in selected_props]
                if st.button("비교표 재생성", use_container_width=True, type="secondary"):
                    from services.comparison_generator import generate_comparison_excel
                    try:
                        fname, fbytes = generate_comparison_excel(
                            data, prop_list, sel_indices)
                        if fbytes:
                            st.session_state.comparison_file = (fname, fbytes)
                            st.rerun()
                    except Exception as e:
                        st.error(safe_error("비교표 생성", e))

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
        _render_contract_selector(data, contracts)


def _render_contract_selector(data: dict, contracts: list):
    """계약 선택/해제 UI + 엑셀 재생성"""
    # 초기값: 전체 선택
    if "selected_contract_idxs" not in st.session_state:
        st.session_state.selected_contract_idxs = [
            c["_idx"] for c in contracts
        ]

    with st.expander(f"계약 목록 ({len(contracts)}건) — 분석에 포함할 계약을 선택하세요", expanded=True):
        # 체크박스 key 초기값 설정 (최초 1회)
        for c in contracts:
            k = f"ct_sel_{c['_idx']}"
            if k not in st.session_state:
                st.session_state[k] = True

        def _select_all():
            for c in contracts:
                st.session_state[f"ct_sel_{c['_idx']}"] = True

        def _deselect_all():
            for c in contracts:
                st.session_state[f"ct_sel_{c['_idx']}"] = False

        sel_all, desel_all = st.columns(2)
        sel_all.button("전체 선택", use_container_width=True, key="sel_all",
                       on_click=_select_all)
        desel_all.button("전체 해제", use_container_width=True, key="desel_all",
                         on_click=_deselect_all)

        for c in contracts:
            idx = c["_idx"]
            prem = c.get("월보험료", 0)
            label = (
                f"**{c.get('보험사', '')}** | "
                f"{c.get('상품명', '')[:30]} | "
                f"월 {prem:,}원 | "
                f"{c.get('보장나이', '')}"
            )
            st.checkbox(label, key=f"ct_sel_{idx}")

    # 체크박스 상태에서 선택 목록 동기화
    selected = [c["_idx"] for c in contracts if st.session_state.get(f"ct_sel_{c['_idx']}", True)]
    st.session_state.selected_contract_idxs = selected

    selected = st.session_state.selected_contract_idxs
    total = len(contracts)
    n_sel = len(selected)

    if n_sel == 0:
        st.warning("최소 1개 이상의 계약을 선택해주세요.")
        return

    if n_sel < total:
        st.info(f"{total}건 중 {n_sel}건 선택됨")
        if st.button("선택된 계약으로 엑셀 재생성", type="primary",
                     use_container_width=True, key="regen_selected"):
            _regenerate_with_selection(data, contracts, selected)

    # 전체 선택 상태에서 분석 직후 → 별도 재생성 불필요


def _regenerate_with_selection(data: dict, contracts: list, selected_idxs: list):
    """선택된 계약만으로 엑셀 재생성"""
    from services.analysis_engine import regenerate_excel

    filtered = [c for c in contracts if c["_idx"] in selected_idxs]
    coverage_raw = data.get("_coverage_raw", {})
    filtered_cov = {k: v for k, v in coverage_raw.items() if k in selected_idxs}

    # 필터된 데이터로 임시 data dict 생성
    filtered_data = {
        "고객명": data.get("고객명", "고객"),
        "성별": data.get("성별", ""),
        "나이": data.get("나이", 0),
        "_all_contracts": filtered,
        "_coverage_raw": filtered_cov,
    }

    fmt_used = st.session_state.get("proposal_format_used", "보장분석표에 포함")
    proposal = st.session_state.get("proposal_data") if fmt_used == "보장분석표에 포함" else None
    review_last = st.session_state.get("review_last_toggle", False)

    try:
        excel_files = regenerate_excel(
            filtered_data, proposal=proposal, review_last=review_last,
        )
        st.session_state.excel_files = excel_files
        st.success(f"{len(filtered)}건 계약으로 엑셀이 재생성되었습니다.")
        st.rerun()
    except Exception as e:
        st.error(safe_error("엑셀 재생성", e))


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
        score = data.get("보장점수", 0)
        res = sb.table("analysis_records").insert({
            "fc_id": fc_id,
            "client_name": data.get("고객명", ""),
            "contract_count": len(contracts),
            "result_summary": {
                "성별": data.get("성별", ""),
                "나이": data.get("나이", 0),
                "보장점수": score,
            },
        }).execute()
        record_id = res.data[0]["id"] if res.data else None

        # 고객 테이블에 보장점수 반영
        if score > 0:
            client_name = data.get("고객명", "")
            if client_name:
                sb.table("clients").update({"coverage_score": score}).eq(
                    "fc_id", fc_id
                ).eq("name", client_name).execute()

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
