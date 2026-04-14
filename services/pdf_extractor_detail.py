"""PDF 가입상품상세 파싱 + 검증 (pdf_extractor에서 분리)"""
import re
from services.item_map import ITEM_ROW_MAP, find_row_for_item
from services.pdf_extractor import parse_amount


def parse_detail_pages(pdf, all_contracts: list, coverage_raw: dict):
    """Page 9~17 가입상품상세에서 누락된 보장금액 보완 (원→만원 변환)"""
    total_pages = len(pdf.pages)
    if total_pages <= 8:
        return

    matched_indices = set()

    for pg_idx in range(8, min(total_pages, 18)):
        pg = pdf.pages[pg_idx]
        text = pg.extract_text() or ""

        if "가입상품상세" not in text and "상세 보장" not in text:
            continue

        contract_idx = _match_detail_to_contract(text, all_contracts, matched_indices)
        if contract_idx is None:
            continue
        matched_indices.add(contract_idx)

        if contract_idx not in coverage_raw:
            coverage_raw[contract_idx] = {}

        tables = pg.extract_tables()
        for tbl in tables:
            if not tbl or len(tbl) < 2:
                continue
            _extract_detail_table(tbl, contract_idx, coverage_raw)


def _match_detail_to_contract(text: str, all_contracts: list, already_matched: set):
    """상세 페이지 텍스트에서 보험사+상품명 매칭 → contract _idx"""
    text_clean = text.replace("\n", " ").replace(" ", "")

    for c in all_contracts:
        ci = c["_idx"]
        if ci in already_matched:
            continue
        comp = c["보험사"].replace("\n", "").replace(" ", "")
        prod = c["상품명"].replace("\n", "").replace(" ", "")[:20]
        if comp in text_clean and prod in text_clean:
            return ci

    for c in all_contracts:
        ci = c["_idx"]
        if ci in already_matched:
            continue
        comp = c["보험사"].replace("\n", "").replace(" ", "")
        if comp in text_clean:
            return ci
    return None


def _extract_detail_table(tbl: list, contract_idx: int, coverage_raw: dict):
    """상세 보장 테이블에서 (보장명, 보장금액) 추출. 원→만원 변환."""
    ncols = len(tbl[0]) if tbl[0] else 0

    if ncols == 5:
        for row in tbl:
            if not row:
                continue
            _apply_detail_item(
                (row[0] or "").strip(), (row[2] or "").strip(),
                contract_idx, coverage_raw,
            )
            _apply_detail_item(
                (row[3] or "").strip(), (row[4] or "").strip(),
                contract_idx, coverage_raw,
            )

    elif ncols == 2:
        for row in tbl:
            if not row:
                continue
            _apply_detail_item(
                (row[0] or "").strip(), (row[1] or "").strip(),
                contract_idx, coverage_raw,
            )


def _apply_detail_item(name: str, amount_str: str, contract_idx: int, coverage_raw: dict):
    """보장명+금액(원 단위) → 매핑된 행에 만원 단위로 저장 (누락분만 보완)"""
    if not name or not amount_str:
        return
    if name in ("보장명", "구분", ""):
        return

    row_num = find_row_for_item(name)
    if row_num is None:
        return

    amount_won = parse_amount(amount_str)
    if amount_won <= 0:
        return
    amount_man = amount_won // 10000
    if amount_man <= 0:
        return

    key = str(row_num)
    existing = coverage_raw[contract_idx].get(key, 0)
    if existing == 0:
        coverage_raw[contract_idx][key] = amount_man


def verify_coverages(pdf, coverage_raw: dict) -> list[str]:
    """Page 4~5 보장진단 합계와 coverage_raw 비교 → 경고 목록"""
    warnings = []
    total_pages = len(pdf.pages)

    summary_items = {}
    seen_keys_per_page = {}
    for pg_idx in range(3, min(5, total_pages)):
        pg = pdf.pages[pg_idx]
        tables = pg.extract_tables()
        page_seen = set()
        for tbl in tables:
            if not tbl:
                continue
            for row in tbl:
                if not row or len(row) < 2:
                    continue
                name = (row[0] or "").strip()
                if not name:
                    continue
                row_num = find_row_for_item(name)
                if row_num is None:
                    continue
                key = str(row_num)
                # 같은 페이지에서 동일 항목 중복 집계 방지
                if key in page_seen:
                    continue
                for cell in reversed(row[1:]):
                    val = parse_amount(cell)
                    if val > 0:
                        summary_items[key] = summary_items.get(key, 0) + val
                        page_seen.add(key)
                        break

    if not summary_items:
        return warnings

    extracted_sums = {}
    for ci, cov in coverage_raw.items():
        for key, val in cov.items():
            extracted_sums[key] = extracted_sums.get(key, 0) + val

    for key, expected in summary_items.items():
        actual = extracted_sums.get(key, 0)
        if actual == 0 and expected > 0:
            # 누락 항목 → 페이지 4~5 데이터로 자동 보충
            _fill_missing(coverage_raw, key, expected)
            if expected > 100:
                row_num = int(key)
                name = _row_to_name(row_num)
                warnings.append(f"자동보충: {name}(행{row_num}) — 진단 합계 {expected}만원")
        elif actual > 0 and expected > 0 and abs(actual - expected) / max(actual, expected) > 0.3:
            name = _row_to_name(int(key))
            warnings.append(
                f"불일치: {name} — 진단 {expected}만원 vs 추출 {actual}만원"
            )

    return warnings


def _fill_missing(coverage_raw: dict, key: str, total: int):
    """누락 항목을 가장 많은 보장을 가진 계약에 배분"""
    if not coverage_raw:
        return
    # 보장 항목이 가장 많은 계약에 할당
    best_ci = max(coverage_raw.keys(), key=lambda ci: len(coverage_raw[ci]))
    coverage_raw[best_ci][key] = total


def _row_to_name(row_num: int) -> str:
    """행 번호 → 대표 항목명"""
    for name, rn in ITEM_ROW_MAP.items():
        if rn == row_num and len(name) >= 3:
            return name
    return f"항목{row_num}"
