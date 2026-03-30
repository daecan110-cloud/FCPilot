"""간판 OCR — Claude Vision API"""
import base64
import json
import streamlit as st
import anthropic
from config import CLAUDE_MODEL

OCR_PROMPT = """이 간판 사진에서 다음 정보를 추출해주세요.
JSON으로만 응답하세요.

```json
{
  "shop_name": "가게 이름",
  "category": "업종 (음식점/카페/미용실/병원/기타)",
  "phone": "전화번호 (있으면)",
  "address": "주소 (간판에 있으면)"
}
```

간판에서 읽을 수 없는 항목은 빈 문자열로 두세요."""


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
