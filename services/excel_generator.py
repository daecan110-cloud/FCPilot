"""보장분석 엑셀 생성기 — master_template.xlsx 서식 100% 보존"""
import io
import os
import math
import shutil
import tempfile
from copy import copy
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from services.item_map import COL_IDX, COL_LTRS

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "templates", "master_template.xlsx"
)

REVIEW_START = 75
REVIEW_TEMPLATE_ROWS = 5  # 템플릿 기본 리뷰 행 (Row 75~79)


def safe_val(ws, row, col, value):
    """값만 설정. 서식은 절대 건드리지 않음."""
    cell = ws.cell(row=row, column=col)
    if cell.__class__.__name__ != "MergedCell":
        cell.value = value


def generate_analysis_excel(
    data: dict, include_review: bool = False
) -> list[tuple[str, bytes]]:
    all_contracts = data.get("_all_contracts", data.get("계약", []))
    coverage_raw = data.get("_coverage_raw", {})
    customer = data.get("고객명", "고객")

    if len(all_contracts) <= 7:
        sd = _make_slice(data, all_contracts, coverage_raw)
        b = _fill_primary(sd, data, include_review)
        return [(f"{customer}_보장분석표.xlsx", b)]

    results = []
    num_files = math.ceil(len(all_contracts) / 7)
    for i in range(num_files):
        chunk = all_contracts[i * 7:(i + 1) * 7]
        sd = _make_slice(data, chunk, coverage_raw)
        if i == 0:
            b = _fill_primary(sd, data, include_review)
        else:
            b = _fill_secondary(sd)
        results.append((f"{customer}_보장분석표_{i + 1}.xlsx", b))
    return results


def _make_slice(base, contracts, coverage_raw):
    data = {
        "고객명": base["고객명"], "성별": base["성별"], "나이": base["나이"],
        "계약": [], "보장금액": {}, "기납입보험료": {}, "납입할보험료": {},
    }
    for new_i, c in enumerate(contracts):
        col = COL_LTRS[new_i]
        nc = {k: v for k, v in c.items() if not k.startswith("_")}
        nc["열"] = col
        data["계약"].append(nc)
        data["기납입보험료"][col] = c["_paid"]
        data["납입할보험료"][col] = c["_topay"]
        if c["_idx"] in coverage_raw:
            data["보장금액"][col] = coverage_raw[c["_idx"]]
    return data


# ══════════════════════════════════════════════════════════════════
# 파일1: 전체 (보장금액 + 리뷰 + 가족 + 세액공제)
# ══════════════════════════════════════════════════════════════════

def _fill_primary(slice_data, full_data, include_review):
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy(TEMPLATE_PATH, tmp.name)
    wb = load_workbook(tmp.name)
    ws = wb.active

    all_contracts = full_data.get("_all_contracts", [])
    extra = max(0, len(all_contracts) - REVIEW_TEMPLATE_ROWS)

    # 리뷰 행 추가 필요 시 먼저 삽입 (하단 섹션 밀림)
    if extra > 0:
        _insert_review_rows(ws, extra)

    # 값 클리어 (서식 보존, 값만 None)
    _clear_values(ws, extra)

    # 데이터 채우기
    _fill_common(ws, slice_data)

    if include_review:
        _fill_renewal(ws, slice_data.get("계약", []))

    k_column = full_data.get("_k_column", {})
    _fill_review_values(ws, all_contracts, k_column)
    _fill_family_values(ws, full_data, extra)
    _fill_tax_values(ws, full_data, extra)

    _final_format_pass(ws)

    buf = io.BytesIO()
    wb.save(buf)
    os.unlink(tmp.name)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# 파일2+: Row 1~69만
# ══════════════════════════════════════════════════════════════════

def _fill_secondary(slice_data):
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp.close()
    shutil.copy(TEMPLATE_PATH, tmp.name)
    wb = load_workbook(tmp.name)
    ws = wb.active

    _clear_values_top(ws)
    _fill_common(ws, slice_data)

    # Row 70+ 삭제
    merges_to_remove = [m for m in list(ws.merged_cells.ranges) if m.min_row >= 70]
    for m in merges_to_remove:
        ws.unmerge_cells(str(m))
    if ws.max_row >= 70:
        ws.delete_rows(70, ws.max_row - 69)

    _final_format_pass(ws)

    buf = io.BytesIO()
    wb.save(buf)
    os.unlink(tmp.name)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# 공통: Row 1~69 데이터
# ══════════════════════════════════════════════════════════════════

def _fill_common(ws, slice_data):
    customer = slice_data.get("고객명", "고객")
    gender = slice_data.get("성별", "남")
    age = slice_data.get("나이", 0)
    contracts = slice_data.get("계약", [])[:7]

    safe_val(ws, 1, 1, f"{customer} 님({gender} - {age}세)을 위한 보장분석")

    for c in contracts:
        col = COL_IDX.get(c["열"], 4)
        safe_val(ws, 2, col, c.get("보험사", ""))
        safe_val(ws, 3, col, c.get("상품명", ""))
        safe_val(ws, 4, col, c.get("보장나이", ""))
        safe_val(ws, 5, col, c.get("월보험료", 0))
        safe_val(ws, 6, col, c.get("가입시기", ""))

    for col_ltr, row_data in slice_data.get("보장금액", {}).items():
        col = COL_IDX.get(col_ltr)
        if not col:
            continue
        for row_str, amount in row_data.items():
            row_num = int(row_str)
            if 7 <= row_num <= 64:
                safe_val(ws, row_num, col, amount if amount else None)

    paid = slice_data.get("기납입보험료", {})
    to_pay = slice_data.get("납입할보험료", {})
    for col_ltr in COL_LTRS[:len(contracts)]:
        col = COL_IDX[col_ltr]
        safe_val(ws, 65, col, paid.get(col_ltr, 0) or None)
        safe_val(ws, 66, col, to_pay.get(col_ltr, 0) or None)


# ══════════════════════════════════════════════════════════════════
# 값 클리어 (서식 유지, 값만 None)
# ══════════════════════════════════════════════════════════════════

def _clear_values(ws, extra):
    """파일1 클리어: 값만 지움, 서식 보존"""
    ranges = [
        (1, 1, 1, 11),
        (2, 4, 6, 10),
        (7, 4, 64, 10),
        (65, 4, 66, 10),
        (70, 4, 71, 10),
        (75, 1, 79 + extra, 11),   # 리뷰 (삽입분 포함)
        (84 + extra, 1, 87 + extra, 11),  # 가족 (밀린 위치)
        (91 + extra, 4, 93 + extra, 11),  # 세액공제 (밀린 위치)
    ]
    for r_s, c_s, r_e, c_e in ranges:
        for r in range(r_s, r_e + 1):
            for c in range(c_s, c_e + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.value = None


def _clear_values_top(ws):
    """파일2 클리어: Row 1~69 값만"""
    for r_s, c_s, r_e, c_e in [(1,1,1,11), (2,4,6,10), (7,4,64,10), (65,4,66,10)]:
        for r in range(r_s, r_e + 1):
            for c in range(c_s, c_e + 1):
                cell = ws.cell(row=r, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    cell.value = None


# ══════════════════════════════════════════════════════════════════
# 리뷰 행 삽입 (서식 완전 복제)
# ══════════════════════════════════════════════════════════════════

def _insert_review_rows(ws, count):
    """Row 80 위치에 행 삽입 + Row 75 서식/병합/높이 완전 복제"""
    insert_at = REVIEW_START + REVIEW_TEMPLATE_ROWS  # Row 80

    # 1) 삽입 전: Row 80+ 병합 + 행높이 기록 후 해제
    merges_above = []
    heights_above = {}
    for m in list(ws.merged_cells.ranges):
        if m.min_row >= insert_at:
            merges_above.append((m.min_row, m.min_col, m.max_row, m.max_col))
            ws.unmerge_cells(str(m))
    for r in range(insert_at, ws.max_row + 1):
        h = ws.row_dimensions[r].height
        if h:
            heights_above[r] = h

    # 2) 행 삽입
    ws.insert_rows(insert_at, count)

    # 2b) 기존 행높이 복원 (shifted by count)
    for orig_row, h in heights_above.items():
        ws.row_dimensions[orig_row + count].height = h

    # 3) 기존 병합 복원 (shifted by count)
    for r1, c1, r2, c2 in merges_above:
        try:
            ws.merge_cells(
                start_row=r1 + count, start_column=c1,
                end_row=r2 + count, end_column=c2,
            )
        except Exception:
            pass

    # 4) 삽입된 행에 Row 75 서식 복제
    src = REVIEW_START
    src_height = ws.row_dimensions[src].height or 69.75

    for offset in range(count):
        dst = insert_at + offset
        ws.row_dimensions[dst].height = src_height

        for col in range(1, 12):
            src_cell = ws.cell(row=src, column=col)
            dst_cell = ws.cell(row=dst, column=col)
            if src_cell.__class__.__name__ == "MergedCell":
                continue
            if dst_cell.__class__.__name__ == "MergedCell":
                continue
            dst_cell.font = copy(src_cell.font)
            dst_cell.fill = copy(src_cell.fill)
            dst_cell.border = copy(src_cell.border)
            dst_cell.alignment = copy(src_cell.alignment)
            dst_cell.number_format = src_cell.number_format

        # Row 75 병합 패턴: A:B, E:H, I:K
        try:
            ws.merge_cells(f"A{dst}:B{dst}")
        except Exception:
            pass
        try:
            ws.merge_cells(f"E{dst}:H{dst}")
        except Exception:
            pass
        try:
            ws.merge_cells(f"I{dst}:K{dst}")
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
# 갱신/보험료변화 (Row 70~71) — 값+스타일 직접 설정
# ══════════════════════════════════════════════════════════════════

def _fill_renewal(ws, contracts):
    for c in contracts:
        col = COL_IDX.get(c["열"], 4)
        text, bg, fc = _infer_renewal(c)
        cell = ws.cell(row=70, column=col)
        if cell.__class__.__name__ != "MergedCell":
            cell.value = text
            cell.fill = PatternFill(fill_type="solid", fgColor=bg)
            cell.font = Font(name="Malgun Gothic", bold=True, size=8.5, color=fc)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        text, bg, bold, fc = _infer_premium_change(c)
        cell = ws.cell(row=71, column=col)
        if cell.__class__.__name__ != "MergedCell":
            cell.value = text
            cell.fill = PatternFill(fill_type="solid", fgColor=bg)
            cell.font = Font(name="Malgun Gothic", bold=bold, size=8.5, color=fc)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _infer_renewal(contract):
    combined = contract.get("상품명", "") + contract.get("보장나이", "")
    if any(k in combined for k in ["실손", "의료비보험"]):
        return ("갱신형", "FCE4D6", "C00000")
    if any(k in combined for k in ["단체", "단기", "단년"]):
        return ("단기계약\n(갱신 없음)", "F2F2F2", "595959")
    if any(k in combined for k in ["종신", "변액", "어린이"]):
        return ("비갱신형", "D5E8D4", "375623")
    if any(k in combined for k in ["100세", "80세"]):
        return ("비갱신형", "D5E8D4", "375623")
    return ("부분 갱신형", "FFF2CC", "7F6000")


def _infer_premium_change(contract):
    combined = contract.get("상품명", "") + contract.get("보장나이", "")
    if any(k in combined for k in ["단체", "단기"]):
        return ("만기 소멸 예정", "FFF0F0", True, "C00000")
    if any(k in combined for k in ["실손", "의료비"]):
        return ("갱신 시\n급등 예상", "FCE4D6", True, "C00000")
    if any(k in combined for k in ["종신", "100세"]):
        return ("변동 없음", "D5E8D4", False, "375623")
    return ("납입 완료 후\n변동 없음", "D6E4F7", False, "1F2D3D")


# ══════════════════════════════════════════════════════════════════
# 리뷰 (Row 75~) — 값만 설정, 서식 건드리지 않음
# ══════════════════════════════════════════════════════════════════

def _fill_review_values(ws, all_contracts, k_column=None):
    k_column = k_column or {}
    for i, c in enumerate(all_contracts):
        r = REVIEW_START + i
        safe_val(ws, r, 1, f"{c.get('보험사', '')}\n{c.get('상품명', '')}")
        start = c.get("가입시기", "")
        period = c.get("보장나이", "")
        safe_val(ws, r, 3, f"{start}~{period}" if start and period else start)
        prem = c.get("월보험료", 0)
        safe_val(ws, r, 4, f"{prem:,}원" if prem > 0 else "0원\n(단체/무료)")
        safe_val(ws, r, 5, _build_review(c))
        # K열(I~K 병합): 약관 분석 결과. col 9(I열)에 설정 → 병합 셀 전체 표시
        k_text = k_column.get(i, k_column.get(str(i), ""))
        safe_val(ws, r, 9, k_text if k_text else "약관 제공 시\n분석 가능")


def _build_review(contract):
    combined = contract.get("상품명", "") + contract.get("보험사", "")
    period = contract.get("보장나이", "")
    premium = contract.get("월보험료", 0)
    checks = []
    if any(k in combined for k in ["단체", "단기"]):
        checks.append("단체/단기계약 - 퇴직/탈퇴 시 자동 소멸")
        checks.append("개인 보험 전환 필요 여부 검토")
    elif any(k in combined for k in ["실손", "의료비"]):
        checks.append("실손의료비 보험 가입")
        checks.append("갱신형: 5년마다 보험료 재산정")
    elif any(k in combined for k in ["종신", "변액"]):
        checks.append("종신/변액보험 - 비갱신형")
        if premium > 0:
            checks.append(f"납입 현황: 월 {premium:,}원")
    elif any(k in combined for k in ["운전자", "자동차"]):
        checks.append("운전자보험 가입")
        checks.append("교통상해/벌금/변호사선임비 보장")
    elif any(k in combined for k in ["치아"]):
        checks.append("치아보험 가입")
        checks.append("보철/보존 치료비 보장")
    elif any(k in combined for k in ["CI"]):
        checks.append("CI보험 - 중대질병 진단 시 보험금 지급")
        checks.append(f"보장기간: {period}")
    elif any(k in combined for k in ["건강", "상해", "종합"]):
        checks.append("건강/상해 보장")
        checks.append(f"보장기간: {period}")
    else:
        checks.append(f"보장 내용 확인 필요 (보장나이: {period})")
    return "\n".join(checks)


# ══════════════════════════════════════════════════════════════════
# 가족 보장 현황 — 값만 설정
# ══════════════════════════════════════════════════════════════════

def _fill_family_values(ws, full_data, offset):
    customer = full_data.get("고객명", "")
    age = full_data.get("나이", 0)
    all_contracts = full_data.get("_all_contracts", [])
    coverage_raw = full_data.get("_coverage_raw", {})

    total_premium = sum(c.get("월보험료", 0) for c in all_contracts)
    death_total = sum(cov.get("7", 0) for cov in coverage_raw.values())
    cancer_total = sum(cov.get("16", 0) for cov in coverage_raw.values())
    has_silson = any(
        cov.get("63", 0) > 0 or cov.get("64", 0) > 0
        for cov in coverage_raw.values()
    )

    issues = []
    if death_total < 5000:
        issues.append("사망보장 보강 필요")
    if cancer_total < 3000:
        issues.append("암보장 보강 필요")
    if not has_silson:
        issues.append("실손 미가입")
    summary = " / ".join(issues) if issues else "주요 보장 적정"

    r = 84 + offset
    safe_val(ws, r, 1, "본인")
    safe_val(ws, r, 2, f"{customer} / {age}세")
    safe_val(ws, r, 4, f"{total_premium:,}원")
    safe_val(ws, r, 6, f"{death_total:,}만원" if death_total else "-")
    safe_val(ws, r, 7, f"{cancer_total:,}만원" if cancer_total else "-")
    safe_val(ws, r, 8, "가입" if has_silson else "미가입")
    safe_val(ws, r, 9, summary)

    safe_val(ws, r + 1, 1, "배우자")
    safe_val(ws, r + 1, 2, "           /       세")
    safe_val(ws, r + 2, 1, "자녀1")
    safe_val(ws, r + 2, 2, "           /       세")
    safe_val(ws, r + 3, 1, "자녀2")
    safe_val(ws, r + 3, 2, "           /       세")


# ══════════════════════════════════════════════════════════════════
# 세액공제 — 값만 설정
# ══════════════════════════════════════════════════════════════════

def _fill_tax_values(ws, full_data, offset):
    all_contracts = full_data.get("_all_contracts", [])
    r91 = 91 + offset
    r92 = 92 + offset
    r93 = 93 + offset

    for i, c in enumerate(all_contracts[:7]):
        col = COL_IDX[COL_LTRS[i]]
        monthly = c.get("월보험료", 0)
        annual = monthly * 12

        safe_val(ws, r91, col, f"{annual:,}원" if annual > 0 else "0원")
        safe_val(ws, r92, col, _calc_tax(c, annual))
        safe_val(ws, r93, col, _tax_note(c))

    total_annual = sum(c.get("월보험료", 0) * 12 for c in all_contracts)
    max_ded = min(total_annual, 1000000)
    ded_local = int(max_ded * 0.132)
    safe_val(ws, r91, 9, f"{total_annual:,}원")
    safe_val(ws, r92, 9, f"최대 연 {ded_local:,}원\n(지방세 포함)")


def _calc_tax(contract, annual):
    combined = contract.get("상품명", "")
    if contract.get("월보험료", 0) == 0:
        return "비해당\n(무료/단체)"
    if any(k in combined for k in ["단체", "단기"]):
        return "비해당\n(단체계약)"
    amount = int(min(annual, 1000000) * 0.12)
    return f"{amount:,}원"


def _tax_note(contract):
    combined = contract.get("상품명", "")
    if contract.get("월보험료", 0) == 0 or any(k in combined for k in ["단체", "단기"]):
        return "단체보험\n세액공제 비해당"
    if any(k in combined for k in ["종신", "변액"]):
        return "종신/변액\n무해지환급형 유지"
    if any(k in combined for k in ["실손", "의료비"]):
        return "실손의료비\n위험보험료 별도 확인"
    if any(k in combined for k in ["운전자"]):
        return "운전자 특화\n상해사망/수술비 포함"
    if any(k in combined for k in ["치아"]):
        return "치아보험\n보철/보존 치료"
    if any(k in combined for k in ["CI"]):
        return "CI보험\n중대질병 보장"
    return ""


# ══════════════════════════════════════════════════════════════════
# 최종 포맷 패스 — 저장 직전 무조건 실행
# ══════════════════════════════════════════════════════════════════

def _final_format_pass(ws):
    """전체 셀: Malgun Gothic 강제, Row 3 wrap_text. MergedCell skip."""
    for r in range(1, ws.max_row + 1):
        for c in range(1, 12):  # A~K
            cell = ws.cell(row=r, column=c)
            if cell.__class__.__name__ == "MergedCell":
                continue
            # 폰트: Malgun Gothic 강제 (기존 size, bold, color 유지)
            old = cell.font
            cell.font = Font(
                name="Malgun Gothic",
                size=old.size if old.size else 9,
                bold=old.bold if old.bold else False,
                italic=old.italic if old.italic else False,
                color=old.color,
            )
        # Row 3: 상품명 줄바꿈
        if r == 3:
            for c in range(4, 11):  # D~J
                cell = ws.cell(row=3, column=c)
                if cell.__class__.__name__ != "MergedCell":
                    old_al = cell.alignment
                    cell.alignment = Alignment(
                        horizontal=old_al.horizontal or "center",
                        vertical=old_al.vertical or "center",
                        wrap_text=True,
                    )
