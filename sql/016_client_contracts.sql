-- 016: 기계약자 계약 정보 테이블
CREATE TABLE IF NOT EXISTS client_contracts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    fc_id UUID NOT NULL REFERENCES auth.users(id),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    company TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL DEFAULT '',
    category TEXT CHECK (category IN ('종신보험','건강보험','연금보험','저축보험','변액보험','기타')) DEFAULT '기타',
    monthly_premium INTEGER DEFAULT 0,
    contract_date DATE,
    main_coverage TEXT DEFAULT '',
    riders JSONB DEFAULT '[]'::jsonb,
    memo TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE client_contracts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_contracts" ON client_contracts
    FOR ALL USING (fc_id = auth.uid());

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_client_contracts_client ON client_contracts(client_id);
CREATE INDEX IF NOT EXISTS idx_client_contracts_fc ON client_contracts(fc_id);
