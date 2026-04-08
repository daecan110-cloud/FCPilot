"""상품설계서 PDF에서 주계약·특약 정보 추출 (Claude API)"""
import json
import base64
import pdfplumber
from config import CLAUDE_MODEL, CLAUDE_MAX_TOKENS
from utils.secrets_loader import get_secret

_SYSTEM_PROMPT = """보험 상품설계서 PDF 텍스트에서 계약 정보를 추출하세요.
반드시 아래 JSON 배열 형식으로만 응답하세요. 설명 없이 JSON만 출력하세요.

[
  {
    "company": "보험사명",
    "product_name": "상품명",
    "category": "종신보험|건강보험|연금보험|저축보험|변액보험|기타",
    "monthly_premium": 월보험료(숫자, 원 단위),
    "main_coverage": "주계약 보장내용 요약",
    "riders": [
      {"name": "특약명", "amount": "보장금액 또는 보험료"}
    ]
  }
]

규칙:
- 주계약과 특약을 구분하세요
- 월보험료는 숫자만 (원 단위)
- category는 상품 성격에 맞게 6가지 중 선택
- 추출 불가한 필드는 빈 문자열 또는 0
- 여러 계약이 있으면 배열에 모두 포함"""


def extract_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """상품설계서 PDF → 계약 정보 리스트"""
    text = _extract_text(pdf_bytes)
    if not text.strip():
        return []
    return _call_claude(text)


def _extract_text(pdf_bytes: bytes) -> str:
    """PDF에서 텍스트 추출 (최대 20페이지)"""
    import io
    pages_text = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages[:20]):
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages_text.append(f"[페이지 {i+1}]\n{page_text}")

            # 테이블도 추출
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl:
                    continue
                for row in tbl:
                    if row:
                        cells = [str(c or "").strip() for c in row]
                        if any(cells):
                            pages_text.append(" | ".join(cells))

    return "\n".join(pages_text)


def _call_claude(text: str) -> list[dict]:
    """Claude API로 계약 정보 추출"""
    import anthropic

    api_key = get_secret("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    # 텍스트가 너무 길면 앞부분만
    if len(text) > 30000:
        text = text[:30000]

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"다음 상품설계서에서 계약 정보를 추출하세요:\n\n{text}"}],
    )

    raw = response.content[0].text.strip()

    # JSON 파싱
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(result, list):
        result = [result]

    # 유효성 검증 + 정규화
    validated = []
    for item in result:
        if not isinstance(item, dict):
            continue
        validated.append({
            "company": str(item.get("company", "")).strip(),
            "product_name": str(item.get("product_name", "")).strip(),
            "category": _validate_category(item.get("category", "기타")),
            "monthly_premium": _to_int(item.get("monthly_premium", 0)),
            "main_coverage": str(item.get("main_coverage", "")).strip(),
            "riders": _validate_riders(item.get("riders", [])),
        })
    return validated


def _validate_category(cat: str) -> str:
    valid = {"종신보험", "건강보험", "연금보험", "저축보험", "변액보험", "기타"}
    return cat if cat in valid else "기타"


def _to_int(val) -> int:
    try:
        return int(float(str(val).replace(",", "").replace(" ", "")))
    except (ValueError, TypeError):
        return 0


def _validate_riders(riders) -> list:
    if not isinstance(riders, list):
        return []
    result = []
    for r in riders:
        if isinstance(r, dict):
            result.append({
                "name": str(r.get("name", "")).strip(),
                "amount": str(r.get("amount", "")).strip(),
            })
    return result
