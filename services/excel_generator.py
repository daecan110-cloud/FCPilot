"""보장분석 엑셀 생성기 — 신규 양식 (2026-04)"""
import io
import os
import math
import shutil
import tempfile
from copy import copy
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from services.item_map import COL_IDX, COL_LTRS, DATA_ROWS

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "templates", "master_template.xlsx"
)
MAX_PRODUCTS = 6  # C~H


def safe_val(ws, row, col, value):
    """값만 설정. 서식은 절대 건드리지 않음."""
    cell = ws.cell(row=row, column=col)
    if cell.__class__.__name__ != "MergedCell":
        cell.value = value


def generate_analysis_excel(data: dict, **_kw) -> list[tuple[str, bytes]]:
    all_contracts = data.get("_all_contracts", data.get("계약", []))
    coverage_raw = data.get("_coverage_raw", {})
    customer = data.get("고객명", "고객")

    if len(all_contracts) <= MAX_PRODUCTS:
        sd = _make_slice(data, all_contracts, coverage_raw)
        b = _fill_workbook(sd, data)
        return [(f"{customer}_보장분석표.xlsx", b)]

    results = []
    num_files = math.ceil(len(all_contracts) / MAX_PRODUCTS)
    for i in range(num_files):
        chunk = all_contracts[i * MAX_PRODUCTS:(i + 1) * MAX_PRODUCTS]
        sd = _make_slice(data, chunk, coverage_raw)
        b = _fill_workbook(sd, data)
        results.append((f"{customer}_보장분석표_{i + 1}.xlsx", b))
    return results


def _make_slice(base, contracts, coverage_raw):
    data = {
        "고객명": base["고객명"], "성별": base["성별"], "나이": base["나이"],
        "계약": [], "보장금액": {},
    }
    for new_i, c in enumerate(contracts):
        col = COL_LTRS[new_i]
        nc = {k: v for k, v in c.items() if not k.startswith("_")}
        nc["열"] = col
        nc["_납입기간"] = c.get("_납입기간", "")
        nc["_납입개월"] = c.get("_납입개월", 0)
        nc["_총납입개월"] = c.get("_총납입개월", 0)
        data["계약"].append(nc)
        if c["_idx"] in coverage_raw:
            data["보장금액"][col] = coverage_raw[c["_idx"]]
    return data


def _fill_workbook(slice_data, full_data):
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy(TEMPLATE_PATH, tmp.name)
    wb = load_workbook(tmp.name)
    ws = wb.active

    _clear_values(ws)
    _fill_header(ws, slice_data)
    _fill_coverage(ws, slice_data)
    _fill_sums(ws, slice_data.get("계약", []))
    _fill_review(ws, slice_data.get("계약", []))
    _final_format(ws)

    buf = io.BytesIO()
    wb.save(buf)
    os.unlink(tmp.name)
    return buf.getvalue()


def _clear_values(ws):
    """데이터 영역만 클리어 (서식 보존)"""
    ranges = [
        (1, 1, 1, 9),       # 제목
        (3, 3, 7, 8),       # 상품정보 C~H
        (9, 3, 74, 8),      # 보장금액 C~H (섹션헤더 포함)
        (9, 9, 74, 9),      # 합계 I열
        (77, 3, 77, 9),     # 총납입 합계
        (80, 1, 85, 9),     # 리뷰
    ]
    for r_s, c_s, r_e, c_e in ranges:
        for r in range(r_s, r_e + 1):
            for c in range(c_s, c_e + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.value = None


def _fill_header(ws, slice_data):
    """Row 1~7: 고객 정보 + 상품 헤더"""
    customer = slice_data.get("고객명", "고객")
    gender = slice_data.get("성별", "남")
    age = slice_data.get("나이", 0)
    gender_full = "남자" if gender == "남" else "여자"
    safe_val(ws, 1, 1, f"{customer}님 ({gender_full}, {age}세) · 보장 분석표")

    for c in slice_data.get("계약", [])[:MAX_PRODUCTS]:
        col = COL_IDX.get(c["열"], 3)
        safe_val(ws, 3, col, f"{c.get('상품명', '')}\n({c.get('보험사', '')})")
        safe_val(ws, 4, col, c.get("가입시기", ""))
        safe_val(ws, 5, col, c.get("_납입기간", "") or c.get("보장나이", ""))
        paid_m = c.get("_납입개월", 0)
        total_m = c.get("_총납입개월", 0)
        if total_m:
            safe_val(ws, 6, col, f"{paid_m}/{total_m}")
        else:
            safe_val(ws, 6, col, None)
        safe_val(ws, 7, col, c.get("월보험료", 0))


def _fill_coverage(ws, slice_data):
    """Row 9~74: 보장금액 채우기"""
    for col_ltr, row_data in slice_data.get("보장금액", {}).items():
        col = COL_IDX.get(col_ltr)
        if not col:
            continue
        for row_str, amount in row_data.items():
            row_num = int(row_str)
            if row_num in DATA_ROWS:
                safe_val(ws, row_num, col, amount if amount else None)


def _fill_sums(ws, contracts):
    """I열(col 9) 합계 + Row 77 총납입"""
    for row_num in DATA_ROWS:
        total = 0
        for c in range(3, 9):  # C(3) ~ H(8)
            cell = ws.cell(row=row_num, column=c)
            if cell.__class__.__name__ != "MergedCell":
                if isinstance(cell.value, (int, float)):
                    total += cell.value
        safe_val(ws, row_num, 9, total if total > 0 else None)

    # Row 7: 월보험료 합계
    prem_total = 0
    for c in range(3, 9):
        cell = ws.cell(row=7, column=c)
        if cell.__class__.__name__ != "MergedCell":
            if isinstance(cell.value, (int, float)):
                prem_total += cell.value
    safe_val(ws, 7, 9, prem_total if prem_total > 0 else None)

    # Row 77: 총납입 보험료 = 월보험료 × 총납입개월 (계약 데이터에서 직접)
    total_paid = 0
    for ct in contracts[:MAX_PRODUCTS]:
        col = COL_IDX.get(ct["열"], 3)
        prem = ct.get("월보험료", 0)
        months = ct.get("_총납입개월", 0)
        if prem and months:
            val = int(prem * months)
            safe_val(ws, 77, col, val)
            total_paid += val
    safe_val(ws, 77, 9, total_paid if total_paid > 0 else None)


def _short_name(contract):
    """상품명을 짧게 축약"""
    name = contract.get("상품명", "")
    company = contract.get("보험사", "")
    # 불필요한 접두사 제거
    for prefix in ["무배당 ", "(무배당)", "무배당", "無", "삼성 "]:
        name = name.replace(prefix, "")
    # 빈 괄호 정리
    name = name.replace("()", "").strip()
    # 줄바꿈 이후 부분 제거 (부제목)
    if "\n" in name:
        name = name.split("\n")[0]
    # 보험사명 축약
    for full, short in [("삼성생명보험", "삼성생명"), ("한화생명보험", "한화생명"),
                        ("새마을금고중앙회", "새마을금고"), ("현대해상화재보험", "현대해상")]:
        company = company.replace(full, short)
    return f"{name}\n({company})"


def _fill_review(ws, contracts):
    """Row 80~85: 주계약 리뷰"""
    for i, c in enumerate(contracts[:MAX_PRODUCTS]):
        r = 80 + i
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
        checks.append(f"변액유니버셜종신 — 수익률·적립금 확인 필요")
    elif any(k in combined for k in ["종신"]):
        checks.append("종신보험 — 비갱신형")
    elif any(k in combined for k in ["운전자", "자동차"]):
        checks.append("운전자보험 — 교통상해/벌금/변호사비 보장")
    elif any(k in combined for k in ["CI"]):
        checks.append(f"CI보험 — 중대질병 진단 시 보험금 지급")
    elif any(k in combined for k in ["건강", "상해", "종합"]):
        checks.append(f"건강/상해 보장 ({period})")
    else:
        checks.append(f"보장기간: {period}")
    if premium == 0:
        checks.append("납입완료")
    return " / ".join(checks)


def _final_format(ws):
    """전체 셀: Malgun Gothic 강제. Row 3 wrap_text."""
    for r in range(1, ws.max_row + 1):
        for c in range(1, 10):  # A~I
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
        if r == 3:
            for c in range(3, 9):  # C~H
                cell = ws.cell(row=3, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    old_al = cell.alignment
                    cell.alignment = Alignment(
                        horizontal=old_al.horizontal or "center",
                        vertical=old_al.vertical or "center",
                        wrap_text=True,
                    )
