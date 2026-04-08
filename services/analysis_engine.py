"""보장분석 엔진 — pdfplumber 기반"""
import io
from services.pdf_extractor import extract_from_pdf
from services.excel_generator import generate_analysis_excel


def analyze_and_generate(
    pdf_bytes: bytes, **_kw,
) -> tuple[dict, list[tuple[str, bytes]]]:
    """PDF → 데이터 추출 → 엑셀 생성.

    Returns:
        (분석 데이터 dict, [(파일명, 엑셀 bytes)] 리스트)
    """
    pdf_stream = io.BytesIO(pdf_bytes)
    data = extract_from_pdf(pdf_stream)
    excel_files = generate_analysis_excel(data)
    return data, excel_files


def regenerate_excel(data: dict, **_kw) -> list[tuple[str, bytes]]:
    """기존 분석 데이터로 엑셀만 재생성 (PDF 재분석 없이)"""
    return generate_analysis_excel(data)
