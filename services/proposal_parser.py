"""상품제안서 PDF 파싱 — 특약 목록 + 대표지급금액 추출"""
import io
import re

import pdfplumber


def parse_proposal(pdf_bytes: bytes) -> dict:
    """상품제안서 PDF에서 특약 목록을 추출한다.

    Returns:
        {
            "상품명": str,
            "보험료합계": int,
            "특약목록": [
                {
                    "번호": str,          # "[1]", "[2]" 등
                    "특약명": str,
                    "대표지급금액": int,   # 만원 단위
                    "보험기간": str,
                    "납입기간": str,
                    "보험료": int,         # 원 단위
                    "갱신형": bool,
                },
                ...
            ],
        }
    """
    stream = io.BytesIO(pdf_bytes)
    pdf = pdfplumber.open(stream)
    try:
        return _do_parse(pdf)
    finally:
        pdf.close()


def _do_parse(pdf) -> dict:
    result: dict = {"상품명": "", "보험료합계": 0, "특약목록": []}

    # Page 6 부근에서 "주계약 및 특약 보험료" 테이블을 찾는다
    for page in pdf.pages:
        tables = page.extract_tables()
        for tbl in tables:
            if not tbl or len(tbl) < 3:
                continue
            if _is_rider_table(tbl):
                _extract_riders(tbl, result)
                return result

    return result


def _is_rider_table(tbl: list[list]) -> bool:
    """'주계약 및 특약 보험료' 테이블인지 판별"""
    for row in tbl[:3]:
        joined = " ".join(str(c or "") for c in row)
        if "특약" in joined and "보험료" in joined:
            return True
    return False


def _extract_riders(tbl: list[list], result: dict):
    """테이블에서 특약 행을 파싱한다.

    예상 열 구조 (8열):
      상품명 | (merge) | 가입금액 | (merge) | 대표지급금액 | 보험기간 | 납입기간 | 보험료
    """
    header_idx = _find_header_row(tbl)
    if header_idx < 0:
        return

    # 열 인덱스 결정 — 헤더에서 '대표지급금액', '보험기간', '납입기간', '보험료' 위치
    col_map = _detect_columns(tbl[header_idx])

    for row in tbl[header_idx + 1:]:
        name_raw = str(row[0] or "").strip()

        # [번호] 로 시작하는 행 = 특약/주계약
        m = re.match(r"\[(\d[\d\-]*)\]\s*(.*)", name_raw, re.DOTALL)
        if not m:
            # 보험료 합계 행 — 아무 셀에서나 금액 찾기
            if "합계" in name_raw:
                total = _find_won_in_row(row)
                if total:
                    result["보험료합계"] = total
            continue

        번호 = f"[{m.group(1)}]"
        특약명 = _clean_name(m.group(2))

        # 주계약이면 상품명으로 저장
        if 번호 == "[1]":
            result["상품명"] = 특약명

        대표 = _parse_man(row, col_map.get("대표지급금액"))
        보험기간 = _get_cell(row, col_map.get("보험기간"))
        납입기간 = _get_cell(row, col_map.get("납입기간"))
        보험료 = _parse_won(row, col_map.get("보험료"))
        갱신형 = "갱신" in 보험기간 or "갱신" in 특약명

        result["특약목록"].append({
            "번호": 번호,
            "특약명": 특약명,
            "대표지급금액": 대표,
            "보험기간": 보험기간,
            "납입기간": 납입기간,
            "보험료": 보험료,
            "갱신형": 갱신형,
        })


def _find_header_row(tbl: list[list]) -> int:
    for i, row in enumerate(tbl):
        joined = " ".join(str(c or "") for c in row)
        if "상품명" in joined and "보험료" in joined:
            return i
    return -1


def _detect_columns(header_row: list) -> dict[str, int]:
    """헤더 행에서 각 열의 인덱스를 찾는다."""
    col_map: dict[str, int] = {}
    targets = ["대표지급금액", "보험기간", "납입기간", "보험료"]
    for i, cell in enumerate(header_row):
        text = str(cell or "").replace("\n", "").strip()
        for t in targets:
            if t in text and t not in col_map:
                col_map[t] = i
                break
    return col_map


def _get_cell(row: list, idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ""
    return str(row[idx] or "").replace("\n", " ").strip()


def _parse_man(row: list, idx: int | None) -> int:
    """'1,000만원' → 1000 (만원 단위 정수)"""
    text = _get_cell(row, idx)
    if not text:
        return 0
    text = text.split("\n")[0].strip()
    # "1,000만원" or "1,000 만원"
    m = re.search(r"([\d,]+)\s*만\s*원", text)
    if m:
        return int(m.group(1).replace(",", ""))
    # 숫자만 있으면 그대로
    m = re.search(r"([\d,]+)", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return 0


def _parse_won(row: list, idx: int | None) -> int:
    """'60,023원' → 60023 (원 단위 정수)"""
    text = _get_cell(row, idx)
    if not text:
        return 0
    m = re.search(r"([\d,]+)\s*원", text)
    if m:
        return int(m.group(1).replace(",", ""))
    m = re.search(r"([\d,]+)", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return 0


def _find_won_in_row(row: list) -> int:
    """행 전체에서 '원' 단위 금액을 찾는다."""
    for cell in row:
        text = str(cell or "").strip()
        m = re.search(r"([\d,]+)\s*원", text)
        if m:
            return int(m.group(1).replace(",", ""))
    return 0


def _clean_name(raw: str) -> str:
    """특약명 정리 — 줄바꿈 제거, 공백 정규화"""
    name = raw.replace("\n", " ").strip()
    name = re.sub(r"\s+", " ", name)
    return name
