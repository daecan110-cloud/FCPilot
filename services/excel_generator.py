"""보장분석 엑셀 생성기 — v10 양식 7상품 (2026-04)"""
import io
import os
import shutil
import tempfile
from openpyxl import load_workbook
from copy import copy
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from services.item_map import COL_IDX, COL_LTRS, SUM_COL, PROP_COL, TOTAL_COL, DATA_ROWS

_TMPL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
TEMPLATE = os.path.join(_TMPL_DIR, "master_template.xlsx")

_FONT_NAME = "KoPubWorld돋움체 Bold"


def safe_val(ws, row, col, value):
    cell = ws.cell(row=row, column=col)
    if cell.__class__.__name__ != "MergedCell":
        cell.value = value


def generate_analysis_excel(data: dict, proposal: dict | None = None, **_kw) -> list[tuple[str, bytes]]:
    all_contracts = data.get("_all_contracts", data.get("계약", []))
    coverage_raw = data.get("_coverage_raw", {})
    customer = data.get("고객명", "고객")

    contracts = all_contracts[:7]
    sd = _make_slice(data, contracts, coverage_raw)
    b = _fill_workbook(sd, proposal=proposal)
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
        nc["_paid"] = c.get("_paid", 0)
        nc["_topay"] = c.get("_topay", 0)
        data["계약"].append(nc)
        if c["_idx"] in coverage_raw:
            data["보장금액"][col] = coverage_raw[c["_idx"]]
    return data


def _fill_workbook(slice_data, proposal=None):
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy(TEMPLATE, tmp.name)
    wb = load_workbook(tmp.name)
    ws = wb.active

    has_proposal = proposal and proposal.get("특약목록")
    contracts = slice_data.get("계약", [])
    _clear_values(ws, has_proposal=has_proposal)
    _fill_header(ws, slice_data)
    _fill_coverage(ws, slice_data)
    if has_proposal:
        _fill_proposal(ws, proposal)
        _format_proposal_cols(ws)
    _fill_sums(ws, contracts, has_proposal=has_proposal, proposal=proposal)
    _fill_renewal(ws, contracts)
    _fill_review(ws, contracts)
    _final_format(ws, has_proposal=has_proposal)

    buf = io.BytesIO()
    wb.save(buf)
    os.unlink(tmp.name)
    return buf.getvalue()


# v10: D~J(col 4~10), K=합계(col 11), L=제안(col 12), M=전체합계(col 13)
_DATA_START = 4   # D
_DATA_END = 10    # J
_MAX_COL = 11     # K (제안 없을 때)
_MAX_COL_PROP = 13  # M (제안 있을 때)
_REVIEW_START = 90   # was 85 (+5)
_REVIEW_COUNT = 7


def _clear_values(ws, has_proposal=False):
    max_c = _MAX_COL_PROP if has_proposal else _MAX_COL
    ranges = [
        (1, 1, 1, max_c),              # 제목
        (3, _DATA_START, 7, _DATA_END), # 상품정보 (Row 3~7, D~J)
        (9, _DATA_START, 74, _DATA_END),# 보장금액
        (9, SUM_COL, 74, SUM_COL),      # K열 합계
        (80, _DATA_START, 82, max_c),   # 보험료
        (_REVIEW_START, 1, _REVIEW_START + _REVIEW_COUNT - 1, max_c),
    ]
    if has_proposal:
        ranges.append((2, PROP_COL, 7, PROP_COL))      # L열 헤더
        ranges.append((9, PROP_COL, 74, PROP_COL))      # L열 보장
        ranges.append((2, TOTAL_COL, 7, TOTAL_COL))     # M열 헤더
        ranges.append((9, TOTAL_COL, 74, TOTAL_COL))    # M열 합계

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
        if total_m:
            remain = total_m - paid_m
            safe_val(ws, 6, col, f"{paid_m}/{total_m}\n(남은 {remain}개월)")
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


def _fill_proposal(ws, proposal):
    """L열(col 12)에 신상품 제안 데이터 채우기"""
    from services.proposal_parser import map_riders_to_rows

    riders = proposal.get("특약목록", [])
    주계약 = riders[0] if riders else {}

    # Row 2: 헤더 (병합 전 값)
    safe_val(ws, 2, PROP_COL, "신상품 제안")
    # Row 3: 상품명 (L3:L4 병합 예정)
    safe_val(ws, 3, PROP_COL, proposal.get("상품명", "제안 상품"))
    # Row 5: 납입기간 (보장기간) (L5:L6 병합 예정)
    납입 = 주계약.get("납입기간", "")
    보장 = 주계약.get("보험기간", "")
    if 납입 and 보장:
        safe_val(ws, 5, PROP_COL, f"{납입}\n({보장})")
    elif 납입:
        safe_val(ws, 5, PROP_COL, 납입)
    else:
        safe_val(ws, 5, PROP_COL, 보장)
    # Row 7: 월보험료
    total_prem = proposal.get("보험료합계", 0)
    if total_prem:
        safe_val(ws, 7, PROP_COL, total_prem)

    # 보장금액 매핑
    row_amounts = map_riders_to_rows(riders)
    for row_num, amount in row_amounts.items():
        if row_num in DATA_ROWS:
            safe_val(ws, row_num, PROP_COL, amount)


def _format_proposal_cols(ws):
    """K열 서식을 L, M열에 복사 + 셀 병합"""
    from openpyxl.utils import get_column_letter

    l_ltr = get_column_letter(PROP_COL)    # L
    m_ltr = get_column_letter(TOTAL_COL)   # M

    # 열 너비 설정
    ws.column_dimensions[l_ltr].width = 18
    ws.column_dimensions[m_ltr].width = 18

    # K열 서식을 L, M 열에 복사 (Row 1 ~ 86)
    for r in range(1, 87):
        src = ws.cell(row=r, column=SUM_COL)
        if src.__class__.__name__ == "MergedCell":
            continue
        for col in (PROP_COL, TOTAL_COL):
            dst = ws.cell(row=r, column=col)
            if dst.__class__.__name__ == "MergedCell":
                continue
            dst.font = copy(src.font)
            dst.border = copy(src.border)
            dst.fill = copy(src.fill)
            dst.number_format = src.number_format
            dst.alignment = copy(src.alignment)

    # 병합 전에 Row 2~6 서식을 먼저 적용
    src2 = ws.cell(row=2, column=SUM_COL)
    _thin = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    _hdr_style = {
        "font": Font(name=_FONT_NAME, size=9, bold=True),
        "fill": copy(src2.fill),
        "border": _thin,
        "number_format": "#,##0",
        "alignment": Alignment(horizontal="center", vertical="center", wrap_text=True),
    }
    for r in range(2, 7):
        for col in (PROP_COL, TOTAL_COL):
            cell = ws.cell(row=r, column=col)
            if cell.__class__.__name__ != "MergedCell":
                for attr, val in _hdr_style.items():
                    setattr(cell, attr, copy(val) if attr != "number_format" else val)

    # ── 셀 병합 ──
    # L3:L4 — 상품명
    ws.merge_cells(f"{l_ltr}3:{l_ltr}4")
    # L5:L6 — 납입기간(보장기간)
    ws.merge_cells(f"{l_ltr}5:{l_ltr}6")
    # M2:M6 — "전체합계"
    ws.merge_cells(f"{m_ltr}2:{m_ltr}6")


def _fill_sums(ws, contracts, has_proposal=False, proposal=None):
    from openpyxl.utils import get_column_letter
    start_ltr = get_column_letter(_DATA_START)   # D
    end_ltr = get_column_letter(_DATA_END)        # J
    k_ltr = get_column_letter(SUM_COL)            # K
    l_ltr = get_column_letter(PROP_COL)           # L

    # 데이터 행 합계 (K열)
    for row_num in DATA_ROWS:
        safe_val(ws, row_num, SUM_COL, f"=SUM({start_ltr}{row_num}:{end_ltr}{row_num})")

    # Row 7 월보험료 합계 (K열)
    safe_val(ws, 7, SUM_COL, f"=SUM({start_ltr}7:{end_ltr}7)")

    # 전체합계 M열 (K + L)
    if has_proposal:
        safe_val(ws, 2, TOTAL_COL, "전체합계")
        for row_num in DATA_ROWS:
            safe_val(ws, row_num, TOTAL_COL, f"={k_ltr}{row_num}+{l_ltr}{row_num}")
        safe_val(ws, 7, TOTAL_COL, f"={k_ltr}7+{l_ltr}7")

    # Row 80 기납입보험료 (was 75)
    for ct in contracts:
        col = COL_IDX.get(ct["열"], 4)
        paid_amt = ct.get("_paid", 0)
        if not paid_amt:
            prem = ct.get("월보험료", 0)
            paid_m = ct.get("_납입개월", 0)
            paid_amt = int(prem * paid_m) if prem and paid_m else 0
        if paid_amt:
            safe_val(ws, 80, col, paid_amt)
    safe_val(ws, 80, SUM_COL, f"=SUM({start_ltr}80:{end_ltr}80)")

    # Row 81 납입할보험료 (was 76)
    for ct in contracts:
        col = COL_IDX.get(ct["열"], 4)
        topay_amt = ct.get("_topay", 0)
        if not topay_amt:
            prem = ct.get("월보험료", 0)
            total_m = ct.get("_총납입개월", 0)
            paid_m = ct.get("_납입개월", 0)
            remain = total_m - paid_m
            topay_amt = int(prem * remain) if prem and remain > 0 else 0
        if topay_amt:
            safe_val(ws, 81, col, topay_amt)
    safe_val(ws, 81, SUM_COL, f"=SUM({start_ltr}81:{end_ltr}81)")

    # Row 82 총납입보험료 = 기납입 + 납입할 (was 77)
    for c_ltr in COL_LTRS:
        col = COL_IDX[c_ltr]
        col_l = get_column_letter(col)
        safe_val(ws, 82, col, f"={col_l}80+{col_l}81")
    safe_val(ws, 82, SUM_COL, f"=SUM({start_ltr}82:{end_ltr}82)")

    if has_proposal:
        # L열 납입할보험료 — 월보험료 × 납입개월
        from services.proposal_parser import _parse_납입개월
        if proposal:
            riders = proposal.get("특약목록", [])
            주계약 = riders[0] if riders else {}
            납입개월 = _parse_납입개월(주계약.get("납입기간", ""))
            total_prem = proposal.get("보험료합계", 0)
            if 납입개월 and total_prem:
                topay = total_prem * 납입개월
                safe_val(ws, 81, PROP_COL, topay)
                safe_val(ws, 82, PROP_COL, topay)

        safe_val(ws, 80, TOTAL_COL, f"={k_ltr}80+{l_ltr}80")
        safe_val(ws, 81, TOTAL_COL, f"={k_ltr}81+{l_ltr}81")
        safe_val(ws, 82, TOTAL_COL, f"={k_ltr}82+{l_ltr}82")


def _fill_renewal(ws, contracts):
    """Row 85 갱신 구분, Row 86 보험료 변화 예고 (was 80/81)"""
    for i, ct in enumerate(contracts):
        col = COL_IDX.get(ct["열"], 4)
        name = ct.get("상품명", "")
        company = ct.get("보험사", "")
        prem = ct.get("월보험료", 0)
        total_m = ct.get("_총납입개월", 0)
        paid_m = ct.get("_납입개월", 0)

        # 갱신형 판별 (상품명 + 보험사 유형)
        is_renewal = "갱신" in name
        is_short = total_m and total_m <= 12
        # 손해보험 종합/건강보험 → 특약 갱신형 가능성 (부분 갱신형)
        is_sonhae = any(k in company for k in ["화재", "손해", "해상"])
        is_comprehensive = any(k in name for k in [
            "건강", "종합", "케어", "플러스", "훼밀리", "간편",
            "The", "NEW", "희망", "자녀", "Good",
        ])

        if is_renewal:
            renewal = "갱신형 ⚠️"
        elif is_short:
            renewal = "단기계약\n갱신없음"
        elif is_sonhae and is_comprehensive:
            renewal = "부분 갱신형 ⚠️"
        else:
            renewal = "비갱신형 ✅"
        safe_val(ws, 85, col, renewal)

        # 보험료 변화 예고
        if prem == 0:
            notice = "납입완료"
        elif is_renewal:
            notice = "갱신 시\n보험료 변동 예상 ⚠️"
        elif is_short:
            notice = "만기 소멸 예정"
        elif is_sonhae and is_comprehensive:
            notice = "특약 갱신 시\n일부 변동 가능 ⚠️"
        else:
            remain = total_m - paid_m if total_m else 0
            if remain <= 0:
                notice = "납입완료 예정"
            elif remain <= 24:
                notice = f"약 {remain}개월 후\n납입완료 예정"
            else:
                notice = "변동 없음"
        safe_val(ws, 86, col, notice)


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


def _final_format(ws, has_proposal=False):
    max_c = _MAX_COL_PROP if has_proposal else _MAX_COL
    for r in range(1, ws.max_row + 1):
        for c in range(1, max_c + 1):
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
        # Row 3, 5, 6: 상품명/납입기간/개월 — 가운데 정렬 + 줄바꿈
        if r in (3, 5, 6):
            for c in range(_DATA_START, _DATA_END + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.alignment = Alignment(
                        horizontal="center", vertical="center", wrap_text=True,
                    )
    # L열(제안) 상품명도 줄바꿈
    if has_proposal:
        for r in (3, 5, 6):
            cell = ws.cell(row=r, column=PROP_COL)
            if cell.__class__.__name__ != "MergedCell":
                cell.alignment = Alignment(
                    horizontal="center", vertical="center", wrap_text=True,
                )
    # Row 5, 6 행 높이 — 2줄 텍스트 표시용
    ws.row_dimensions[5].height = 30
    ws.row_dimensions[6].height = 30
    # 리뷰 행 서식
    for r in range(_REVIEW_START, _REVIEW_START + _REVIEW_COUNT):
        for c in range(1, max_c + 1):
            cell = ws.cell(row=r, column=c)
            if cell.__class__.__name__ != "MergedCell":
                cell.alignment = Alignment(
                    horizontal="left", vertical="center", wrap_text=True,
                )
