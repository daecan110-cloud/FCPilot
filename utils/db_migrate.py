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

    for h, p, u in options:
        try:
            conn = pg8000.connect(
                host=h, port=p, database="postgres",
                user=u, password=password, timeout=5,
            )
            conn.autocommit = True
            conn.run("SELECT 1")
            return conn
        except Exception:
            continue
    return None
