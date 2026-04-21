"""PDF 가입상품상세 파싱 + 검증 (pdf_extractor에서 분리)"""
import re
from services.item_map import ITEM_ROW_MAP, find_row_for_item
from services.pdf_extractor import parse_amount

# 동일 이름(truncated)이 N회 반복되면 각 subtype 행으로 순차 분배
# "특정순환계질환주요치료비특약..."가 5회 반복 → Row 49~53
# "상급종합병원(...)암주요치..."가 4회 반복 → Row 30~33
# 키: 이름에 포함되어야 할 서브스트링 / 값: 순차 분배할 행 리스트
_EXPAND_GROUPS = [
    ("특정순환계", [49, 50, 51, 52, 53]),
    ("암주요치", [30, 31, 32, 33]),  # "상급종합병원...암주요치" truncated
]


def parse_detail_pages(pdf, all_contracts: list, coverage_raw: dict,
                       seen_rows: dict = None):
    """Page 9~17 가입상품상세에서 누락된 보장금액 보완 (원→만원 변환).
    seen_rows: Page 6~8에서 확인된 항목 (값 0 포함). 여기 있는 항목은 덮어쓰지 않음.
    """
    if seen_rows is None:
        seen_rows = {}
    total_pages = len(pdf.pages)
    if total_pages <= 6:
        return

    matched_indices = set()

    # 세로 포맷은 상세 페이지가 index 7부터, 가로는 index 8부터 시작
    # 텍스트 필터("가입상품상세")로 자동 구분하므로 6부터 안전하게 탐색
    for pg_idx in range(6, min(total_pages, 30)):
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

        contract_seen = seen_rows.get(contract_idx, set())
        tables = pg.extract_tables()
        for tbl in tables:
            if not tbl or len(tbl) < 2:
                continue
            _extract_detail_table(tbl, contract_idx, coverage_raw, contract_seen)


def _match_detail_to_contract(text: str, all_contracts: list, already_matched: set):
    """상세 페이지 텍스트에서 보험사+상품명 매칭 → contract _idx"""
    text_clean = text.replace("\n", " ").replace(" ", "")

    # 1차: 보험사 + 상품명 전체 매칭
    for c in all_contracts:
        ci = c["_idx"]
        if ci in already_matched:
            continue
        comp = c["보험사"].replace("\n", "").replace(" ", "")
        prod = c["상품명"].replace("\n", "").replace(" ", "")[:20]
        if comp in text_clean and prod in text_clean:
            return ci

    # 2차: 보험사 + 상품명 앞 10자 매칭 (축약된 상품명 대응)
    for c in all_contracts:
        ci = c["_idx"]
        if ci in already_matched:
            continue
        comp = c["보험사"].replace("\n", "").replace(" ", "")
        prod = c["상품명"].replace("\n", "").replace(" ", "")[:10]
        if comp in text_clean and prod and prod in text_clean:
            return ci

    # 보험사만으로 매칭하지 않음 — 같은 보험사 다른 상품 오배정 방지
    return None


def _extract_detail_table(tbl: list, contract_idx: int, coverage_raw: dict,
                          contract_seen: set = None):
    """상세 보장 테이블에서 (보장명, 보장금액) 추출. 원→만원 변환.

    중요: 동일 truncated 이름이 N회 반복되면 _EXPAND_GROUPS 규칙으로
    Row 49~53(특정순환계) 또는 Row 30~33(암주요치)에 순차 분배.
    """
    if contract_seen is None:
        contract_seen = set()
    ncols = len(tbl[0]) if tbl[0] else 0

    # 1단계: (name, amount_str) 쌍을 읽는 순서대로 수집
    pairs: list[tuple[str, str]] = []
    if ncols == 5:
        for row in tbl:
            if not row:
                continue
            name1 = (row[0] or "").strip()
            amt1 = (row[2] or "").strip()
            name2 = (row[3] or "").strip()
            amt2 = (row[4] or "").strip()
            if name1 and amt1:
                pairs.append((name1, amt1))
            if name2 and amt2:
                pairs.append((name2, amt2))
    elif ncols == 2:
        for row in tbl:
            if not row:
                continue
            name = (row[0] or "").strip()
            amt = (row[1] or "").strip()
            if name and amt:
                pairs.append((name, amt))

    # 2단계: 동일 키워드 그룹 묶어서 분배 (선순위: _EXPAND_GROUPS)
    used_indices: set[int] = set()
    for kw, rows in _EXPAND_GROUPS:
        # "비급여암주요치료"는 Row 34 단독 처리 대상 — 그룹 분배에서 제외
        group_idxs = [
            i for i, (n, _) in enumerate(pairs)
            if kw in n and i not in used_indices and "비급여" not in n
        ]
        if not group_idxs:
            continue

        # 단일 항목 + 상급종합병원 암주요치: Row 30~33 모든 subtype에 동일 금액 복제
        # (신한/교보 특약은 통상 1회 지급이나 subtype 전체 대상이므로 합계 왜곡 방지 위해 복제)
        if kw == "암주요치" and len(group_idxs) == 1:
            idx = group_idxs[0]
            name, amt = pairs[idx]
            if "상급종합병원" in name or "상급병원" in name:
                for r in rows:  # 30, 31, 32, 33
                    _apply_detail_item(
                        name, amt, contract_idx, coverage_raw, contract_seen,
                        row_override=r,
                    )
                used_indices.add(idx)
                continue

        # N개 순차 분배 (N개 → rows[0]~rows[N-1])
        if len(group_idxs) >= 2:
            for seq, idx in enumerate(group_idxs):
                if seq >= len(rows):
                    break
                name, amt = pairs[idx]
                _apply_detail_item(
                    name, amt, contract_idx, coverage_raw, contract_seen,
                    row_override=rows[seq],
                )
                used_indices.add(idx)

    # 3단계: 나머지는 기존 키워드 매칭 로직
    for i, (name, amt) in enumerate(pairs):
        if i in used_indices:
            continue
        _apply_detail_item(name, amt, contract_idx, coverage_raw, contract_seen)


def _apply_detail_item(name: str, amount_str: str, contract_idx: int,
                       coverage_raw: dict, contract_seen: set = None,
                       row_override: int = None):
    """보장명+금액(원 단위) → 매핑된 행에 만원 단위로 저장 (누락분만 보완).
    Page 6에서 이미 확인된(0 포함) 항목은 덮어쓰지 않음.
    row_override 지정 시 ITEM_ROW_MAP 매칭 무시하고 지정 행에 저장 (분배 용도).
    """
    if contract_seen is None:
        contract_seen = set()
    if not name or not amount_str:
        return
    if name in ("보장명", "구분", ""):
        return

    if row_override is not None:
        row_num = row_override
    else:
        row_num = find_row_for_item(name)
    if row_num is None:
        return

    # Coverage table(Page 6~8)에서 확인된 항목은 덮어쓰지 않음 (0이어도)
    # 0 = "이 계약에 해당 보장 없음"이므로 detail page로 채우면 안 됨
    # row_override는 특약 분배 용도(특정순환계 등)라서 검사 생략
    if row_override is None and row_num in contract_seen:
        return

    amount_won = parse_amount(amount_str)
    if amount_won <= 0:
        return
    amount_man = amount_won // 10000
    # 만원 변환 시 0이면 → 이미 만원 단위일 가능성 (실비 5,000 등)
    if amount_man <= 0:
        amount_man = amount_won

    key = str(row_num)
    existing = coverage_raw[contract_idx].get(key, 0)
    if existing == 0:
        coverage_raw[contract_idx][key] = amount_man


def verify_coverages(pdf, coverage_raw: dict) -> list[str]:
    """Page 4~5 보장진단 합계와 coverage_raw 비교 → 경고 목록"""
    warnings = []
    total_pages = len(pdf.pages)

    summary_items = {}
    seen_keys_global = set()  # 페이지 간 중복 방지 (세로 PDF는 양쪽 페이지에 동일 항목)
    for pg_idx in range(3, min(6, total_pages)):
        pg = pdf.pages[pg_idx]
        text = pg.extract_text() or ""
        if "보장진단" not in text and "분석결과" not in text:
            continue
        tables = pg.extract_tables()
        page_seen = set()
        for tbl in tables:
            if not tbl:
                continue
            for row in tbl:
                if not row or len(row) < 2:
                    continue
                # col 0이 카테고리명이면 col 1을 사용
                name = (row[0] or "").strip()
                if name in ("사망보장", "후유장해", "암보장", "뇌,심장 보장",
                            "뇌, 심장 보장", "말기질환, 치매 보장", "말기질환,치매 보장",
                            "수술비", "입원비", "치료비, 기타", "치료비,기타",
                            "의료비", "말기질환,\n 치매 보장", "뇌,\n 심장 보장",
                            "치료비,\n 기타"):
                    name = (row[1] or "").strip() if len(row) > 1 else ""
                if not name:
                    continue
                row_num = find_row_for_item(name)
                if row_num is None:
                    continue
                key = str(row_num)
                # 동일 항목 중복 집계 방지 (페이지 내 + 페이지 간)
                if key in page_seen or key in seen_keys_global:
                    continue
                # "미가입" 항목은 건너뛰기 (필요보장만 있고 실제 가입 안됨)
                row_text = " ".join(str(c or "") for c in row)
                if "미가입" in row_text:
                    continue
                for cell in reversed(row[1:]):
                    val = parse_amount(cell)
                    if val > 0:
                        summary_items[key] = val
                        page_seen.add(key)
                        seen_keys_global.add(key)
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
