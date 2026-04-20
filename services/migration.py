"""구글시트 CSV → Supabase 마이그레이션"""
import csv
import io
import streamlit as st
from services.crypto import encrypt_phone, hash_phone_last4
from utils.supabase_client import get_supabase_client
from auth import get_current_user_id


def migrate_clients_csv(csv_bytes: bytes) -> dict:
    """CSV 파일에서 고객 데이터를 파싱하여 Supabase에 저장.

    CSV 컬럼 (유연하게 매핑):
      이름, 전화번호, 나이, 성별, 직업, 주소, 등급, 출처, 메모
    """
    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = csv_bytes.decode("cp949", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    sb = get_supabase_client()
    fc_id = get_current_user_id()

    success = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            name = _get(row, ["이름", "name", "고객명", "First Name", "Last Name", "Display Name"])
            phone = _get(row, ["전화번호", "phone", "연락처", "Phone 1 - Value", "Phone", "Mobile"])
            age = _get(row, ["나이", "age"])
            gender = _get(row, ["성별", "gender"])
            occupation = _get(row, ["직업", "occupation"])
            address = _get(row, ["주소", "address"])
            grade = _get(row, ["등급", "grade", "가망등급"])
            source = _get(row, ["출처", "source", "DB종류"])
            memo = _get(row, ["메모", "memo", "비고"])

            if not name:
                errors.append(f"행 {i}: 이름 없음")
                continue

            # 전화번호 정규화 (010-xxx-xxxxx → 010-xxxx-xxxx)
            phone = _normalize_phone(phone)

            # 전화번호 암호화
            phone_enc = encrypt_phone(phone) if phone else ""
            phone_hash = hash_phone_last4(phone) if phone else ""

            # 성별 정규화
            gender_val = None
            if gender:
                g = gender.strip()
                if g in ("남", "남성", "M", "male"):
                    gender_val = "M"
                elif g in ("여", "여성", "F", "female"):
                    gender_val = "F"

            # 등급 정규화
            grade_val = "C"
            if grade and grade.strip().upper() in ("A", "B", "C", "D"):
                grade_val = grade.strip().upper()

            sb.table("clients").insert({
                "fc_id": fc_id,
                "name": name.strip(),
                "phone_encrypted": phone_enc,
                "phone_last4_hash": phone_hash,
                "age": int(age) if age and age.strip().isdigit() else None,
                "gender": gender_val,
                "occupation": (occupation or "").strip(),
                "address": (address or "").strip(),
                "prospect_grade": grade_val,
                "db_source": (source or "").strip(),
                "memo": (memo or "").strip(),
            }).execute()
            success += 1
        except Exception as e:
            err_msg = str(e)
            if any(k in err_msg.lower() for k in ["duplicate", "null value", "violates"]):
                errors.append(f"행 {i}: 데이터 형식을 확인해주세요.")
            else:
                errors.append(f"행 {i}: 저장 실패 — 관리자에게 문의하세요.")

    return {"success": success, "errors": errors}


def _normalize_phone(phone: str) -> str:
    """전화번호 정규화 → 010-XXXX-XXXX 형식"""
    if not phone:
        return ""
    digits = phone.replace("-", "").replace(" ", "")
    if len(digits) == 11 and digits.startswith("010"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return phone


def _get(row: dict, keys: list) -> str:
    """여러 가능한 컬럼명에서 값 찾기"""
    for k in keys:
        if k in row and row[k]:
            return row[k].strip()
    return ""
