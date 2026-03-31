-- fp_reminders 테이블 RLS 활성화 확인 및 정책 추가
-- 이미 테이블이 존재하는 경우를 전제로 함

ALTER TABLE fp_reminders ENABLE ROW LEVEL SECURITY;

-- 기존 정책이 있으면 삭제 후 재생성
DROP POLICY IF EXISTS "fc_own_reminders" ON fp_reminders;

-- fc_id 기반 완전한 격리 정책 (SELECT/INSERT/UPDATE/DELETE 모두 적용)
CREATE POLICY "fc_own_reminders" ON fp_reminders
    FOR ALL
    USING (fc_id = auth.uid())
    WITH CHECK (fc_id = auth.uid());

-- 인덱스 (없을 경우 생성)
CREATE INDEX IF NOT EXISTS idx_fp_reminders_fc_id ON fp_reminders(fc_id);
CREATE INDEX IF NOT EXISTS idx_fp_reminders_client_id ON fp_reminders(client_id);
CREATE INDEX IF NOT EXISTS idx_fp_reminders_status ON fp_reminders(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_fp_reminders_date ON fp_reminders(reminder_date);
