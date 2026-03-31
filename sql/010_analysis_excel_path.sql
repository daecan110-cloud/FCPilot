-- Sprint 10 Round 2: 보장분석 Excel 영구 저장
-- analysis_records에 excel_path 컬럼 추가

ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS excel_path TEXT;
