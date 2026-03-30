-- FCPilot Sprint 3: 약관 분석 기록 테이블
-- Supabase SQL Editor에서 실행

CREATE TABLE IF NOT EXISTS fp_yakwan_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES fp_analysis_records(id) ON DELETE SET NULL,
    contract_index INTEGER NOT NULL DEFAULT 0,
    company TEXT DEFAULT '',
    product TEXT DEFAULT '',
    yakwan_result JSONB DEFAULT '{}',
    k_column_text TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE fp_yakwan_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_yakwan" ON fp_yakwan_records
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_fp_yakwan_fc_id ON fp_yakwan_records(fc_id);
CREATE INDEX idx_fp_yakwan_analysis_id ON fp_yakwan_records(analysis_id);
