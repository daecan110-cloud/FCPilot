-- FCPilot Sprint 2 추가 테이블
-- Supabase SQL Editor에서 실행

-- 1. 개척 매장
CREATE TABLE IF NOT EXISTS fp_pioneer_shops (
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

ALTER TABLE fp_pioneer_shops ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_shops" ON fp_pioneer_shops
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_fp_pioneer_shops_fc_id ON fp_pioneer_shops(fc_id);

-- 2. 개척 방문 기록
CREATE TABLE IF NOT EXISTS fp_pioneer_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    shop_id UUID NOT NULL REFERENCES fp_pioneer_shops(id) ON DELETE CASCADE,
    visit_date DATE DEFAULT CURRENT_DATE,
    result TEXT DEFAULT '' CHECK (result IN ('', 'interest', 'rejected', 'revisit', 'contracted')),
    memo TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE fp_pioneer_visits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_visits" ON fp_pioneer_visits
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_fp_pioneer_visits_shop_id ON fp_pioneer_visits(shop_id);

-- updated_at 트리거
CREATE TRIGGER tr_fp_pioneer_shops_updated
    BEFORE UPDATE ON fp_pioneer_shops
    FOR EACH ROW EXECUTE FUNCTION fp_update_timestamp();
