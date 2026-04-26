---
name: excel-validator
description: >
  보장분석표 엑셀 템플릿 검증. "엑셀 검증", "템플릿 확인", "행번호 체크" 요청 시 활성화.
  master_template.xlsx의 행번호/수식/병합 상태를 item_map.py와 교차 검증한다.
---

## 검증 절차

### 1. 템플릿 로드
```python
from openpyxl import load_workbook
wb = load_workbook("templates/master_template.xlsx")
ws = wb.active
```

### 2. DATA_ROWS 검증
`services/item_map.py`의 `DATA_ROWS`에 정의된 모든 행에 대해:
- B열 (항목명)에 값이 있는지
- K열 (L열=SUM_COL)에 `=SUM(D:J)` 수식이 있는지
- 해당 행이 병합에 포함되어 있다면 병합 범위 출력

### 3. ITEM_ROW_MAP 교차 검증
`services/item_map.py`의 `ITEM_ROW_MAP` 딕셔너리의 모든 값(행 번호)이:
- `DATA_ROWS`에 포함되는지
- None인 항목(무시 대상)이 적절한지

### 4. excel_helpers.py 상수 일치 확인
`services/excel_helpers.py`의 `DATA_START`, `DATA_END`, `REVIEW_START`, `REVIEW_COUNT`가
실제 템플릿 구조와 일치하는지 확인

### 5. 글로벌 스킬 동기화 (선택)
`~/.claude/skills/coverage-table/skill.md` 내 행번호 매핑표가 있다면
`item_map.py`와 비교하여 불일치 항목 출력

## 출력 형식
```
✅ DATA_ROWS 검증: N행 전체 정상
✅ ITEM_ROW_MAP: M개 항목 매핑 정상 (None 제외 K개)
✅ K열 SUM 수식: N행 정상
⚠️ 불일치 발견:
  - Row XX: item_map에 있지만 템플릿 B열 비어있음
  - Row YY: SUM 수식 누락
```

## 주의사항
- 템플릿 파일을 **절대 수정하지 마**. 읽기만 한다.
- 문제 발견 시 수정 방안을 제시하되, 실행은 영민 확인 후.
