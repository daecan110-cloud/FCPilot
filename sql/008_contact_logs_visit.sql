-- Sprint 7: contact_logs에 방문 예약 컬럼 추가
ALTER TABLE contact_logs
  ADD COLUMN IF NOT EXISTS visit_reserved BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS visit_datetime TIMESTAMPTZ;
