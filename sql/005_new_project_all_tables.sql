-- FCPilot 전체 테이블 생성 (새 프로젝트: ghglnszzjuuvrrwpvhhb)
-- fp_ 접두사 제거 버전
-- Supabase SQL Editor에서 1회 실행

-- ═══════════════════════════════════════════
-- 0. 헬퍼 함수
-- ═══════════════════════════════════════════

-- 타임스탬프 자동 업데이트
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- SQL 실행 헬퍼 (Python에서 DDL 실행용)
CREATE OR REPLACE FUNCTION exec_sql(query text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN EXECUTE query; RETURN 'OK'; END;
$$;

-- ═══════════════════════════════════════════
-- 1. users_settings (FC 설정)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS users_settings (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT DEFAULT '',
    company TEXT DEFAULT '',
    mode TEXT DEFAULT 'pioneer' CHECK (mode IN ('pioneer', 'referral', 'both')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE users_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "own_settings" ON users_settings
    FOR ALL USING (id = auth.uid());

CREATE TRIGGER tr_users_settings_updated
    BEFORE UPDATE ON users_settings
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- 신규 유저 자동 설정 생성
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users_settings (id, display_name)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ═══════════════════════════════════════════
-- 2. clients (고객 마스터)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    phone_encrypted TEXT DEFAULT '',
    phone_last4_hash TEXT DEFAULT '',
    age INTEGER,
    gender TEXT DEFAULT '' CHECK (gender IN ('', 'M', 'F')),
    occupation TEXT DEFAULT '',
    address TEXT DEFAULT '',
    memo TEXT DEFAULT '',
    prospect_grade TEXT DEFAULT 'C' CHECK (prospect_grade IN ('A', 'B', 'C', 'D')),
    db_source TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_clients" ON clients
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_clients_fc_id ON clients(fc_id);

CREATE TRIGGER tr_clients_updated
    BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ═══════════════════════════════════════════
-- 3. contact_logs (상담/터치 이력)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS contact_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    touch_method TEXT DEFAULT '',
    memo TEXT DEFAULT '',
    next_date DATE,
    next_action TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE contact_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_contact_logs" ON contact_logs
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_contact_logs_client_id ON contact_logs(client_id);

-- ═══════════════════════════════════════════
-- 4. analysis_records (보장분석 기록)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS analysis_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    client_name TEXT DEFAULT '',
    contract_count INTEGER DEFAULT 0,
    result_summary JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE analysis_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_analysis" ON analysis_records
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_analysis_records_fc_id ON analysis_records(fc_id);

-- ═══════════════════════════════════════════
-- 5. pioneer_shops (개척 매장)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS pioneer_shops (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    shop_name TEXT NOT NULL,
    address TEXT DEFAULT '',
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    category TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    memo TEXT DEFAULT '',
    photo_url TEXT DEFAULT '',
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'visited', 'contracted', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE pioneer_shops ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_shops" ON pioneer_shops
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_pioneer_shops_fc_id ON pioneer_shops(fc_id);

CREATE TRIGGER tr_pioneer_shops_updated
    BEFORE UPDATE ON pioneer_shops
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ═══════════════════════════════════════════
-- 6. pioneer_visits (개척 방문 기록)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS pioneer_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    shop_id UUID NOT NULL REFERENCES pioneer_shops(id) ON DELETE CASCADE,
    visit_date DATE DEFAULT CURRENT_DATE,
    result TEXT DEFAULT '' CHECK (result IN ('', 'interest', 'rejected', 'revisit', 'contracted')),
    memo TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE pioneer_visits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_visits" ON pioneer_visits
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_pioneer_visits_shop_id ON pioneer_visits(shop_id);

-- ═══════════════════════════════════════════
-- 7. yakwan_records (약관 분석 기록)
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS yakwan_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    analysis_id UUID REFERENCES analysis_records(id) ON DELETE SET NULL,
    contract_index INTEGER NOT NULL DEFAULT 0,
    company TEXT DEFAULT '',
    product TEXT DEFAULT '',
    yakwan_result JSONB DEFAULT '{}',
    k_column_text TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE yakwan_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_yakwan" ON yakwan_records
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_yakwan_fc_id ON yakwan_records(fc_id);
CREATE INDEX idx_yakwan_analysis_id ON yakwan_records(analysis_id);
