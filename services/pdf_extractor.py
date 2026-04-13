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
    with pdfplumber.open(pdf_bytes) as pdf:
        return _do_extract(pdf)


def _do_extract(pdf) -> dict:
    result = {
        "고객명": "", "성별": "", "나이": 0,
        "_all_contracts": [], "_coverage_raw": {},
        "계약": [], "보장금액": {},
        "기납입보험료": {}, "납입할보험료": {},
        "_warnings": [],
    }

    if len(pdf.pages) < 1:
        return result

    p1_text = pdf.pages[0].extract_text() or ""

    # Page 1: 고객명
    m = re.search(r"(\S+)\s*고객님", p1_text)
    if not m:
        m = re.search(r"(\S+)\s*님의", p1_text)
    if m:
        result["고객명"] = m.group(1)

    # Page 3: 계약현황
    if len(pdf.pages) < 3:
        return result
    p3 = pdf.pages[2]
    p3_text = p3.extract_text() or ""
    all_contracts = _parse_contracts(p3)

    # 성별/나이
    _extract_demographics(result, pdf, p1_text, p3_text)

    # 보장금액: Page 6~8 (상품별 보장금액)
    coverage_raw = _parse_coverages(pdf, all_contracts)

    # 보완: Page 9~17 (가입상품상세) 파싱
    from services.pdf_extractor_detail import parse_detail_pages, verify_coverages
    parse_detail_pages(pdf, all_contracts, coverage_raw)

    # 검증: Page 4~5 보장진단 합계와 비교
    warnings = verify_coverages(pdf, coverage_raw)
    result["_warnings"] = warnings

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
            if not r0 or r0 in ("보험회사", "보험사", "회사명", "구분"):
                continue
            product = (row[1] or "").strip()
            # 상품명 없거나 헤더행이면 스킵
            if not product or product in ("상품명", "보험상품명"):
                continue

            idx = len(all_contracts)
            col_ltr = COL_LTRS_EXT[idx] if idx < len(COL_LTRS_EXT) else "L"
            start = (row[4] or "").strip() if len(row) > 4 else ""
            end_age = (row[6] or "").strip() if len(row) > 6 else ""
            end_month = (row[5] or "").strip() if len(row) > 5 else ""
            premium = int(re.sub(r"[^\d]", "", row[11] or "0") or "0") if len(row) > 11 else 0
            paid_amt = int(re.sub(r"[^\d]", "", row[12] or "0") or "0") if len(row) > 12 else 0
            topay_amt = int(re.sub(r"[^\d]", "", row[13] or "0") or "0") if len(row) > 13 else 0
            period = f"{end_age}만기" if end_age else end_month

            # 납입기간 / 납입횟수 추출
            pay_info = (row[9] or "").strip() if len(row) > 9 else ""
            pay_count = (row[10] or "").strip() if len(row) > 10 else ""
            납입기간 = pay_info.split("/")[-1] if "/" in pay_info else pay_info
            납입개월 = 0
            총납입개월 = 0
            if "/" in pay_count:
                parts = pay_count.split("/")
                납입개월 = int(re.sub(r"[^\d]", "", parts[0]) or "0")
                총납입개월 = int(re.sub(r"[^\d]", "", parts[-1]) or "0")

            all_contracts.append({
                "_idx": idx, "열": col_ltr,
                "보험사": r0, "상품명": product,
                "보장나이": period, "월보험료": premium,
                "가입시기": start, "_paid": paid_amt, "_topay": topay_amt,
                "_납입기간": 납입기간, "_납입개월": 납입개월, "_총납입개월": 총납입개월,
            })

    return all_contracts


def _extract_demographics(result: dict, pdf, p1_text: str, p3_text: str):
    """성별/나이 추출"""
    m_tag = re.search(r"#(\d+)대\s*#(남|여)성", p3_text)
    if m_tag:
        result["성별"] = m_tag.group(2)
        result["나이"] = int(m_tag.group(1)) + 8

    p2_text = (pdf.pages[1].extract_text() or "") if len(pdf.pages) > 1 else ""
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
