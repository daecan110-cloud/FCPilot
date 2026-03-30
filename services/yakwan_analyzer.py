"""약관 분석 엔진 — Claude API"""
import base64
import streamlit as st
import anthropic
from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS

YAKWAN_PROMPT = """당신은 보험 약관 분석 전문가입니다.
첨부된 약관 PDF를 분석하여 다음 정보를 추출해주세요.

## 분석 대상 계약
보험사: {company}
상품명: {product}

## 추출 항목
1. 면책기간 (각 보장별)
2. 감액기간 및 감액 비율
3. 보장 범위 특이사항
4. 갱신 조건 (갱신형인 경우)
5. 해지환급금 특이사항
6. 주의사항 (고객에게 안내 필요한 사항)

## 출력 형식
간결하게 핵심만 작성하세요.
각 항목은 한 줄로 요약하고, 특이사항이 없으면 생략하세요.
절대 고객 이름이나 전화번호를 응답에 포함하지 마세요."""


def analyze_yakwan(pdf_bytes: bytes, company: str, product: str) -> str:
    """약관 PDF 분석 -> 텍스트 결과"""
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

    return message.content[0].text
