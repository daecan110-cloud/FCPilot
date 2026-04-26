-- analysis_records에 client_id FK 추가 (ilike client_name 조회 → eq client_id 전환용)
ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_analysis_records_client_id ON analysis_records(client_id);
