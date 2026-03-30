"""보장분석 탭 UI"""
import streamlit as st
from config import MAX_FILE_SIZE_MB
from services.analysis_engine import analyze_and_generate
from services.yakwan_analyzer import analyze_yakwan
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
                                    help="체크하면 갱신구분/보험료변화/리뷰 섹션 포함")

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

    # 결과 표시
    data = st.session_state.get("analysis_data")
    if data is None:
        return

    _show_result(data)

    # 검증 경고
    warnings = data.get("_warnings", [])
    if warnings:
        with st.expander(f"검증 경고 ({len(warnings)}건)", expanded=True):
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

    # DB 저장
    if st.button("분석 기록 저장", use_container_width=True):
        _save_to_db(data)

    # 약관 분석 대화창
    st.divider()
    _render_yakwan_chat(data)


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
    else:
        st.warning("추출된 계약 정보가 없습니다.")


def _save_to_db(data: dict):
    save_data = {
        "고객명": data.get("고객명", ""),
        "성별": data.get("성별", ""),
        "나이": data.get("나이", 0),
        "계약수": len(data.get("_all_contracts", [])),
    }
    try:
        sb = get_supabase_client()
        sb.table("fp_analysis_records").insert({
            "fc_id": get_current_user_id(),
            "client_name": data.get("고객명", ""),
            "analysis_result": save_data,
            "pdf_filename": "",
        }).execute()
        st.success("분석 기록이 저장되었습니다.")
    except Exception as e:
        st.error(f"저장 실패: {e}")


# ── 약관 분석 대화창 ──

def _render_yakwan_chat(data: dict):
    st.subheader("약관 분석 (AI 대화)")
    st.caption("계약을 선택하고 약관 PDF를 업로드하면 면책기간/특이사항을 분석합니다.")

    contracts = data.get("_all_contracts", data.get("계약", []))
    if not contracts:
        return

    # 계약 선택
    options = [
        f"[{i+1}] {c.get('보험사', '')} - {c.get('상품명', '')[:25]}"
        for i, c in enumerate(contracts)
    ]
    selected = st.selectbox("분석할 계약 선택", options, index=None,
                             placeholder="계약을 선택하세요")

    # 약관 PDF 업로드
    yakwan_pdf = st.file_uploader(
        "약관 PDF 업로드",
        type=["pdf"],
        key="yakwan_pdf",
        help="선택한 계약의 약관 PDF를 업로드하세요",
    )

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

            # 결과 저장
            if "yakwan_results" not in st.session_state:
                st.session_state.yakwan_results = {}
            st.session_state.yakwan_results[idx] = result

    # 기존 분석 결과 표시
    yakwan_results = st.session_state.get("yakwan_results", {})
    for idx, result in yakwan_results.items():
        contract = contracts[idx] if idx < len(contracts) else {}
        with st.expander(
            f"{contract.get('보험사', '')} - {contract.get('상품명', '')[:25]}",
            expanded=True,
        ):
            st.markdown(result)

    # 대화 입력
    if yakwan_results:
        if "yakwan_chat" not in st.session_state:
            st.session_state.yakwan_chat = []

        for msg in st.session_state.yakwan_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("약관에 대해 추가 질문하세요")
        if prompt:
            st.session_state.yakwan_chat.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # 컨텍스트에 기존 분석 결과 포함
            context = "\n\n".join(
                f"[{contracts[i].get('보험사', '')} {contracts[i].get('상품명', '')[:20]}]\n{r}"
                for i, r in yakwan_results.items()
                if i < len(contracts)
            )

            with st.chat_message("assistant"):
                with st.spinner("분석 중..."):
                    try:
                        import anthropic
                        client = anthropic.Anthropic(
                            api_key=st.secrets["claude"]["api_key"]
                        )
                        messages = [
                            {"role": "user", "content": f"이전 약관 분석 결과:\n{context}"},
                            {"role": "assistant", "content": "네, 약관 분석 결과를 확인했습니다. 추가 질문해주세요."},
                        ]
                        for msg in st.session_state.yakwan_chat:
                            messages.append(msg)

                        response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=2048,
                            system="보험 약관 분석 전문가입니다. 한국어로 간결하게 답변하세요.",
                            messages=messages,
                        )
                        answer = response.content[0].text
                    except Exception as e:
                        answer = f"응답 실패: {e}"

                st.markdown(answer)
            st.session_state.yakwan_chat.append({"role": "assistant", "content": answer})
