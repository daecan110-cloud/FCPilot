"""tests/pdfs/ 폴더의 모든 스마트보장분석 PDF를 파싱하여 검증

사용법:
  1. tests/pdfs/ 에 스마트보장분석 PDF를 넣기
  2. python tests/test_pdf_batch.py
  3. 결과: 각 PDF별 파싱 결과 + 검증 경고 + 2차 보완 항목 리포트

영민이 보장분석 뽑을 수 있는 고객 PDF를 전부 넣어주면,
파서가 못 잡는 패턴을 찾아서 개선합니다.
"""
import sys
import os
import io
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from services.pdf_extractor import extract_from_pdf, _parse_contracts, _parse_coverages
from services.item_map import ITEM_ROW_MAP, find_row_for_item
import pdfplumber

PDF_DIR = os.path.join(ROOT, "tests", "pdfs")


def _row_to_name(row_num):
    for name, rn in ITEM_ROW_MAP.items():
        if rn == row_num and len(name) >= 4:
            return name
    return f"행{row_num}"


def analyze_one(pdf_path):
    """PDF 하나를 파싱하고 1차/2차 비교 리포트 생성"""
    fname = os.path.basename(pdf_path)

    # Full parse (1차 + 2차)
    with open(pdf_path, "rb") as f:
        data = extract_from_pdf(io.BytesIO(f.read()))

    # 1차만 (coverage table only)
    with pdfplumber.open(pdf_path) as pdf:
        p3 = pdf.pages[2] if len(pdf.pages) > 2 else None
        if not p3:
            return None
        extra = []
        if len(pdf.pages) > 3:
            p4t = pdf.pages[3].extract_text() or ""
            if "계약현황" in p4t or "보유계약" in p4t:
                extra.append(pdf.pages[3])
        contracts = _parse_contracts(p3, extra)
        cov_1st, seen_1st = _parse_coverages(pdf, contracts)

    result = {
        "파일": fname,
        "고객명": data["고객명"],
        "성별": data["성별"],
        "나이": data["나이"],
        "계약수": len(data["_all_contracts"]),
        "계약": [],
        "1차_항목수": sum(len(v) for v in cov_1st.values()),
        "2차_항목수": sum(len(v) for v in data["_coverage_raw"].values()),
        "2차_추가": [],
        "경고": data.get("_warnings", []),
    }

    for c in data["_all_contracts"]:
        result["계약"].append(
            f'{c["보험사"]} / {c["상품명"][:25]} / {c["월보험료"]:,}원'
        )

    # 2차에서 추가된 항목 추적
    for ci in sorted(data["_coverage_raw"].keys()):
        ct = data["_all_contracts"][ci]
        c1 = cov_1st.get(ci, {})
        c2 = data["_coverage_raw"][ci]
        for k, v in sorted(c2.items(), key=lambda x: int(x[0])):
            if k not in c1:
                name = _row_to_name(int(k))
                result["2차_추가"].append(
                    f'계약{ci} {ct["보험사"][:8]} | row{k} {name} = {v}만원'
                )

    return result


def run():
    if not os.path.isdir(PDF_DIR):
        print(f"폴더 없음: {PDF_DIR}")
        print("tests/pdfs/ 폴더에 스마트보장분석 PDF를 넣어주세요.")
        return

    pdfs = sorted(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    if not pdfs:
        print(f"PDF 없음: {PDF_DIR}")
        print("tests/pdfs/ 폴더에 스마트보장분석 PDF를 넣어주세요.")
        return

    print(f"총 {len(pdfs)}개 PDF 분석\n")

    all_warnings = 0
    all_additions = 0

    for pdf_path in pdfs:
        r = analyze_one(pdf_path)
        if not r:
            print(f"  {os.path.basename(pdf_path)}: 파싱 실패\n")
            continue

        print(f"{'='*60}")
        print(f"  {r['파일']} — {r['고객명']} ({r['성별']}/{r['나이']}세)")
        print(f"{'='*60}")
        print(f"  계약: {r['계약수']}건")
        for c in r["계약"]:
            print(f"    {c}")
        print(f"  1차(Coverage Table): {r['1차_항목수']}개")
        print(f"  2차(Detail 보완):    {r['2차_항목수']}개 (+{len(r['2차_추가'])})")

        if r["2차_추가"]:
            print(f"  ── 2차에서 추가된 항목 ──")
            for item in r["2차_추가"]:
                print(f"    {item}")
            all_additions += len(r["2차_추가"])

        if r["경고"]:
            print(f"  ── 검증 경고 ──")
            for w in r["경고"]:
                print(f"    {w}")
            all_warnings += len(r["경고"])
        else:
            print(f"  검증: 경고 없음")
        print()

    print(f"{'='*60}")
    print(f"  총계: {len(pdfs)}개 PDF, 경고 {all_warnings}개, 2차 추가 {all_additions}개")
    print(f"{'='*60}")


if __name__ == "__main__":
    run()
