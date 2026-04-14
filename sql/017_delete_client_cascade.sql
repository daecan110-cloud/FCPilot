-- 017: 고객 삭제 RPC 함수 (트랜잭션 원자성 보장)
-- fp_reminders FK에 ON DELETE CASCADE가 없을 수 있으므로,
-- RPC 함수로 모든 관련 데이터를 한 트랜잭션에서 삭제

-- 1. FK CASCADE 보장
ALTER TABLE IF EXISTS fp_reminders
  DROP CONSTRAINT IF EXISTS fp_reminders_client_id_fkey;
ALTER TABLE IF EXISTS fp_reminders
  ADD CONSTRAINT fp_reminders_client_id_fkey
  FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;

-- 2. 고객 삭제 RPC 함수
CREATE OR REPLACE FUNCTION delete_client(p_client_id UUID, p_fc_id UUID)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  DELETE FROM fp_reminders WHERE client_id = p_client_id AND fc_id = p_fc_id;
  DELETE FROM client_contracts WHERE client_id = p_client_id AND fc_id = p_fc_id;
  DELETE FROM contact_logs WHERE client_id = p_client_id AND fc_id = p_fc_id;
  DELETE FROM clients WHERE id = p_client_id AND fc_id = p_fc_id;
END;
$$;
