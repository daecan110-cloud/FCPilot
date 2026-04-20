"""엑셀 보장분석 — 리뷰/갱신 섹션 (excel_generator에서 분리)"""
import math
import re

from openpyxl.styles import Font, Alignment

from services.item_map import COL_IDX, COL_LTRS, DATA_ROWS
from services.excel_helpers import (
    safe_val, safe_merge, copy_row_style, short_name, classify_renewal,
    _FONT_NAME,
)

_DATA_START = 4
_DATA_END = 10
_MAX_COL = 11
_MAX_COL_PROP = 13
_REVIEW_START = 90
_REVIEW_COUNT = 7


# ── 갱신 구분 ────────────────────────────────────────────

def fill_renewal(ws, contracts):
    """Row 85 갱신 구분, Row 86 보험료 변화 예고"""
    for ct in contracts:
        col = COL_IDX.get(ct["열"], 4)
        renewal, notice = classify_renewal(ct)
        safe_val(ws, 85, col, renewal)
        safe_val(ws, 86, col, notice)


def fill_renewal_all(ws, all_contracts):
    """전체 계약 갱신/보험료변화 (7개씩 그룹, 동적 행 확장)"""
    n_groups = math.ceil(len(all_contracts) / 7)

    if n_groups > 1:
        extra_rows = (n_groups - 1) * 2
        _unmerge_from_row(ws, 87)
        ws.insert_rows(87, extra_rows)

        for i in range(extra_rows):
            r_new = 87 + i
            r_src = 85 + (i % 2)
            copy_row_style(ws, r_src, r_new, cols=range(1, _MAX_COL_PROP + 1))
            src_h = ws.row_dimensions[r_src].height if ws.row_dimensions.get(r_src) else None
            if src_h:
                ws.row_dimensions[r_new].height = src_h

        review_title_row = 88 + extra_rows
        review_hdr_row = review_title_row + 1
        ws.merge_cells(f"A{review_title_row}:K{review_title_row}")
        ws.merge_cells(f"A{review_hdr_row}:B{review_hdr_row}")
        ws.merge_cells(f"E{review_hdr_row}:H{review_hdr_row}")
        ws.merge_cells(f"I{review_hdr_row}:K{review_hdr_row}")

        safe_val(ws, review_title_row, 1, "📋  현재 유지중인 보험 리뷰")
        safe_val(ws, review_hdr_row, 1, "보험사 / 상품명")
        safe_val(ws, review_hdr_row, 3, "가입일 / 만기")
        ws.row_dimensions[review_title_row].height = 28
        ws.row_dimensions[review_hdr_row].height = 20

    for g in range(n_groups):
        chunk = all_contracts[g * 7:(g + 1) * 7]
        renewal_row = 85 + g * 2
        notice_row = 86 + g * 2

        for i, ct in enumerate(chunk):
            col = COL_IDX.get(COL_LTRS[i], 4)
            renewal, notice = classify_renewal(ct)
            safe_val(ws, renewal_row, col, renewal)
            safe_val(ws, notice_row, col, notice)

        for row in (renewal_row, notice_row):
            for c in range(_DATA_START, _DATA_END + 1):
                cell = ws.cell(row=row, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.font = Font(name=_FONT_NAME, size=8, bold=True)
                    cell.alignment = Alignment(
                        horizontal="center", vertical="center", wrap_text=True,
                    )
            ws.row_dimensions[row].height = 26 if row % 2 == 0 else 20

    return (n_groups - 1) * 2


# ── 리뷰 ─────────────────────────────────────────────────

def fill_review(ws, contracts, coverage_map=None):
    """슬라이스 계약 리뷰"""
    for i, c in enumerate(contracts):
        r = _REVIEW_START + i
        cov = (coverage_map or {}).get(c.get("열", ""), {})
        _write_review_row(ws, r, c, cov)


def fill_review_all(ws, all_contracts, all_coverage_raw):
    """전체 계약 리뷰 (동적 행 확장)"""
    n_groups = math.ceil(len(all_contracts) / 7)
    extra_renewal = (n_groups - 1) * 2 if n_groups > 1 else 0

    review_start = _REVIEW_START + extra_renewal
    n_contracts = len(all_contracts)
    extra_review = max(0, n_contracts - _REVIEW_COUNT)

    if extra_review > 0:
        _unmerge_from_row(ws, review_start)
        ws.insert_rows(review_start + _REVIEW_COUNT, extra_review)
        for i in range(extra_review):
            r_new = review_start + _REVIEW_COUNT + i
            r_src = review_start + ((_REVIEW_COUNT + i) % 5)
            copy_row_style(ws, r_src, r_new, cols=range(1, _MAX_COL_PROP + 1))
            ws.row_dimensions[r_new].height = 70

    title_row = review_start - 2
    header_row = review_start - 1
    safe_merge(ws, f"A{title_row}:K{title_row}")
    safe_merge(ws, f"A{header_row}:B{header_row}")
    safe_merge(ws, f"E{header_row}:H{header_row}")
    safe_merge(ws, f"I{header_row}:K{header_row}")
    safe_val(ws, title_row, 1, "📋  현재 유지중인 보험 리뷰")
    safe_val(ws, header_row, 1, "보험사 / 상품명")
    safe_val(ws, header_row, 3, "가입일 / 만기")
    safe_val(ws, header_row, 4, "월 보험료")
    safe_val(ws, header_row, 5, "주요 체크사항")
    safe_val(ws, header_row, 9, "특이사항 (면책기간, 보장범위 등)")

    for i in range(n_contracts):
        r = review_start + i
        safe_merge(ws, f"A{r}:B{r}")
        safe_merge(ws, f"E{r}:H{r}")
        safe_merge(ws, f"I{r}:K{r}")

    for i, c in enumerate(all_contracts):
        r = review_start + i
        cov_data = {}
        if c["_idx"] in all_coverage_raw:
            cov_data = {str(k): v for k, v in all_coverage_raw[c["_idx"]].items()}
        _write_review_row(ws, r, c, cov_data)

        for col_n in range(1, _MAX_COL + 1):
            cell = ws.cell(row=r, column=col_n)
            if cell.__class__.__name__ != "MergedCell":
                cell.font = Font(name=_FONT_NAME, size=8, bold=True)
                cell.alignment = Alignment(
                    horizontal="left", vertical="center", wrap_text=True,
                )
        ws.row_dimensions[r].height = 70


def _write_review_row(ws, r: int, c: dict, cov_data: dict):
    """리뷰 행 1줄 쓰기 (fill_review / fill_review_all 공통)"""
    safe_val(ws, r, 1, short_name(c))
    period = c.get("보장나이", "")
    start = c.get("가입시기", "")
    safe_val(ws, r, 3, f"{start}\n({period})" if start else period)
    prem = c.get("월보험료", 0)
    safe_val(ws, r, 4, f"{prem:,.0f}원" if prem else "납입완료")
    safe_val(ws, r, 5, build_review(c, coverage_data=cov_data))


# ── 리뷰 텍스트 생성 ─────────────────────────────────────

def build_review(contract, coverage_data=None):
    name = contract.get("상품명", "")
    company = contract.get("보험사", "")
    combined = name + company
    period = contract.get("보장나이", "")
    premium = contract.get("월보험료", 0)
    checks = []

    if any(k in combined for k in ["단체", "단기"]):
        checks.append("단체/단기계약 — 퇴직·탈퇴 시 자동 소멸")
    elif any(k in combined for k in ["실손", "의료비"]):
        start_date = contract.get("가입시기", "")
        gen = _detect_silbi_gen(name, company, start_date)
        checks.append(f"실손의료비 {gen} (갱신형)")
    elif any(k in combined for k in ["종신"]) and any(k in combined for k in ["변액", "유니버셜"]):
        checks.append("변액유니버셜종신 — 수익률·적립금 확인 필요")
    elif any(k in combined for k in ["종신"]):
        checks.append("종신보험 — 비갱신형")
    elif any(k in combined for k in ["운전자", "자동차"]):
        checks.append("운전자보험 — 교통상해/벌금/변호사비 보장")
    elif any(k in combined for k in ["CI"]):
        checks.append("CI보험 — 중대질병 진단 시 보험금 지급")
    elif any(k in combined for k in ["치아"]):
        checks.append(f"치아보험 ({period})")
    elif any(k in combined for k in ["건강", "상해", "종합"]):
        checks.append(f"건강/상해 보장 ({period})")
    elif any(k in combined for k in ["암"]):
        checks.append(f"암보험 ({period})")
    elif any(k in combined for k in ["저축", "연금", "적립"]):
        checks.append(f"저축/연금 ({period})")
    else:
        checks.append(f"보장기간: {period}")

    if premium == 0:
        checks.append("납입완료")

    if coverage_data:
        highlights = _coverage_highlights(coverage_data)
        if highlights:
            checks.append(highlights)

    return " / ".join(checks)


def _detect_silbi_gen(name: str, company: str, start_date: str = "") -> str:
    """실손의료비 세대 판별"""
    combined = name + company

    if any(k in combined for k in ["착한", "비급여특약"]):
        return "4세대"
    if any(k in combined for k in ["4세대", "신실손"]):
        return "4세대"
    if any(k in combined for k in ["표준화", "3세대"]):
        return "3세대"
    if any(k in combined for k in ["단독", "2세대"]):
        return "2세대"
    if any(k in combined for k in ["1세대"]):
        return "1세대"
    if any(k in combined for k in ["5세대"]):
        return "5세대"

    m = re.search(r"(20[0-2]\d)", name)
    if m:
        year = int(m.group(1))
        if year >= 2026:
            return "5세대"
        if year >= 2017:
            return "4세대"

    if start_date:
        m = re.match(r"(\d{4})-?(\d{2})?", start_date)
        if m:
            y = int(m.group(1))
            mo = int(m.group(2) or "1")
            ym = y * 100 + mo
            if ym >= 202605:
                return "5세대"
            if ym >= 201704:
                return "4세대"
            if ym >= 201301:
                return "3세대"
            if ym >= 200910:
                return "2세대"
            return "1세대"

    return "(세대 확인 필요)"


def _coverage_highlights(cov: dict) -> str:
    """주요 보장 항목 요약"""
    labels = {
        "9": "사망", "17": "일반암", "44": "심근경색",
        "39": "뇌혈관", "76": "실비",
    }
    parts = []
    for row_str, label in labels.items():
        amt = cov.get(row_str, 0)
        if amt:
            parts.append(f"{label} {amt:,}")
    return " / ".join(parts) if parts else ""


# ── 내부 유틸 ─────────────────────────────────────────────

def _unmerge_from_row(ws, from_row: int):
    """from_row 이후의 병합 해제 (insert_rows 전 필수)"""
    from openpyxl.utils.cell import range_boundaries
    to_remove = [str(mg) for mg in ws.merged_cells.ranges if mg.min_row >= from_row]
    for r in to_remove:
        ws.merged_cells.ranges = [m for m in ws.merged_cells.ranges if str(m) != r]
        mc, mr, xc, xr = range_boundaries(r)
        for row in range(mr, xr + 1):
            for col in range(mc, xc + 1):
                if (row, col) in ws._cells and ws._cells[(row, col)].__class__.__name__ == "MergedCell":
                    del ws._cells[(row, col)]
