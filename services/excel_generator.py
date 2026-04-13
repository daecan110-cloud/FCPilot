"""보장분석 엑셀 생성기 — 6/12상품 자동 선택 (2026-04)"""
import io
import os
import shutil
import tempfile
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from services.item_map import (
    COL_IDX, COL_LTRS, COL_IDX_12, COL_LTRS_12, DATA_ROWS,
)

_TMPL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
TEMPLATE_6 = os.path.join(_TMPL_DIR, "master_template.xlsx")
TEMPLATE_12 = os.path.join(_TMPL_DIR, "master_template_12.xlsx")


def safe_val(ws, row, col, value):
    cell = ws.cell(row=row, column=col)
    if cell.__class__.__name__ != "MergedCell":
        cell.value = value


def generate_analysis_excel(data: dict, **_kw) -> list[tuple[str, bytes]]:
    all_contracts = data.get("_all_contracts", data.get("계약", []))
    coverage_raw = data.get("_coverage_raw", {})
    customer = data.get("고객명", "고객")

    # 6개 이하 → 6상품 양식, 7~12개 → 12상품 양식
    use_12 = len(all_contracts) > 6
    cfg = _cfg_12() if use_12 else _cfg_6()
    contracts = all_contracts[:cfg["max"]]

    sd = _make_slice(data, contracts, coverage_raw, cfg)
    b = _fill_workbook(sd, cfg)
    return [(f"{customer}_보장분석표.xlsx", b)]


def _cfg_6():
    return {
        "template": TEMPLATE_6, "max": 6,
        "col_idx": COL_IDX, "col_ltrs": COL_LTRS,
        "data_end": 8, "sum_col": 9, "max_col": 9,
        "review_start": 80, "review_count": 6,
    }


def _cfg_12():
    return {
        "template": TEMPLATE_12, "max": 12,
        "col_idx": COL_IDX_12, "col_ltrs": COL_LTRS_12,
        "data_end": 14, "sum_col": 15, "max_col": 15,
        "review_start": 80, "review_count": 12,
    }


def _make_slice(base, contracts, coverage_raw, cfg):
    col_ltrs = cfg["col_ltrs"]
    data = {
        "고객명": base["고객명"], "성별": base["성별"], "나이": base["나이"],
        "계약": [], "보장금액": {},
    }
    for new_i, c in enumerate(contracts):
        col = col_ltrs[new_i]
        nc = {k: v for k, v in c.items() if not k.startswith("_")}
        nc["열"] = col
        nc["_납입기간"] = c.get("_납입기간", "")
        nc["_납입개월"] = c.get("_납입개월", 0)
        nc["_총납입개월"] = c.get("_총납입개월", 0)
        data["계약"].append(nc)
        if c["_idx"] in coverage_raw:
            data["보장금액"][col] = coverage_raw[c["_idx"]]
    return data


def _fill_workbook(slice_data, cfg):
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy(cfg["template"], tmp.name)
    wb = load_workbook(tmp.name)
    ws = wb.active

    contracts = slice_data.get("계약", [])
    _clear_values(ws, cfg)
    _fill_header(ws, slice_data, cfg)
    _fill_coverage(ws, slice_data, cfg)
    _fill_sums(ws, contracts, cfg)
    _fill_review(ws, contracts, cfg)
    _final_format(ws, cfg)

    buf = io.BytesIO()
    wb.save(buf)
    os.unlink(tmp.name)
    return buf.getvalue()


def _clear_values(ws, cfg):
    mc = cfg["max_col"]
    de = cfg["data_end"]
    sc = cfg["sum_col"]
    rs = cfg["review_start"]
    rc = cfg["review_count"]
    ranges = [
        (1, 1, 1, mc),
        (3, 3, 7, de),
        (9, 3, 74, de),
        (9, sc, 74, sc),
        (77, 3, 77, mc),
        (rs, 1, rs + rc - 1, mc),
    ]
    for r_s, c_s, r_e, c_e in ranges:
        for r in range(r_s, r_e + 1):
            for c in range(c_s, c_e + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.value = None


def _fill_header(ws, slice_data, cfg):
    customer = slice_data.get("고객명", "고객")
    gender = slice_data.get("성별", "남")
    age = slice_data.get("나이", 0)
    gender_full = "남자" if gender == "남" else "여자"
    safe_val(ws, 1, 1, f"{customer}님 ({gender_full}, {age}세) · 보장 분석표")

    col_idx = cfg["col_idx"]
    for c in slice_data.get("계약", []):
        col = col_idx.get(c["열"], 3)
        safe_val(ws, 3, col, f"{c.get('상품명', '')}\n({c.get('보험사', '')})")
        safe_val(ws, 4, col, c.get("가입시기", ""))
        safe_val(ws, 5, col, c.get("_납입기간", "") or c.get("보장나이", ""))
        paid_m = c.get("_납입개월", 0)
        total_m = c.get("_총납입개월", 0)
        coverage_period = c.get("보장나이", "")
        if total_m and coverage_period:
            safe_val(ws, 6, col, f"{paid_m}/{total_m}\n({coverage_period})")
        elif total_m:
            safe_val(ws, 6, col, f"{paid_m}/{total_m}")
        elif coverage_period:
            safe_val(ws, 6, col, coverage_period)
        safe_val(ws, 7, col, c.get("월보험료", 0))


def _fill_coverage(ws, slice_data, cfg):
    col_idx = cfg["col_idx"]
    for col_ltr, row_data in slice_data.get("보장금액", {}).items():
        col = col_idx.get(col_ltr)
        if not col:
            continue
        for row_str, amount in row_data.items():
            row_num = int(row_str)
            if row_num in DATA_ROWS:
                safe_val(ws, row_num, col, amount if amount else None)


def _fill_sums(ws, contracts, cfg):
    sc = cfg["sum_col"]
    col_start, col_end = 3, cfg["data_end"] + 1  # C ~ last data col

    for row_num in DATA_ROWS:
        total = 0
        for c in range(col_start, col_end):
            cell = ws.cell(row=row_num, column=c)
            if cell.__class__.__name__ != "MergedCell":
                if isinstance(cell.value, (int, float)):
                    total += cell.value
        safe_val(ws, row_num, sc, total if total > 0 else None)

    # Row 7 월보험료 합계
    prem_total = 0
    for c in range(col_start, col_end):
        cell = ws.cell(row=7, column=c)
        if cell.__class__.__name__ != "MergedCell":
            if isinstance(cell.value, (int, float)):
                prem_total += cell.value
    safe_val(ws, 7, sc, prem_total if prem_total > 0 else None)

    # Row 77 총납입 = 월보험료 × 총납입개월
    col_idx = cfg["col_idx"]
    total_paid = 0
    for ct in contracts:
        col = col_idx.get(ct["열"], 3)
        prem = ct.get("월보험료", 0)
        months = ct.get("_총납입개월", 0)
        if prem and months:
            val = int(prem * months)
            safe_val(ws, 77, col, val)
            total_paid += val
    safe_val(ws, 77, sc, total_paid if total_paid > 0 else None)


def _short_name(contract):
    name = contract.get("상품명", "")
    company = contract.get("보험사", "")
    for prefix in ["무배당 ", "(무배당)", "무배당", "無", "삼성 "]:
        name = name.replace(prefix, "")
    name = name.replace("()", "").strip()
    if "\n" in name:
        name = name.split("\n")[0]
    for full, short in [("삼성생명보험", "삼성생명"), ("한화생명보험", "한화생명"),
                        ("새마을금고중앙회", "새마을금고"), ("현대해상화재보험", "현대해상")]:
        company = company.replace(full, short)
    return f"{name}\n({company})"


def _fill_review(ws, contracts, cfg):
    rs = cfg["review_start"]
    for i, c in enumerate(contracts):
        r = rs + i
        safe_val(ws, r, 1, _short_name(c))
        safe_val(ws, r, 3, _build_review(c))


def _build_review(contract):
    combined = contract.get("상품명", "") + contract.get("보험사", "")
    period = contract.get("보장나이", "")
    premium = contract.get("월보험료", 0)
    checks = []
    if any(k in combined for k in ["단체", "단기"]):
        checks.append("단체/단기계약 — 퇴직·탈퇴 시 자동 소멸")
    elif any(k in combined for k in ["실손", "의료비"]):
        checks.append("실손의료비 보험 (갱신형)")
    elif any(k in combined for k in ["종신"]) and any(k in combined for k in ["변액", "유니버셜"]):
        checks.append("변액유니버셜종신 — 수익률·적립금 확인 필요")
    elif any(k in combined for k in ["종신"]):
        checks.append("종신보험 — 비갱신형")
    elif any(k in combined for k in ["운전자", "자동차"]):
        checks.append("운전자보험 — 교통상해/벌금/변호사비 보장")
    elif any(k in combined for k in ["CI"]):
        checks.append("CI보험 — 중대질병 진단 시 보험금 지급")
    elif any(k in combined for k in ["건강", "상해", "종합"]):
        checks.append(f"건강/상해 보장 ({period})")
    else:
        checks.append(f"보장기간: {period}")
    if premium == 0:
        checks.append("납입완료")
    return " / ".join(checks)


def _final_format(ws, cfg):
    mc = cfg["max_col"]
    de = cfg["data_end"]
    rs = cfg["review_start"]
    rc = cfg["review_count"]
    for r in range(1, ws.max_row + 1):
        for c in range(1, mc + 1):
            cell = ws.cell(row=r, column=c)
            if cell.__class__.__name__ == "MergedCell":
                continue
            old = cell.font
            cell.font = Font(
                name="Malgun Gothic",
                size=old.size if old.size else 9,
                bold=old.bold if old.bold else False,
                italic=old.italic if old.italic else False,
                color=old.color,
            )
        if r in (3, 6):
            for c in range(3, de + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    old_al = cell.alignment
                    cell.alignment = Alignment(
                        horizontal=old_al.horizontal or "center",
                        vertical=old_al.vertical or "center",
                        wrap_text=True,
                    )
    # 주계약 리뷰 영역 — 행간격 및 줄바꿈 정렬
    for r in range(rs, rs + rc):
        ws.row_dimensions[r].height = 33
        for c in range(1, mc + 1):
            cell = ws.cell(row=r, column=c)
            if cell.__class__.__name__ != "MergedCell":
                cell.alignment = Alignment(
                    horizontal="left" if c <= 2 else "left",
                    vertical="center",
                    wrap_text=True,
                )
