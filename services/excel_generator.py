"""보장분석 엑셀 생성기"""
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill


def generate_analysis_excel(analysis: dict, client_name: str = "") -> bytes:
    """분석 결과를 엑셀 파일로 생성"""
    wb = Workbook()
    ws = wb.active
    ws.title = "보장분석표"

    # 스타일 정의
    header_font = Font(name="맑은 고딕", bold=True, size=14)
    sub_font = Font(name="맑은 고딕", bold=True, size=11)
    normal_font = Font(name="맑은 고딕", size=10)
    header_fill = PatternFill(start_color="1E88E5", end_color="1E88E5", fill_type="solid")
    header_font_white = Font(name="맑은 고딕", bold=True, size=11, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 제목
    ws.merge_cells("A1:F1")
    ws["A1"] = "보장분석표"
    ws["A1"].font = header_font
    ws["A1"].alignment = Alignment(horizontal="center")

    # 기본 정보
    row = 3
    info_labels = [
        ("보험사", analysis.get("insurance_company", "")),
        ("상품명", analysis.get("product_name", "")),
        ("계약일", analysis.get("contract_date", "")),
        ("만기일", analysis.get("expiry_date", "")),
        ("납입기간", analysis.get("payment_period", "")),
        ("월 보험료", _format_amount(analysis.get("monthly_premium"))),
    ]

    if client_name:
        info_labels.insert(0, ("고객명", client_name))

    for label, value in info_labels:
        ws.cell(row=row, column=1, value=label).font = sub_font
        ws.cell(row=row, column=2, value=value).font = normal_font
        ws.cell(row=row, column=1).border = thin_border
        ws.cell(row=row, column=2).border = thin_border
        row += 1

    # 보장 내역 헤더
    row += 1
    coverage_headers = ["특약명", "보장유형", "보장금액", "보장기간"]
    col_widths = [30, 12, 15, 12]
    for col_idx, (header, width) in enumerate(zip(coverage_headers, col_widths), 1):
        cell = ws.cell(row=row, column=col_idx, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border
        ws.column_dimensions[chr(64 + col_idx)].width = width

    # 보장 내역
    coverages = analysis.get("coverages", [])
    for cov in coverages:
        row += 1
        ws.cell(row=row, column=1, value=cov.get("rider_name", "")).font = normal_font
        ws.cell(row=row, column=2, value=cov.get("coverage_type", "")).font = normal_font
        ws.cell(row=row, column=3, value=_format_amount(cov.get("coverage_amount"))).font = normal_font
        ws.cell(row=row, column=4, value=cov.get("coverage_period", "")).font = normal_font
        for c in range(1, 5):
            ws.cell(row=row, column=c).border = thin_border
            ws.cell(row=row, column=c).alignment = Alignment(horizontal="center")
        ws.cell(row=row, column=1).alignment = Alignment(horizontal="left")

    # 열 너비 조정
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 15

    # 바이트로 변환
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _format_amount(amount) -> str:
    """금액 포맷 (만원 단위)"""
    if amount is None:
        return "-"
    try:
        amount = int(amount)
        if amount >= 10000:
            man = amount // 10000
            remainder = amount % 10000
            if remainder:
                return f"{man}만 {remainder:,}원"
            return f"{man:,}만원"
        return f"{amount:,}원"
    except (ValueError, TypeError):
        return str(amount)
