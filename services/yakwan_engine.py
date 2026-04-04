"""약관 분석 엔진 — Claude API → 구조화 결과 + K열 요약"""
import base64
import json
import time
import streamlit as st
import anthropic
from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS

YAKWAN_PROMPT = """당신은 보험 약관 분석 전문가입니다.
첨부된 약관 PDF를 분석하여 다음 정보를 JSON으로 추출해주세요.

## 분석 대상
보험사: {company}
상품명: {product}

## 출력 형식 (JSON)
```json
{{
  "면책기간": "예: 암 90일, 뇌/심장 없음",
  "감액기간": "예: 1년 50% 감액 / 없음",
  "보장범위": "예: 16대 질병수술 기준 / 전체 질병수술",
  "갱신조건": "예: 15년 갱신, 최대 100세 / 비갱신",
  "해지환급금": "예: 무해지환급형 (해지 시 0원) / 표준형",
  "주의사항": "예: 면책기간 내 진단 시 보험료만 환급",
  "k_column": "2줄 이내 핵심 요약 (엑셀 K열용)"
}}
```

핵심만 간결하게. 해당 없는 항목은 빈 문자열.
절대 고객 이름이나 전화번호를 포함하지 마세요."""


def analyze_yakwan(pdf_bytes: bytes, company: str, product: str) -> dict:
    """약관 PDF → 구조화된 분석 결과 dict (429 시 최대 2회 재시도)"""
    client = anthropic.Anthropic(api_key=st.secrets["claude"]["api_key"])
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    prompt = YAKWAN_PROMPT.format(company=company, product=product)

    wait_secs = [35, 65]  # 1차: 35초, 2차: 65초 대기
    for attempt in range(3):
        try:
            message = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=1024,  # 출력은 JSON만이므로 1024로 충분
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }],
            )
            if not message.content:
                raise ValueError("AI 응답이 비어 있습니다.")
            return _parse(message.content[0].text)
        except Exception as e:
            err = str(e)
            if ("rate_limit" in err or "429" in err) and attempt < 2:
                wait = wait_secs[attempt]
                # Streamlit 컨텍스트에서 카운트다운 표시
                placeholder = st.empty()
                for remaining in range(wait, 0, -1):
                    placeholder.warning(f"⏳ API 토큰 한도 초과 — {remaining}초 후 재시도... (시도 {attempt + 1}/3)")
                    time.sleep(1)
                placeholder.empty()
                continue
            raise


def format_display(result: dict) -> str:
    """분석 결과를 사용자 표시용 텍스트로 변환"""
    lines = []
    labels = [
        ("면책기간", "면책기간"),
        ("감액기간", "감액기간"),
        ("보장범위", "보장범위"),
        ("갱신조건", "갱신조건"),
        ("해지환급금", "해지환급금"),
        ("주의사항", "주의사항"),
    ]
    for key, label in labels:
        val = result.get(key, "")
        if val:
            lines.append(f"**{label}**: {val}")
    return "\n\n".join(lines) if lines else "분석 결과 없음"


def _parse(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"k_column": "", "raw": text}
