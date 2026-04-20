"""개척 매장 엑셀 일괄 등록 스크립트 (CLI용)

사용법:
    py scripts/import_pioneer_excel.py <엑셀파일경로>

Streamlit secrets에서 Supabase 인증 정보를 읽어 직접 등록합니다.
"""
import sys
import os
import tomllib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pioneer_import import parse_pioneer_excel, bulk_insert_shops
from supabase import create_client


def load_secrets() -> dict:
    """Streamlit secrets.toml에서 supabase 설정 로드"""
    secrets_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".streamlit", "secrets.toml"
    )
    with open(secrets_path, "rb") as f:
        return tomllib.load(f)


def main():
    if len(sys.argv) < 2:
        print("사용법: py scripts/import_pioneer_excel.py <엑셀파일경로>")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"파일을 찾을 수 없습니다: {filepath}")
        sys.exit(1)

    # 1. Supabase 연결
    secrets = load_secrets()
    sb_conf = secrets["supabase"]
    sb = create_client(sb_conf["url"], sb_conf["anon_key"])

    # 2. 로그인 (서비스 키 대신 FC 계정으로 로그인)
    email = input("FC 이메일: ").strip()
    password = input("비밀번호: ").strip()
    auth_res = sb.auth.sign_in_with_password({"email": email, "password": password})
    fc_id = auth_res.user.id
    print(f"로그인 성공: {fc_id}")

    # 3. 엑셀 파싱
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    rows, parse_errors = parse_pioneer_excel(file_bytes)
    for err in parse_errors:
        print(f"  경고: {err}")
    print(f"파싱 완료: {len(rows)}건")

    if not rows:
        print("등록할 데이터가 없습니다.")
        sys.exit(1)

    # 4. 중복 체크
    existing = sb.table("pioneer_shops").select("shop_name").eq("fc_id", fc_id).execute()
    existing_names = {r["shop_name"] for r in (existing.data or [])}
    new_rows = [r for r in rows if r["shop_name"] not in existing_names]
    dup_count = len(rows) - len(new_rows)

    if dup_count > 0:
        print(f"중복 {dup_count}건 제외 → 신규 {len(new_rows)}건")

    if not new_rows:
        print("모든 매장이 이미 등록되어 있습니다.")
        sys.exit(0)

    # 5. 등록
    confirm = input(f"{len(new_rows)}건 등록할까요? (y/n): ").strip().lower()
    if confirm != "y":
        print("취소됨")
        sys.exit(0)

    inserted, insert_errors = bulk_insert_shops(sb, fc_id, new_rows)
    for err in insert_errors:
        print(f"  에러: {err}")
    print(f"등록 완료: {inserted}건")


if __name__ == "__main__":
    main()
