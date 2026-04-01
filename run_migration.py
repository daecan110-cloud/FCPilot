"""SQL 마이그레이션 실행 스크립트 (1회용)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pg8000
from utils.secrets_loader import load_secrets

_secrets = load_secrets()
DB_PASSWORD = _secrets.get("database", {}).get("password", "")
# project ref를 supabase URL에서 추출
_sb_url = _secrets.get("supabase", {}).get("url", "")
PROJECT_REF = _sb_url.replace("https://", "").split(".")[0] if _sb_url else ""

# Supabase 연결 옵션 (순서대로 시도)
CONNECT_OPTIONS = [
    {
        "desc": "Pooler (transaction mode)",
        "host": f"aws-0-ap-northeast-2.pooler.supabase.com",
        "port": 6543,
        "user": f"postgres.{PROJECT_REF}",
    },
    {
        "desc": "Pooler (session mode)",
        "host": f"aws-0-ap-northeast-2.pooler.supabase.com",
        "port": 5432,
        "user": f"postgres.{PROJECT_REF}",
    },
    {
        "desc": "Direct DB",
        "host": f"db.{PROJECT_REF}.supabase.co",
        "port": 5432,
        "user": "postgres",
    },
]

SQL_FILES = [
    "sql/005_new_project_all_tables.sql",
]


def try_connect():
    for opt in CONNECT_OPTIONS:
        print(f"Trying {opt['desc']}...", end=" ")
        try:
            conn = pg8000.connect(
                host=opt["host"],
                port=opt["port"],
                database="postgres",
                user=opt["user"],
                password=DB_PASSWORD,
                timeout=10,
            )
            conn.autocommit = True
            conn.run("SELECT 1")
            print("OK!")
            return conn
        except Exception as e:
            print(f"FAIL: {e}")
    return None


def run_sql_file(conn, filepath):
    print(f"\n=== {filepath} ===")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by semicolons, handling $$ blocks
    statements = split_sql(content)
    for i, stmt in enumerate(statements):
        short = stmt.replace("\n", " ")[:60]
        try:
            conn.run(stmt)
            print(f"  [{i+1}] OK: {short}...")
        except Exception as e:
            err = str(e)
            if "already exists" in err:
                print(f"  [{i+1}] SKIP (already exists): {short}...")
            else:
                print(f"  [{i+1}] ERROR: {err}")
                return False
    return True


def split_sql(content):
    statements = []
    current = []
    in_dollar = False

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)

        if "$$" in stripped:
            in_dollar = not in_dollar

        if not in_dollar and stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current = []

    if current:
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)

    return statements


if __name__ == "__main__":
    conn = try_connect()
    if not conn:
        print("\nAll connection methods failed.")
        print("Please check your database password.")
        sys.exit(1)

    success = True
    for f in SQL_FILES:
        if not run_sql_file(conn, f):
            success = False
            break

    conn.close()

    if success:
        print("\n=== All migrations completed! ===")
    else:
        print("\n=== Migration stopped due to error ===")
        sys.exit(1)
