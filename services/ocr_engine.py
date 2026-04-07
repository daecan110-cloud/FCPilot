"""간판 OCR — Claude Vision API"""
import base64
import json
import streamlit as st
import anthropic
from config import CLAUDE_MODEL

OCR_PROMPT = """이 사진은 한국의 가게 간판입니다.
간판과 사진 속 모든 텍스트를 꼼꼼히 읽어서 아래 JSON 형식으로만 응답하세요.

```json
{
  "shop_name": "가게 이름 (가장 큰 글씨가 보통 가게명)",
  "category": "업종 — 음식점/카페/미용실/뷰티/학원/교육/병원/약국/편의점/마트/의류/패션/사무실/기타 중 하나",
  "phone": "전화번호 (031-XXX-XXXX, 010-XXXX-XXXX 등 숫자와 하이픈)",
  "address": "주소 (시/군/구, 읍/면/동, 리/번지 등 — 간판 어디든 주소가 보이면 기재)"
}
```

중요:
- 간판의 큰 글씨뿐 아니라 작은 글씨(하단, 측면, 창문 등)도 모두 확인하세요.
- 전화번호와 주소는 간판 하단이나 작은 글씨에 있는 경우가 많습니다.
- 읽기 어려운 항목만 빈 문자열("")로 두세요."""


def extract_from_sign(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """간판 사진에서 가게명/업종/전화번호 추출"""
    client = anthropic.Anthropic(api_key=st.secrets["claude"]["api_key"])
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    },
                },
                {"type": "text", "text": OCR_PROMPT},
            ],
        }],
    )

    if not message.content:
        return {"shop_name": "", "category": "", "items": []}
    return _parse(message.content[0].text)


def _parse(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"shop_name": "", "category": "", "phone": "", "address": "", "raw": text}
