-- Sprint 5: 텔레그램 명령 큐 (Claude Code 제어용)

CREATE TABLE IF NOT EXISTS command_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fc_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    command TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

ALTER TABLE command_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fc_own_commands" ON command_queue
    FOR ALL USING (fc_id = auth.uid());

CREATE INDEX idx_command_queue_status ON command_queue(status);
