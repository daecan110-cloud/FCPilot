"""보장분석 엑셀 생성기 — v10 양식 7상품 (2026-04)"""
import io
import os
import shutil
import tempfile
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from services.item_map import COL_IDX, COL_LTRS, SUM_COL, DATA_ROWS

_TMPL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
TEMPLATE = os.path.join(_TMPL_DIR, "master_template.xlsx")

_FONT_NAME = "KoPubWorld돋움체 Bold"


def safe_val(ws, row, col, value):
    cell = ws.cell(row=row, column=col)
    if cell.__class__.__name__ != "MergedCell":
        cell.value = value


def generate_analysis_excel(data: dict, **_kw) -> list[tuple[str, bytes]]:
    all_contracts = data.get("_all_contracts", data.get("계약", []))
    coverage_raw = data.get("_coverage_raw", {})
    customer = data.get("고객명", "고객")

    contracts = all_contracts[:7]
    sd = _make_slice(data, contracts, coverage_raw)
    b = _fill_workbook(sd)
    return [(f"{customer}_보장분석표.xlsx", b)]


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


def _fill_workbook(slice_data):
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy(TEMPLATE, tmp.name)
    wb = load_workbook(tmp.name)
    ws = wb.active

    contracts = slice_data.get("계약", [])
    _clear_values(ws)
    _fill_header(ws, slice_data)
    _fill_coverage(ws, slice_data)
    _fill_sums(ws, contracts)
    _fill_review(ws, contracts)
    _final_format(ws)

    buf = io.BytesIO()
    wb.save(buf)
    os.unlink(tmp.name)
    return buf.getvalue()


# v10: D~J(col 4~10), K=합계(col 11)
_DATA_START = 4   # D
_DATA_END = 10    # J
_MAX_COL = 11     # K
_REVIEW_START = 85
_REVIEW_COUNT = 7


def _clear_values(ws):
    ranges = [
        (1, 1, 1, _MAX_COL),           # 제목
        (3, _DATA_START, 7, _DATA_END), # 상품정보 (Row 3~7, D~J)
        (9, _DATA_START, 74, _DATA_END),# 보장금액
        (9, SUM_COL, 74, SUM_COL),      # K열 합계
        (75, _DATA_START, 77, _MAX_COL),# 보험료
        (_REVIEW_START, 1, _REVIEW_START + _REVIEW_COUNT - 1, _MAX_COL),
    ]
    for r_s, c_s, r_e, c_e in ranges:
        for r in range(r_s, r_e + 1):
            for c in range(c_s, c_e + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.value = None


def _fill_header(ws, slice_data):
    customer = slice_data.get("고객명", "고객")
    gender = slice_data.get("성별", "남")
    age = slice_data.get("나이", 0)
    gender_full = "남자" if gender == "남" else "여자"
    safe_val(ws, 1, 1, f"{customer}님 ({gender_full}, {age}세) · 보장 분석표")

    for c in slice_data.get("계약", []):
        col = COL_IDX.get(c["열"], 4)
        # Row 2: 가입회사 (C열 헤더에 이미 있으므로 D~J에 회사명)
        safe_val(ws, 2, col, c.get("보험사", ""))
        # Row 3: 상품명
        safe_val(ws, 3, col, c.get("상품명", ""))
        # Row 4: 가입년,월
        safe_val(ws, 4, col, c.get("가입시기", ""))
        # Row 5: 납입기간 (보장기간)
        납입기간 = c.get("_납입기간", "")
        coverage_period = c.get("보장나이", "")
        if 납입기간 and coverage_period:
            safe_val(ws, 5, col, f"{납입기간}\n({coverage_period})")
        elif 납입기간:
            safe_val(ws, 5, col, 납입기간)
        else:
            safe_val(ws, 5, col, coverage_period or None)
        # Row 6: 총납입개월 (남은 개월)
        paid_m = c.get("_납입개월", 0)
        total_m = c.get("_총납입개월", 0)
        safe_val(ws, 6, col, f"{paid_m}/{total_m}" if total_m else None)
        # Row 7: 월보험료
        safe_val(ws, 7, col, c.get("월보험료", 0))


def _fill_coverage(ws, slice_data):
    for col_ltr, row_data in slice_data.get("보장금액", {}).items():
        col = COL_IDX.get(col_ltr)
        if not col:
            continue
        for row_str, amount in row_data.items():
            row_num = int(row_str)
            if row_num in DATA_ROWS:
                safe_val(ws, row_num, col, amount if amount else None)


def _fill_sums(ws, contracts):
    from openpyxl.utils import get_column_letter
    start_ltr = get_column_letter(_DATA_START)   # D
    end_ltr = get_column_letter(_DATA_END)        # J

    # 데이터 행 합계
    for row_num in DATA_ROWS:
        safe_val(ws, row_num, SUM_COL, f"=SUM({start_ltr}{row_num}:{end_ltr}{row_num})")

    # Row 7 월보험료 합계
    safe_val(ws, 7, SUM_COL, f"=SUM({start_ltr}7:{end_ltr}7)")

    # Row 75 기납입보험료 = 월보험료 × 납입개월
    for ct in contracts:
        col = COL_IDX.get(ct["열"], 4)
        prem = ct.get("월보험료", 0)
        paid_m = ct.get("_납입개월", 0)
        if prem and paid_m:
            safe_val(ws, 75, col, int(prem * paid_m))
    safe_val(ws, 75, SUM_COL, f"=SUM({start_ltr}75:{end_ltr}75)")

    # Row 76 납입할보험료 = 월보험료 × 남은개월
    for ct in contracts:
        col = COL_IDX.get(ct["열"], 4)
        prem = ct.get("월보험료", 0)
        total_m = ct.get("_총납입개월", 0)
        paid_m = ct.get("_납입개월", 0)
        remain = total_m - paid_m
        if prem and remain > 0:
            safe_val(ws, 76, col, int(prem * remain))
    safe_val(ws, 76, SUM_COL, f"=SUM({start_ltr}76:{end_ltr}76)")

    # Row 77 총납입보험료 = 기납입 + 납입할
    for c_ltr in COL_LTRS:
        col = COL_IDX[c_ltr]
        col_l = get_column_letter(col)
        safe_val(ws, 77, col, f"={col_l}75+{col_l}76")
    safe_val(ws, 77, SUM_COL, f"=SUM({start_ltr}77:{end_ltr}77)")


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
    return f"{company}\n{name}"


def _fill_review(ws, contracts):
    for i, c in enumerate(contracts):
        r = _REVIEW_START + i
        # A:B 보험사/상품명
        safe_val(ws, r, 1, _short_name(c))
        # C 가입일/만기
        period = c.get("보장나이", "")
        start = c.get("가입시기", "")
        safe_val(ws, r, 3, f"{start}\n({period})" if start else period)
        # D 월보험료
        prem = c.get("월보험료", 0)
        safe_val(ws, r, 4, f"{prem:,.0f}원" if prem else "납입완료")
        # E:H 주요 체크사항
        safe_val(ws, r, 5, _build_review(c))


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


def _final_format(ws):
    for r in range(1, ws.max_row + 1):
        for c in range(1, _MAX_COL + 1):
            cell = ws.cell(row=r, column=c)
            if cell.__class__.__name__ == "MergedCell":
                continue
            old = cell.font
            cell.font = Font(
                name=_FONT_NAME,
                size=old.size if old.size else 9,
                bold=True,
                italic=old.italic if old.italic else False,
                color=old.color,
            )
        # Row 3, 5: 상품명/납입기간 — 가운데 정렬 + 줄바꿈
        if r in (3, 5):
            for c in range(_DATA_START, _DATA_END + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.alignment = Alignment(
                        horizontal="center", vertical="center", wrap_text=True,
                    )
    # 리뷰 행 서식
    for r in range(_REVIEW_START, _REVIEW_START + _REVIEW_COUNT):
        for c in range(1, _MAX_COL + 1):
            cell = ws.cell(row=r, column=c)
            if cell.__class__.__name__ != "MergedCell":
                cell.alignment = Alignment(
                    horizontal="left", vertical="center", wrap_text=True,
                )
