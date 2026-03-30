"""보장분석 엔진 — pdfplumber 기반 (Claude API 최소화)"""
import io
from services.pdf_extractor import extract_from_pdf
from services.excel_generator import generate_analysis_excel


def analyze_and_generate(
    pdf_bytes: bytes,
    include_review: bool = False,
    k_column_data: dict = None,
) -> tuple[dict, list[tuple[str, bytes]]]:
    """PDF → 데이터 추출 → 엑셀 생성.

    Args:
        k_column_data: {contract_idx: "K열 텍스트"} — 약관 분석 결과

    Returns:
        (분석 데이터 dict, [(파일명, 엑셀 bytes)] 리스트)
    """
    pdf_stream = io.BytesIO(pdf_bytes)
    data = extract_from_pdf(pdf_stream)
    if k_column_data:
        data["_k_column"] = k_column_data
    excel_files = generate_analysis_excel(data, include_review=include_review)
    return data, excel_files
