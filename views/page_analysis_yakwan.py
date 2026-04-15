"""약관 분석 + AI 상담 섹션"""
import streamlit as st
from config import CLAUDE_MODEL
from services.yakwan_engine import analyze_yakwan, format_display
from auth import get_current_user_id, is_api_allowed
from utils.supabase_client import get_supabase_client
from utils.helpers import safe_error


def render_yakwan_section(data: dict):
    st.subheader("약관 분석")

    if not is_api_allowed():
        st.info("약관 분석 기능은 관리자만 사용할 수 있습니다.")
        return

    st.caption("계약을 선택하고 약관 PDF를 업로드 → 면책/특이사항 분석 + AI 상담으로 K열 내용 확정")

    contracts = data.get("_all_contracts", data.get("계약", []))
    if not contracts:
        st.info("보장분석을 먼저 실행하세요.")
        return

    options = [
        f"[{i+1}] {c.get('보험사', '')} - {c.get('상품명', '')[:25]}"
        for i, c in enumerate(contracts)
    ]
    saved_idx = st.session_state.get("yakwan_selected_idx")
    if saved_idx is not None and saved_idx >= len(options):
        saved_idx = None
    selected = st.selectbox(
        "분석할 계약 선택",
        options,
        index=saved_idx,
        placeholder="계약을 선택하세요",
    )

    if selected:
        idx = int(selected.split("]")[0].replace("[", "")) - 1
        st.session_state.yakwan_selected_idx = idx
        contract = contracts[idx]
    else:
        return

    yakwan_pdf = st.file_uploader("약관 PDF 업로드", type=["pdf"], key="yakwan_pdf")

    if yakwan_pdf:
        from utils.helpers import validate_file
        file_err = validate_file(yakwan_pdf, ["pdf"], 20)
        if file_err:
            st.error(file_err)
            return

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
                st.error(safe_error("약관 분석", e))
                return

        if "yakwan_results" not in st.session_state:
            st.session_state.yakwan_results = {}
        st.session_state.yakwan_results[idx] = result
        st.session_state.pop(f"yakwan_chat_{idx}", None)
        _save_yakwan_to_db(idx, contract, result)
        st.rerun()

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

    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

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
    except anthropic.RateLimitError:
        return "API 사용량 초과입니다. 1분 후 다시 시도해주세요."
    except anthropic.AuthenticationError:
        return "API 키가 유효하지 않습니다. 관리자에게 문의하세요."
    except Exception as e:
        import logging
        logging.error(f"약관 상담 API 오류: {e}")
        return f"AI 응답 오류: {type(e).__name__} — 다시 시도해주세요."


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
        from services.analysis_engine import analyze_and_generate
        yakwan_results = st.session_state.get("yakwan_results", {})
        k_column_data = {}
        for i, r in yakwan_results.items():
            k_column_data[i] = r.get("k_column", "")
        if k_text.strip():
            k_column_data[idx] = k_text.strip()

        pdf_bytes = st.session_state.get("pdf_bytes")
        if pdf_bytes:
            with st.spinner("엑셀 재생성 중..."):
                try:
                    _, excel_files = analyze_and_generate(pdf_bytes)
                    st.session_state.excel_files = excel_files
                    st.success("엑셀 재생성 완료. '보장분석 결과' 탭에서 다운로드하세요.")
                except Exception as e:
                    st.error(safe_error("재생성", e))


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
        pass  # 약관 기록 저장 실패해도 분석 결과는 유지
