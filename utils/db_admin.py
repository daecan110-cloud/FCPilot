"""Supabase DB 관리 유틸 — service_role 클라이언트 + SQL 실행

사용법:
1. Supabase Dashboard SQL Editor에서 1회 실행:
   CREATE OR REPLACE FUNCTION fp_exec_sql(query text)
   RETURNS text LANGUAGE plpgsql SECURITY DEFINER AS $$
   BEGIN EXECUTE query; RETURN 'OK'; END; $$;

2. 이후 Python에서:
   from utils.db_admin import run_sql_file
   run_sql_file("sql/003_sprint2_tables.sql")
"""
import streamlit as st
from supabase import create_client, Client


def get_admin_client() -> Client:
    """service_role_key 기반 클라이언트 (RLS 우회)"""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["service_role_key"]
    return create_client(url, key)


def table_exists(table_name: str) -> bool:
    """테이블 존재 여부 확인"""
    try:
        get_admin_client().table(table_name).select("*").limit(0).execute()
        return True
    except Exception:
        return False


def run_sql(sql: str) -> dict:
    """SQL 실행 — fp_exec_sql RPC 함수 사용

    Returns: {"ok": bool, "message": str}
    """
    try:
        res = get_admin_client().rpc("exec_sql", {"query": sql}).execute()
        return {"ok": True, "message": res.data or "OK"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def run_sql_file(filepath: str) -> dict:
    """SQL 파일 읽어서 실행"""
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    return run_sql(sql)


def run_sql_statements(filepath: str) -> list[dict]:
    """SQL 파일을 개별 문장으로 분리하여 순차 실행

    세미콜론으로 분리, 빈 문장/주석만 있는 문장 스킵.
    CREATE TRIGGER 등 복합 문장도 처리.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    statements = _split_sql(content)
    results = []
    for stmt in statements:
        res = run_sql(stmt)
        results.append({"sql": stmt[:80] + "...", **res})
        if not res["ok"]:
            # 'already exists' 에러는 무시하고 계속 진행
            if "already exists" in res["message"]:
                results[-1]["ok"] = True
                results[-1]["message"] += " (이미 존재 — 스킵)"
            else:
                break
    return results


def _split_sql(content: str) -> list[str]:
    """SQL 내용을 실행 가능한 문장 단위로 분리"""
    statements = []
    current = []
    in_function = False

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        current.append(line)

        # $$ 블록 (함수 본문) 감지
        if "$$" in stripped:
            in_function = not in_function

        if not in_function and stripped.endswith(";"):
            stmt = "\n".join(current).strip().rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current = []

    if current:
        stmt = "\n".join(current).strip().rstrip(";").strip()
        if stmt:
            statements.append(stmt)

    return statements


def check_migration_status() -> dict:
    """마이그레이션 상태 확인"""
    tables = {
        "users_settings": "001",
        "clients": "001",
        "contact_logs": "001",
        "analysis_records": "001",
        "pioneer_shops": "003",
        "pioneer_visits": "003",
        "yakwan_records": "004",
    }
    status = {}
    for tbl, sql_num in tables.items():
        status[tbl] = {
            "exists": table_exists(tbl),
            "sql_file": f"sql/{sql_num}_*.sql",
        }
    return status
