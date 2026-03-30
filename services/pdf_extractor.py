"""PDF에서 보장분석 데이터 추출 (pdfplumber)"""
import re
import pdfplumber
from services.item_map import ITEM_ROW_MAP, INSURER_KEYWORDS, find_row_for_item

COL_LTRS_EXT = ["D", "E", "F", "G", "H", "I", "J", "K", "L"]


def parse_amount(s) -> int:
    """금액 문자열 → 만원 단위 숫자"""
    if not s:
        return 0
    s = str(s).strip().replace(",", "").replace(" ", "")
    if not s or s == "-" or s == "None":
        return 0
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def extract_from_pdf(pdf_bytes) -> dict:
    """PDF 바이트에서 보장분석 데이터 추출"""
    pdf = pdfplumber.open(pdf_bytes)

    result = {
        "고객명": "", "성별": "", "나이": 0,
        "_all_contracts": [], "_coverage_raw": {},
        "계약": [], "보장금액": {},
        "기납입보험료": {}, "납입할보험료": {},
        "_warnings": [],
    }

    p1_text = pdf.pages[0].extract_text() or ""

    # Page 1: 고객명
    m = re.search(r"(\S+)\s*고객님", p1_text)
    if not m:
        m = re.search(r"(\S+)\s*님의", p1_text)
    if m:
        result["고객명"] = m.group(1)

    # Page 3: 계약현황
    p3 = pdf.pages[2]
    p3_text = p3.extract_text() or ""
    all_contracts = _parse_contracts(p3)

    # 성별/나이
    _extract_demographics(result, pdf, p1_text, p3_text)

    # 보장금액: Page 6~8 (상품별 보장금액)
    coverage_raw = _parse_coverages(pdf, all_contracts)

    # 보완: Page 9~17 (가입상품상세) 파싱
    _parse_detail_pages(pdf, all_contracts, coverage_raw)

    # 검증: Page 4~5 보장진단 합계와 비교
    warnings = _verify_coverages(pdf, coverage_raw)
    result["_warnings"] = warnings

    pdf.close()

    # 결과 조립
    result["_all_contracts"] = all_contracts
    result["_coverage_raw"] = coverage_raw
    result["계약"] = all_contracts[:7]

    for c in all_contracts:
        col = c["열"]
        result["기납입보험료"][col] = c["_paid"]
        result["납입할보험료"][col] = c["_topay"]
        if c["_idx"] in coverage_raw:
            result["보장금액"][col] = coverage_raw[c["_idx"]]

    return result


def _parse_contracts(p3) -> list:
    """Page 3 테이블에서 계약 파싱 (중복 제거 없음 — 동일 상품 복수 가입 허용)"""
    tables3 = p3.extract_tables()
    all_contracts = []

    for tbl in tables3:
        if not tbl or len(tbl) < 4:
            continue
        for row in tbl:
            if not row or len(row) < 12:
                continue
            r0 = (row[0] or "").strip()
            if not any(k in r0 for k in INSURER_KEYWORDS):
                continue

            product = (row[1] or "").strip()

            idx = len(all_contracts)
            col_ltr = COL_LTRS_EXT[idx] if idx < len(COL_LTRS_EXT) else "L"
            start = (row[4] or "").strip() if len(row) > 4 else ""
            end_age = (row[6] or "").strip() if len(row) > 6 else ""
            end_month = (row[5] or "").strip() if len(row) > 5 else ""
            premium = int(re.sub(r"[^\d]", "", row[11] or "0") or "0") if len(row) > 11 else 0
            paid_amt = int(re.sub(r"[^\d]", "", row[12] or "0") or "0") if len(row) > 12 else 0
            topay_amt = int(re.sub(r"[^\d]", "", row[13] or "0") or "0") if len(row) > 13 else 0
            period = f"{end_age}만기" if end_age else end_month

            all_contracts.append({
                "_idx": idx, "열": col_ltr,
                "보험사": r0, "상품명": product,
                "보장나이": period, "월보험료": premium,
                "가입시기": start, "_paid": paid_amt, "_topay": topay_amt,
            })

    return all_contracts


def _extract_demographics(result: dict, pdf, p1_text: str, p3_text: str):
    """성별/나이 추출"""
    m_tag = re.search(r"#(\d+)대\s*#(남|여)성", p3_text)
    if m_tag:
        result["성별"] = m_tag.group(2)
        result["나이"] = int(m_tag.group(1)) + 8

    p2_text = pdf.pages[1].extract_text() or "" if len(pdf.pages) > 1 else ""
    m_info = re.search(r"/\s*(\d+)\s*/\s*(남|여)성", p2_text)
    if m_info:
        result["나이"] = int(m_info.group(1))
        result["성별"] = m_info.group(2)
    else:
        m_age = re.search(r"(남|여)\s*/?\s*(\d+)\s*세", p1_text + p2_text + p3_text)
        if m_age:
            result["나이"] = int(m_age.group(2))
            result["성별"] = m_age.group(1)


def _parse_coverages(pdf, all_contracts: list) -> dict:
    """Page 6~8에서 보장금액 추출"""
    coverage_raw = {}
    mapped_indices = set()
    total_pages = len(pdf.pages)

    for pg_idx in range(5, min(5 + 3, total_pages)):
        pg = pdf.pages[pg_idx]
        tables = pg.extract_tables()
        data_tbl = item_tbl = None
        for t in tables:
            if not t:
                continue
            r, c = len(t), len(t[0]) if t[0] else 0
            if c == 9 and r >= 25:
                data_tbl = t
            elif c == 7 and r >= 20:
                item_tbl = t
        if not data_tbl or not item_tbl:
            continue

        page_pos_map = {}
        comp_row = data_tbl[1]
        prod_row = data_tbl[2]
        for pos in range(4):
            col = pos * 2
            comp = (comp_row[col] or "").strip().replace("\n", "").replace(" ", "")
            prod = (prod_row[col] or "").strip().replace("\n", "").replace(" ", "")[:15]
            if not comp:
                continue
            for c in all_contracts:
                ci = c["_idx"]
                if ci in mapped_indices:
                    continue
                cn = c["보험사"].replace("\n", "").replace(" ", "")
                cp = c["상품명"].replace("\n", "").replace(" ", "")[:15]
                if (comp in cn or cn in comp) and (prod in cp or cp in prod):
                    page_pos_map[pos] = ci
                    mapped_indices.add(ci)
                    break

        item_pairs = []
        for row in item_tbl[1:]:
            left = (row[1] or "").strip() if len(row) > 1 else ""
            right = (row[4] or "").strip() if len(row) > 4 else ""
            item_pairs.append((left, right))

        for pair_idx, (left_name, right_name) in enumerate(item_pairs):
            data_row_idx = pair_idx + 5
            if data_row_idx >= len(data_tbl):
                break
            dr = data_tbl[data_row_idx]
            for pos, ci in page_pos_map.items():
                if ci not in coverage_raw:
                    coverage_raw[ci] = {}
                li = pos * 2
                ri = pos * 2 + 1
                lv = parse_amount(dr[li] if li < len(dr) else "0")
                if lv and left_name:
                    rn = find_row_for_item(left_name)
                    if rn:
                        coverage_raw[ci][str(rn)] = lv
                rv = parse_amount(dr[ri] if ri < len(dr) else "0")
                if rv and right_name:
                    rn = find_row_for_item(right_name)
                    if rn:
                        coverage_raw[ci][str(rn)] = rv

    return coverage_raw


def _parse_detail_pages(pdf, all_contracts: list, coverage_raw: dict):
    """Page 9~17 가입상품상세에서 누락된 보장금액 보완 (원→만원 변환)"""
    total_pages = len(pdf.pages)
    if total_pages <= 8:
        return

    # 상세 페이지에서 매칭 추적 (동일 상품 복수 가입 지원)
    matched_indices = set()

    for pg_idx in range(8, min(total_pages, 18)):
        pg = pdf.pages[pg_idx]
        text = pg.extract_text() or ""

        if "가입상품상세" not in text and "상세 보장" not in text:
            continue

        # 보험사+상품명으로 계약 매칭 (이미 매칭된 건 건너뛰기)
        contract_idx = _match_detail_to_contract(text, all_contracts, matched_indices)
        if contract_idx is None:
            continue
        matched_indices.add(contract_idx)

        if contract_idx not in coverage_raw:
            coverage_raw[contract_idx] = {}

        # 테이블에서 (보장명, 보장금액) 쌍 추출
        tables = pg.extract_tables()
        for tbl in tables:
            if not tbl or len(tbl) < 2:
                continue
            _extract_detail_table(tbl, contract_idx, coverage_raw)


def _match_detail_to_contract(text: str, all_contracts: list, already_matched: set):
    """상세 페이지 텍스트에서 보험사+상품명 매칭 → contract _idx"""
    text_clean = text.replace("\n", " ").replace(" ", "")

    # 정확 매치 (보험사+상품명) 우선
    for c in all_contracts:
        ci = c["_idx"]
        if ci in already_matched:
            continue
        comp = c["보험사"].replace("\n", "").replace(" ", "")
        prod = c["상품명"].replace("\n", "").replace(" ", "")[:20]
        if comp in text_clean and prod in text_clean:
            return ci

    # 보험사만 매치 (fallback)
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

    # 5열 테이블: [보장명, None, 보장금액, 보장명, 보장금액]
    if ncols == 5:
        for row in tbl:
            if not row:
                continue
            # 왼쪽 쌍: col0=보장명, col2=금액
            _apply_detail_item(
                (row[0] or "").strip(), (row[2] or "").strip(),
                contract_idx, coverage_raw,
            )
            # 오른쪽 쌍: col3=보장명, col4=금액
            _apply_detail_item(
                (row[3] or "").strip(), (row[4] or "").strip(),
                contract_idx, coverage_raw,
            )

    # 2열 테이블: [보장명, 보장금액]
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

    # 헤더 행 무시
    if name in ("보장명", "구분", ""):
        return

    row_num = find_row_for_item(name)
    if row_num is None:
        return

    # 원 단위 → 만원 변환
    amount_won = parse_amount(amount_str)
    if amount_won <= 0:
        return
    amount_man = amount_won // 10000  # 원→만원
    if amount_man <= 0:
        return

    key = str(row_num)
    existing = coverage_raw[contract_idx].get(key, 0)
    # 기존 값이 없는 경우(누락분)에만 보완
    if existing == 0:
        coverage_raw[contract_idx][key] = amount_man


def _verify_coverages(pdf, coverage_raw: dict) -> list[str]:
    """Page 4~5 보장진단 합계와 coverage_raw 비교 → 경고 목록"""
    warnings = []
    total_pages = len(pdf.pages)

    # Page 4~5에서 보장진단 요약 테이블 찾기
    summary_items = {}
    for pg_idx in range(3, min(5, total_pages)):
        pg = pdf.pages[pg_idx]
        tables = pg.extract_tables()
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
                # 합계 열(보통 마지막 열)
                for cell in reversed(row[1:]):
                    val = parse_amount(cell)
                    if val > 0:
                        key = str(row_num)
                        summary_items[key] = summary_items.get(key, 0) + val
                        break

    if not summary_items:
        return warnings

    # coverage_raw 전체 합산과 비교
    extracted_sums = {}
    for ci, cov in coverage_raw.items():
        for key, val in cov.items():
            extracted_sums[key] = extracted_sums.get(key, 0) + val

    for key, expected in summary_items.items():
        actual = extracted_sums.get(key, 0)
        if actual == 0 and expected > 0:
            row_num = int(key)
            # 항목명 역방향 조회
            name = _row_to_name(row_num)
            warnings.append(f"누락 의심: {name}(행{row_num}) — 진단 합계 {expected}만원, 추출 0")
        elif actual > 0 and expected > 0 and abs(actual - expected) / expected > 0.2:
            name = _row_to_name(int(key))
            warnings.append(
                f"불일치: {name} — 진단 {expected}만원 vs 추출 {actual}만원"
            )

    return warnings


def _row_to_name(row_num: int) -> str:
    """행 번호 → 대표 항목명"""
    for name, rn in ITEM_ROW_MAP.items():
        if rn == row_num and len(name) >= 3:
            return name
    return f"항목{row_num}"
