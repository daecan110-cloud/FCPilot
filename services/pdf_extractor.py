"""PDF에서 보장분석 데이터 추출 (pdfplumber)"""
import re
import pdfplumber
from services.item_map import ITEM_ROW_MAP, INSURER_KEYWORDS, find_row_for_item

# PDF에서 최대 9개 계약 추출, 엑셀에는 최대 7개만 사용
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

    # Page 3(+4): 계약현황 — 다건 계약 시 Page 4까지 연장
    if len(pdf.pages) < 3:
        return result
    p3 = pdf.pages[2]
    p3_text = p3.extract_text() or ""
    extra_pages = []
    if len(pdf.pages) > 3:
        p4_text = pdf.pages[3].extract_text() or ""
        if "계약현황" in p4_text or "보유계약" in p4_text:
            extra_pages.append(pdf.pages[3])
    all_contracts = _parse_contracts(p3, extra_pages)

    # 성별/나이
    _extract_demographics(result, pdf, p1_text, p3_text)

    # 보장금액: Page 6~8 (상품별 보장금액)
    coverage_raw, seen_rows = _parse_coverages(pdf, all_contracts)

    # 보완: Page 9~17 (가입상품상세) 파싱 — Page 6에서 0인 항목은 덮어쓰지 않음
    from services.pdf_extractor_detail import parse_detail_pages, verify_coverages
    parse_detail_pages(pdf, all_contracts, coverage_raw, seen_rows)

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


def _parse_contracts(p3, extra_pages=None) -> list:
    """계약현황 테이블에서 계약 파싱 (다중 페이지, 열 레이아웃 자동 감지)"""
    all_contracts = []
    pages = [p3] + (extra_pages or [])

    for pg in pages:
        tables = pg.extract_tables()
        for tbl in tables:
            if not tbl or len(tbl) < 3:
                continue
            layout = _detect_table_layout(tbl)
            if layout:
                _parse_contract_table(tbl, layout, all_contracts)
            elif not all_contracts:
                _parse_contract_table_vertical(tbl, all_contracts)

    return all_contracts


def _detect_table_layout(tbl):
    """헤더 행에서 열 위치 자동 감지"""
    for row in tbl[:3]:
        if not row:
            continue
        header = [(c or "").strip() for c in row]
        joined = "".join(header)
        if "회사명" not in joined and "보험회사" not in joined and "보험사" not in joined:
            continue
        ci = pi = si = pmi = pai = toi = pii = pci = None
        for i, h in enumerate(header):
            if h in ("회사명", "보험회사", "보험사"):
                ci = i
            elif h in ("상품명", "보험상품명"):
                pi = i
            elif "계약월" in h or "계약일" in h:
                si = i
            elif "보험료" in h:
                pmi = i
        if ci is not None and pi is not None:
            ncols = len(header)
            return {"company": ci, "product": pi, "ncols": ncols,
                    "start": si, "premium": pmi}
    return None


def _parse_contract_table(tbl, layout, all_contracts):
    """감지된 레이아웃으로 계약 행 파싱"""
    ci_col = layout["company"]
    pi_col = layout["product"]
    ncols = layout["ncols"]

    for row in tbl:
        if not row or len(row) < 6:
            continue
        company = (row[ci_col] or "").strip()
        if not company:
            continue
        # 헤더/면책 행 필터
        if company in ("보험회사", "보험사", "회사명", "구분"):
            continue
        if company.startswith("※"):
            continue
        product = (row[pi_col] or "").strip()
        if not product or product in ("상품명", "보험상품명"):
            continue

        # 열 위치 결정 (16열 vs 12~14열)
        # 16열: col[1]이 빈 열 → 전체 +1 shift
        # 12~14열: 동일 레이아웃
        if ncols >= 16:
            # 16열: 회사[0] (빈)[1] 상품[2] 상태[3] 계약자[4]
            #   계약월[5] 만기월[6] 만기나이[7] 납완월[8] 납완나이[9]
            #   주기/기간[10] 횟수[11] 월보[12] 납입한[13] 납입할[14]
            start = _cell(row, 5)
            end_age = _cell(row, 7)
            end_month = _cell(row, 6)
            pay_info = _cell(row, 10)
            pay_count = _cell(row, 11)
            premium = _parse_int(row, 12)
            paid_amt = _parse_int(row, 13)
            topay_amt = _parse_int(row, 14)
        else:
            # 12~14열: 회사[0] 상품[1] 상태[2] 계약자[3]
            #   계약월[4] 만기월[5] 만기나이[6] 납완월[7] 납완나이[8]
            #   주기/기간[9] 횟수[10] 월보[11] 납입한[12] 납입할[13]
            start = _cell(row, 4)
            end_age = _cell(row, 6)
            end_month = _cell(row, 5)
            pay_info = _cell(row, 9)
            pay_count = _cell(row, 10)
            premium = _parse_int(row, 11)
            paid_amt = _parse_int(row, 12)
            topay_amt = _parse_int(row, 13)

        period = f"{end_age}만기" if end_age else end_month
        납입기간 = pay_info.split("/")[-1] if "/" in pay_info else pay_info
        납입개월 = 0
        총납입개월 = 0
        if "/" in pay_count:
            parts = pay_count.split("/")
            납입개월 = int(re.sub(r"[^\d]", "", parts[0]) or "0")
            총납입개월 = int(re.sub(r"[^\d]", "", parts[-1]) or "0")

        idx = len(all_contracts)
        col_ltr = COL_LTRS_EXT[idx] if idx < len(COL_LTRS_EXT) else "L"
        all_contracts.append({
            "_idx": idx, "열": col_ltr,
            "보험사": company, "상품명": product,
            "보장나이": period, "월보험료": premium,
            "가입시기": start, "_paid": paid_amt, "_topay": topay_amt,
            "_납입기간": 납입기간, "_납입개월": 납입개월, "_총납입개월": 총납입개월,
        })


def _parse_contract_table_vertical(tbl, all_contracts):
    """세로 포맷 계약 테이블 (6열, 2행 헤더, 계약당 2행)
    Row 0: [회사명, 계약상태, 계약월, 납입완료월(나이), 납입횟수, 납입한보험료]
    Row 1: [상품명, 계약자, 만기년월(나이), 납입주기/기간, 월보험료, 납입할보험료]
    Row 2~: 계약 데이터 (짝수=회사행, 홀수=상품행)
    """
    if len(tbl) < 4 or len(tbl[0]) < 5:
        return
    h0 = "".join((c or "") for c in tbl[0])
    h1 = "".join((c or "") for c in tbl[1])
    if "회사명" not in h0 and "보험회사" not in h0:
        return
    if "상품명" not in h1:
        return

    i = 2
    while i + 1 < len(tbl):
        row_a = tbl[i]
        row_b = tbl[i + 1]
        company = (row_a[0] or "").strip()
        if not company or company.startswith("※"):
            i += 1
            continue
        product = (row_b[0] or "").strip()
        if not product or product in ("상품명", "보험상품명"):
            i += 2
            continue

        start = _cell(row_a, 2)
        end_month_cell = _cell(row_b, 2)
        m = re.search(r"\((\d+세)\)", _cell(row_a, 3))
        end_age = m.group(1) if m else ""
        period = f"{end_age}만기" if end_age else end_month_cell

        pay_info = _cell(row_b, 3)
        pay_count = _cell(row_a, 4)
        premium = _parse_int(row_b, 4)
        paid_amt = _parse_int(row_a, 5)
        topay_amt = _parse_int(row_b, 5)

        납입기간 = pay_info.split("/")[-1] if "/" in pay_info else pay_info
        납입개월 = 0
        총납입개월 = 0
        if "/" in pay_count:
            parts = pay_count.split("/")
            납입개월 = int(re.sub(r"[^\d]", "", parts[0]) or "0")
            총납입개월 = int(re.sub(r"[^\d]", "", parts[-1]) or "0")

        idx = len(all_contracts)
        col_ltr = COL_LTRS_EXT[idx] if idx < len(COL_LTRS_EXT) else "L"
        all_contracts.append({
            "_idx": idx, "열": col_ltr,
            "보험사": company, "상품명": product,
            "보장나이": period, "월보험료": premium,
            "가입시기": start, "_paid": paid_amt, "_topay": topay_amt,
            "_납입기간": 납입기간, "_납입개월": 납입개월, "_총납입개월": 총납입개월,
        })
        i += 2


def _cell(row, idx):
    return (row[idx] or "").strip() if idx < len(row) else ""


def _parse_int(row, idx):
    if idx >= len(row):
        return 0
    return int(re.sub(r"[^\d]", "", row[idx] or "0") or "0")


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


def _parse_coverages(pdf, all_contracts: list) -> tuple[dict, dict]:
    """Page 6~8에서 보장금액 추출. (coverage_raw, seen_rows) 반환.
    seen_rows: {contract_idx: set(row_nums)} — Page 6에서 확인된 항목 (값 0 포함)
    """
    coverage_raw = {}
    seen_rows = {}  # Page 6에서 확인된 행 번호 (0이어도 기록)
    mapped_indices = set()
    total_pages = len(pdf.pages)

    # 보장금액 페이지: "상품별 보장금액" 테이블이 있는 페이지를 동적 탐색
    cov_pages = []
    for pg_idx in range(5, min(total_pages, 15)):
        text = pdf.pages[pg_idx].extract_text() or ""
        if "상품별 보장금액" in text or ("보장항목" in text and "진단" in text):
            cov_pages.append(pg_idx)
        elif cov_pages and "가입상품상세" in text:
            break  # 상세 페이지 시작되면 중단

    for pg_idx in (cov_pages or range(5, min(5 + 3, total_pages))):
        pg = pdf.pages[pg_idx]
        tables = pg.extract_tables()
        data_tbl = item_tbl = None
        # 세로 포맷 후보
        vert_item_tbl = vert_data_tbl = None
        for t in tables:
            if not t:
                continue
            r, c = len(t), len(t[0]) if t[0] else 0
            # 가로 포맷: item 7열 + data 9열
            if c == 9 and r >= 25:
                data_tbl = t
            elif c == 7 and r >= 20:
                item_tbl = t
            # 세로 포맷: item 4열 + data 4열 (둘 다 40행 이상)
            elif c == 4 and r >= 40:
                h = "".join((cell or "") for cell in t[0])
                if any(kw in h for kw in ("보장항목", "구분", "사망")):
                    vert_item_tbl = t
                else:
                    vert_data_tbl = t

        # 가로 포맷 처리
        if data_tbl and item_tbl:
            _parse_coverages_horizontal(
                data_tbl, item_tbl, all_contracts,
                coverage_raw, seen_rows, mapped_indices,
            )
            continue

        # 세로 포맷 처리
        if vert_item_tbl and vert_data_tbl:
            _parse_coverages_vertical(
                vert_item_tbl, vert_data_tbl, all_contracts,
                coverage_raw, seen_rows, mapped_indices,
            )

    return coverage_raw, seen_rows


def _parse_coverages_horizontal(data_tbl, item_tbl, all_contracts,
                                coverage_raw, seen_rows, mapped_indices):
    """가로 포맷: item 7열 + data 9열 (좌/우 쌍 배치)"""
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
            if ci not in seen_rows:
                seen_rows[ci] = set()
            li = pos * 2
            ri = pos * 2 + 1
            lv = parse_amount(dr[li] if li < len(dr) else "0")
            if left_name:
                rn = find_row_for_item(left_name)
                if rn:
                    seen_rows[ci].add(rn)
                    if lv:
                        coverage_raw[ci][str(rn)] = lv
            rv = parse_amount(dr[ri] if ri < len(dr) else "0")
            if not rv and pos == max(page_pos_map.keys()) and ri + 1 < len(dr):
                rv = parse_amount(dr[ri + 1] if ri + 1 < len(dr) else "0")
            if right_name:
                rn = find_row_for_item(right_name)
                if rn:
                    seen_rows[ci].add(rn)
                    if rv:
                        coverage_raw[ci][str(rn)] = rv


def _parse_coverages_vertical(item_tbl, data_tbl, all_contracts,
                              coverage_raw, seen_rows, mapped_indices):
    """세로 포맷: item 4열 + data 4열 (항목이 행별로 나열)
    item_tbl: [구분, 보장항목, 내보장금액, 진단결과] x 46행
    data_tbl: [상품1, 상품2, 상품3, 상품4] x 49행
      Row 0: 보험사명, Row 1: 상품명, Row 2: 보장기간, Row 3: 보험료
      Row 4~: 보장금액 (item_tbl row 1~ 에 대응)
    """
    ncols = len(data_tbl[0]) if data_tbl[0] else 0
    page_pos_map = {}
    for pos in range(ncols):
        comp = (data_tbl[0][pos] or "").strip().replace("\n", "").replace(" ", "")
        prod = (data_tbl[1][pos] or "").strip().replace("\n", "").replace(" ", "")[:15]
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

    if not page_pos_map:
        return

    for item_idx in range(1, len(item_tbl)):
        item_name = (item_tbl[item_idx][1] or "").strip() if len(item_tbl[item_idx]) > 1 else ""
        if not item_name:
            continue
        row_num = find_row_for_item(item_name)
        if row_num is None:
            continue

        data_row_idx = item_idx + 3
        if data_row_idx >= len(data_tbl):
            break
        dr = data_tbl[data_row_idx]

        for pos, ci in page_pos_map.items():
            if ci not in coverage_raw:
                coverage_raw[ci] = {}
            if ci not in seen_rows:
                seen_rows[ci] = set()
            seen_rows[ci].add(row_num)
            val = parse_amount(dr[pos] if pos < len(dr) else "0")
            if val:
                coverage_raw[ci][str(row_num)] = val
