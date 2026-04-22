-- ═══════════════════════════════════════════════════════════════
-- 021: 긴급 RLS 전수 점검 및 수정
-- 날짜: 2026-04-23
-- 원인: Supabase 보안 경고 "rls_disabled_in_public"
--
-- 이 스크립트는 Supabase SQL Editor에서 실행하세요.
-- 이미 RLS가 켜져 있으면 무해하게 넘어갑니다.
-- ═══════════════════════════════════════════════════════════════

-- ┌─────────────────────────────────────────┐
-- │ STEP 0: 현재 RLS 상태 진단 (먼저 실행) │
-- └─────────────────────────────────────────┘
-- 아래 쿼리로 RLS 미적용 테이블 확인:
--
-- SELECT schemaname, tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY tablename;


-- ┌─────────────────────────────────────────┐
-- │ STEP 1: fp_products 테이블 RLS 활성화   │
-- └─────────────────────────────────────────┘
-- fp_products는 CREATE TABLE 마이그레이션 없이 수동 생성됨
-- RLS 미적용 상태일 가능성이 가장 높음

ALTER TABLE IF EXISTS fp_products ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "fc_own_products" ON fp_products;
CREATE POLICY "fc_own_products" ON fp_products
    FOR ALL
    USING (fc_id = auth.uid())
    WITH CHECK (fc_id = auth.uid());

CREATE INDEX IF NOT EXISTS idx_fp_products_fc_id ON fp_products(fc_id);


-- ┌─────────────────────────────────────────┐
-- │ STEP 2: bot_sessions 테이블 RLS 활성화  │
-- └─────────────────────────────────────────┘
-- bot_sessions는 텔레그램 봇 세션 저장용
-- service_role로만 접근하므로 정책 없이 RLS만 켜면 됨
-- (RLS ON + 정책 없음 = anon/authenticated 완전 차단, service_role만 통과)

ALTER TABLE IF EXISTS bot_sessions ENABLE ROW LEVEL SECURITY;


-- ┌─────────────────────────────────────────┐
-- │ STEP 3: 현재 운영 테이블 RLS 재확인     │
-- └─────────────────────────────────────────┘
-- 이미 활성화된 테이블이라도 확실하게 재실행 (멱등)

ALTER TABLE IF EXISTS users_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS contact_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS analysis_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pioneer_shops ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pioneer_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS yakwan_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS command_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS client_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS pioneer_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fp_reminders ENABLE ROW LEVEL SECURITY;


-- ┌─────────────────────────────────────────┐
-- │ STEP 4: 레거시 fp_ 테이블 RLS 강제 활성 │
-- └─────────────────────────────────────────┘
-- 001~004 마이그레이션으로 생성된 구버전 테이블이 아직 존재할 수 있음
-- 사용하지 않더라도 RLS를 켜서 공개 접근 차단

ALTER TABLE IF EXISTS fp_users_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fp_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fp_contact_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fp_analysis_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fp_pioneer_shops ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fp_pioneer_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS fp_yakwan_records ENABLE ROW LEVEL SECURITY;


-- ┌─────────────────────────────────────────┐
-- │ STEP 5: exec_sql 함수 권한 강화         │
-- └─────────────────────────────────────────┘
-- anon, authenticated, public 모두 차단 → service_role만 실행 가능

REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM anon;
REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM authenticated;
REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM public;
GRANT EXECUTE ON FUNCTION exec_sql(text) TO service_role;


-- ┌─────────────────────────────────────────┐
-- │ STEP 6: 검증 쿼리 (결과 확인 필수!)     │
-- └─────────────────────────────────────────┘
-- 이 쿼리 결과에서 rowsecurity = false 인 테이블이 없어야 함

SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
