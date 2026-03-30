"""약관 분석 엔진 — Claude API → 구조화 결과 + K열 요약"""
import base64
import json
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
    """약관 PDF → 구조화된 분석 결과 dict"""
    client = anthropic.Anthropic(api_key=st.secrets["claude"]["api_key"])
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    prompt = YAKWAN_PROMPT.format(company=company, product=product)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
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

    return _parse(message.content[0].text)


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
