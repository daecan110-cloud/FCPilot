"""보장분석 엔진 — Claude API 연동"""
import json
import base64
import streamlit as st
import anthropic
from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS

ANALYSIS_PROMPT = """당신은 보험 보장분석 전문가입니다.
첨부된 보험 계약 PDF를 분석하여 다음 정보를 JSON으로 추출해주세요.

## 추출 항목
1. 보험사명
2. 상품명
3. 계약일 / 만기일
4. 납입기간 / 납입주기
5. 월 보험료
6. 보장 내역 (각 특약별):
   - 특약명
   - 보장내용 (사망/입원/수술/진단 등)
   - 보장금액
   - 보장기간

## 출력 형식 (JSON)
```json
{
  "insurance_company": "보험사명",
  "product_name": "상품명",
  "contract_date": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD",
  "payment_period": "20년납",
  "payment_cycle": "월납",
  "monthly_premium": 50000,
  "coverages": [
    {
      "rider_name": "특약명",
      "coverage_type": "사망|입원|수술|진단|실손|기타",
      "coverage_amount": 10000000,
      "coverage_period": "80세만기"
    }
  ]
}
```

정확한 금액과 날짜를 추출하세요. 불확실하면 null로 표시하세요.
절대 고객 이름이나 전화번호를 응답에 포함하지 마세요."""


def analyze_pdf(pdf_bytes: bytes, filename: str) -> dict:
    """PDF를 Claude API로 분석하여 보장 정보 추출"""
    client = anthropic.Anthropic(api_key=st.secrets["claude"]["api_key"])

    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        messages=[
            {
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
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT,
                    },
                ],
            }
        ],
    )

    return _parse_response(message.content[0].text)


def _parse_response(response_text: str) -> dict:
    """Claude 응답에서 JSON 추출"""
    # JSON 블록 추출
    text = response_text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {
            "error": "분석 결과 파싱 실패",
            "raw_response": response_text,
        }
