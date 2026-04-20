-- 개척 리스트 팀원 공유 테이블
-- 한번 연결하면 끊기 전까지 상대방이 내 개척 매장을 볼 수 있음

CREATE TABLE IF NOT EXISTS pioneer_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    shared_with_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(owner_id, shared_with_id),
    CHECK (owner_id != shared_with_id)
);

ALTER TABLE pioneer_shares ENABLE ROW LEVEL SECURITY;

-- 공유 건은 owner 또는 shared_with 본인만 조회/삭제 가능
CREATE POLICY "own_shares" ON pioneer_shares
    FOR ALL USING (owner_id = auth.uid() OR shared_with_id = auth.uid());

CREATE INDEX idx_pioneer_shares_owner ON pioneer_shares(owner_id);
CREATE INDEX idx_pioneer_shares_shared ON pioneer_shares(shared_with_id);

-- 공유받은 사람이 공유자의 매장을 조회할 수 있도록 pioneer_shops RLS 정책 추가
CREATE POLICY "shared_shops_read" ON pioneer_shops
    FOR SELECT USING (
        fc_id IN (
            SELECT owner_id FROM pioneer_shares
            WHERE shared_with_id = auth.uid()
        )
    );
