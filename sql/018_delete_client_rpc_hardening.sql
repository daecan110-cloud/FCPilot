-- 018: delete_client RPC 보안 강화
-- 1. auth.uid() 검증 — 호출자가 자기 자신의 fc_id로만 호출 가능
-- 2. anon role 차단 — authenticated 만 실행

CREATE OR REPLACE FUNCTION delete_client(p_client_id UUID, p_fc_id UUID)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  -- 호출자 인증 확인 + fc_id 일치 검증 (다른 FC 고객 삭제 차단)
  IF auth.uid() IS NULL OR auth.uid() <> p_fc_id THEN
    RAISE EXCEPTION 'Unauthorized: fc_id mismatch';
  END IF;

  DELETE FROM fp_reminders WHERE client_id = p_client_id AND fc_id = p_fc_id;
  DELETE FROM client_contracts WHERE client_id = p_client_id AND fc_id = p_fc_id;
  DELETE FROM contact_logs WHERE client_id = p_client_id AND fc_id = p_fc_id;
  DELETE FROM clients WHERE id = p_client_id AND fc_id = p_fc_id;
END;
$$;

-- 권한 제한: anon 차단, authenticated 만 허용
REVOKE ALL ON FUNCTION delete_client(UUID, UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION delete_client(UUID, UUID) FROM anon;
GRANT EXECUTE ON FUNCTION delete_client(UUID, UUID) TO authenticated;
