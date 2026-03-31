-- FCPilot: SQL 실행 헬퍼 함수 (1회 실행)
-- Supabase Dashboard SQL Editor에서 실행
-- 이후 Python에서 rpc('fp_exec_sql', {'query': sql})로 DDL 실행 가능

CREATE OR REPLACE FUNCTION fp_exec_sql(query text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  EXECUTE query;
  RETURN 'OK';
END;
$$;
