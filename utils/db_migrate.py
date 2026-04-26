"""앱 시작 시 1회 실행되는 자동 마이그레이션.
Streamlit Cloud에서 pg8000으로 직접 DB에 접속하여 스키마를 갱신한다.
로컬 실행 시 연결 실패해도 앱 동작에는 영향 없음 (새 컬럼 없으면 graceful 처리).
"""
import streamlit as st

_MIGRATIONS = [
    # (설명, SQL)
    ("fp_reminders.result 컬럼", "ALTER TABLE fp_reminders ADD COLUMN IF NOT EXISTS result TEXT DEFAULT ''"),
    ("fp_reminders.result_memo 컬럼", "ALTER TABLE fp_reminders ADD COLUMN IF NOT EXISTS result_memo TEXT DEFAULT ''"),
    ("exec_sql 헬퍼 함수", """
        CREATE OR REPLACE FUNCTION exec_sql(query text)
        RETURNS text LANGUAGE plpgsql SECURITY DEFINER AS $$
        BEGIN EXECUTE query; RETURN 'OK'; END;
        $$
    """),
    ("exec_sql 권한 제한", """
        REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM anon, authenticated;
        GRANT EXECUTE ON FUNCTION exec_sql(text) TO service_role
    """),
    # RLS 강제 활성화 — 모든 public 테이블에 RLS 보장
    ("fp_products RLS 활성화",
     "ALTER TABLE IF EXISTS fp_products ENABLE ROW LEVEL SECURITY"),
    ("bot_sessions RLS 활성화",
     "ALTER TABLE IF EXISTS bot_sessions ENABLE ROW LEVEL SECURITY"),
    ("fp_products RLS 정책", """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'fp_products' AND policyname = 'fc_own_products'
            ) THEN
                CREATE POLICY "fc_own_products" ON fp_products
                    FOR ALL USING (fc_id = auth.uid())
                    WITH CHECK (fc_id = auth.uid());
            END IF;
        END $$
    """),
    # 레거시 테이블 RLS (존재할 경우)
    ("레거시 fp_ 테이블 RLS",
     """DO $$ DECLARE t TEXT; BEGIN
        FOREACH t IN ARRAY ARRAY[
            'fp_users_settings','fp_clients','fp_contact_logs',
            'fp_analysis_records','fp_pioneer_shops','fp_pioneer_visits','fp_yakwan_records'
        ] LOOP
            EXECUTE format('ALTER TABLE IF EXISTS %I ENABLE ROW LEVEL SECURITY', t);
        END LOOP;
     END $$"""),
    # analysis_records에 client_id FK 추가
    ("analysis_records.client_id 컬럼",
     "ALTER TABLE analysis_records ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id) ON DELETE SET NULL"),
    ("analysis_records.client_id 인덱스",
     "CREATE INDEX IF NOT EXISTS idx_analysis_records_client_id ON analysis_records(client_id)"),
]


def run_auto_migrations():
    """앱 세션당 1회 실행. 실패해도 조용히 넘어감."""
    if st.session_state.get("_migrations_done"):
        return
    st.session_state._migrations_done = True

    try:
        conn = _connect()
    except Exception:
        return
    if not conn:
        return

    try:
        for desc, sql in _MIGRATIONS:
            try:
                conn.run(sql)
            except Exception:
                pass  # already exists 등 무시
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _connect():
    """Streamlit secrets에서 DB 접속 정보를 읽어 pg8000으로 연결."""
    try:
        import pg8000
    except ImportError:
        return None

    db = st.secrets.get("database", {})
    sb = st.secrets.get("supabase", {})
    password = db.get("password", "")
    if not password:
        return None

    sb_url = sb.get("url", "")
    ref = sb_url.replace("https://", "").split(".")[0] if sb_url else ""
    host = db.get("host", f"db.{ref}.supabase.co")
    port = int(db.get("port", 5432))

    # 연결 시도 순서
    options = [
        (host, port, "postgres"),
        (f"aws-0-ap-northeast-2.pooler.supabase.com", 6543, f"postgres.{ref}"),
        (f"aws-0-ap-northeast-2.pooler.supabase.com", 5432, f"postgres.{ref}"),
    ]

    # 이전 성공 주소를 우선 시도
    last_ok = st.session_state.get("_db_migrate_ok_idx")
    if last_ok is not None:
        options = [options[last_ok]] + [o for i, o in enumerate(options) if i != last_ok]

    for idx, (h, p, u) in enumerate(options):
        try:
            conn = pg8000.connect(
                host=h, port=p, database="postgres",
                user=u, password=password, timeout=2,
            )
            conn.autocommit = True
            conn.run("SELECT 1")
            st.session_state._db_migrate_ok_idx = idx
            return conn
        except Exception:
            continue
    return None
