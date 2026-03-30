-- FCPilot Supabase 테이블 생성 (Sprint 1)
-- Supabase SQL Editor에서 실행

-- 1. FC 사용자 설정
CREATE TABLE IF NOT EXISTS fp_users_settings (
    id UUID PRIMARY KEY DEFAULT auth.uid(),
    display_name TEXT NOT NULL DEFAULT '',
    company TEXT DEFAULT '신한라이프',
    mode TEXT DEFAULT 'pioneer' CHECK (mode IN ('pioneer', 'referral', 'both')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE fp_users_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_settings" ON fp_users_settings
    FOR ALL USING (id = auth.uid());

-- 2. 고객 마스터
CREATE TABLE IF NOT EXISTS fp_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone_encrypted TEXT DEFAULT '',
    phone_last4_hash TEXT DEFAULT '',
    age INTEGER,
    gender TEXT CHECK (gender IN ('M', 'F', NULL)),
    occupation TEXT DEFAULT '',
    address TEXT DEFAULT '',
    prospect_grade TEXT DEFAULT 'C' CHECK (prospect_grade IN ('A', 'B', 'C', 'D')),
    source TEXT DEFAULT '',
    memo TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE fp_clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_clients" ON fp_clients
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_fp_clients_fc_id ON fp_clients(fc_id);

-- 3. 상담/터치 이력
CREATE TABLE IF NOT EXISTS fp_contact_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES fp_clients(id) ON DELETE CASCADE,
    contact_type TEXT NOT NULL CHECK (contact_type IN ('visit', 'call', 'message', 'email', 'other')),
    content TEXT DEFAULT '',
    next_action TEXT DEFAULT '',
    next_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE fp_contact_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_contact_logs" ON fp_contact_logs
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_fp_contact_logs_client_id ON fp_contact_logs(client_id);

-- 4. 보장분석 기록
CREATE TABLE IF NOT EXISTS fp_analysis_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    client_id UUID REFERENCES fp_clients(id) ON DELETE SET NULL,
    client_name TEXT DEFAULT '',
    analysis_result JSONB DEFAULT '{}',
    pdf_filename TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE fp_analysis_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_analysis" ON fp_analysis_records
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_fp_analysis_fc_id ON fp_analysis_records(fc_id);

-- updated_at 자동 갱신 함수
CREATE OR REPLACE FUNCTION fp_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_fp_users_settings_updated
    BEFORE UPDATE ON fp_users_settings
    FOR EACH ROW EXECUTE FUNCTION fp_update_timestamp();

CREATE TRIGGER tr_fp_clients_updated
    BEFORE UPDATE ON fp_clients
    FOR EACH ROW EXECUTE FUNCTION fp_update_timestamp();
