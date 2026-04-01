"""보장분석 탭 UI"""
import streamlit as st
from config import MAX_FILE_SIZE_MB, CLAUDE_MODEL
from services.analysis_engine import analyze_and_generate
from services.yakwan_engine import analyze_yakwan, format_display
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
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
        st.session_state.pop("yakwan_selected_idx", None)

        _save_to_db(data, silent=True)

    data = st.session_state.get("analysis_data")
    if data is None:
        return

    # 보장분석 결과 + 약관 분석을 탭으로 통합
    tab_result, tab_yakwan = st.tabs(["보장분석 결과", "약관 분석 + AI 상담"])

    with tab_result:
        _show_result(data)

        warnings = data.get("_warnings", [])
        if warnings:
            with st.expander(f"검증 경고 ({len(warnings)}건)"):
                for w in warnings:
                    st.warning(w)

        excel_files = st.session_state.get("excel_files", [])
        for filename, excel_bytes in excel_files:
            st.download_button(
                label=f"다운로드: {filename}",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    with tab_yakwan:
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
        with st.expander(f"📋 계약 목록 ({len(contracts)}건)", expanded=True):
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
                    sb.table("analysis_records").update({"excel_path": path}).eq("id", record_id).execute()
                except Exception:
                    pass  # 업로드 실패해도 분석 기록은 유지

        if not silent:
            st.success("분석 기록이 저장되었습니다.")
    except Exception as e:
        if not silent:
            st.error(f"저장 실패: {e}")


# ── 약관 분석 + AI 상담 ──

def _render_yakwan_section(data: dict):
    st.subheader("약관 분석")
    st.caption("계약을 선택하고 약관 PDF를 업로드 → 면책/특이사항 분석 + AI 상담으로 K열 내용 확정")

    contracts = data.get("_all_contracts", data.get("계약", []))
    if not contracts:
        st.info("보장분석을 먼저 실행하세요.")
        return

    options = [
        f"[{i+1}] {c.get('보험사', '')} - {c.get('상품명', '')[:25]}"
        for i, c in enumerate(contracts)
    ]
    selected = st.selectbox(
        "분석할 계약 선택",
        options,
        index=st.session_state.get("yakwan_selected_idx"),
        placeholder="계약을 선택하세요",
    )

    if selected:
        idx = int(selected.split("]")[0].replace("[", "")) - 1
        st.session_state.yakwan_selected_idx = idx
        contract = contracts[idx]
    else:
        return

    yakwan_pdf = st.file_uploader("약관 PDF 업로드", type=["pdf"], key="yakwan_pdf")

    if yakwan_pdf and st.button("약관 분석 시작", use_container_width=True, type="primary"):
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
        # 새 계약 분석 시 채팅 초기화
        st.session_state.pop(f"yakwan_chat_{idx}", None)
        _save_yakwan_to_db(idx, contract, result)
        st.rerun()

    # 분석 결과 + AI 상담
    yakwan_results = st.session_state.get("yakwan_results", {})
    result = yakwan_results.get(idx)

    if result:
        with st.expander("약관 분석 결과", expanded=True):
            st.markdown(format_display(result))
            k_text = result.get("k_column", "")
            if k_text:
                st.info(f"K열 자동 요약: {k_text}")

        st.divider()
        _render_yakwan_chat(idx, contract, result)

        st.divider()
        _render_k_column_apply(data, idx, result)
    else:
        st.caption("약관 PDF를 업로드하고 분석을 시작하면 AI와 상담할 수 있습니다.")


def _render_yakwan_chat(contract_idx: int, contract: dict, yakwan_result: dict):
    """약관 내용 AI 상담 채팅창"""
    st.subheader("AI 약관 상담")
    st.caption("특약 면책기간, 보장범위, 감액조건 등 K열에 넣을 내용을 AI와 상담하세요.")

    chat_key = f"yakwan_chat_{contract_idx}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    # 채팅 이력 표시
    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 채팅 입력
    if prompt := st.chat_input(
        "예: 암 면책기간이 얼마나 되나요? / K열에 뭐라고 쓸까요?",
        key=f"chat_input_{contract_idx}",
    ):
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with st.spinner("AI 답변 중..."):
            reply = _chat_with_ai(contract, yakwan_result, st.session_state[chat_key])
        st.session_state[chat_key].append({"role": "assistant", "content": reply})
        st.rerun()

    if st.session_state[chat_key]:
        if st.button("채팅 초기화", key=f"chat_clear_{contract_idx}"):
            st.session_state[chat_key] = []
            st.rerun()


def _chat_with_ai(contract: dict, yakwan_result: dict, messages: list) -> str:
    """Claude API로 약관 상담 응답 생성"""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=st.secrets["claude"]["api_key"])

        system = f"""보험 약관 분석 전문가로서 FC(재무컨설턴트)의 질문에 실무적으로 답합니다.

현재 분석 계약:
- 보험사: {contract.get('보험사', '')}
- 상품명: {contract.get('상품명', '')}

약관 분석 결과:
{format_display(yakwan_result)}

K열 자동 요약: {yakwan_result.get('k_column', '(없음)')}

FC가 이 계약의 특약 면책기간, 보장범위, 감액조건, 주계약 내용 등에 대해 묻습니다.
엑셀 보장분석표 K열(특이사항)에 기재할 내용을 함께 결정하는 것도 도와주세요.
짧고 실무적으로 답변하세요. 고객명/전화번호 언급 금지."""

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=system,
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
        )
        return response.content[0].text
    except Exception as e:
        return f"AI 응답 실패: {e}"


def _render_k_column_apply(data: dict, idx: int, result: dict):
    """K열 내용 확정 후 엑셀 재생성"""
    st.subheader("K열 확정 및 엑셀 재생성")

    k_default = result.get("k_column", "")
    k_text = st.text_area(
        "K열에 기재할 내용 (AI 상담 후 수정 가능)",
        value=k_default,
        height=80,
        key=f"k_text_{idx}",
    )

    if st.button("이 내용으로 엑셀 재생성", use_container_width=True, type="primary"):
        yakwan_results = st.session_state.get("yakwan_results", {})
        k_column_data = {}
        for i, r in yakwan_results.items():
            k_column_data[i] = r.get("k_column", "")
        # 현재 선택 계약의 K열은 텍스트 박스 값 우선
        if k_text.strip():
            k_column_data[idx] = k_text.strip()

        pdf_bytes = st.session_state.get("pdf_bytes")
        include_review = st.session_state.get("include_review", False)
        if pdf_bytes:
            try:
                _, excel_files = analyze_and_generate(
                    pdf_bytes, include_review=include_review, k_column_data=k_column_data,
                )
                st.session_state.excel_files = excel_files
                st.success("엑셀 재생성 완료. '보장분석 결과' 탭에서 다운로드하세요.")
            except Exception as e:
                st.error(f"재생성 실패: {e}")


def _save_yakwan_to_db(idx: int, contract: dict, result: dict):
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
        pass
