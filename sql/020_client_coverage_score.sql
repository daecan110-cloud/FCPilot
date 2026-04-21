-- 020: 고객 보장점수 컬럼 추가
-- 보장분석 PDF의 종합 진단 점수 (0~100)
ALTER TABLE clients ADD COLUMN IF NOT EXISTS coverage_score INTEGER DEFAULT 0;
