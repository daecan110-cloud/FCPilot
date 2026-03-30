"""전화번호 암호화/복호화 모듈"""
import hashlib
import streamlit as st
from cryptography.fernet import Fernet


def get_cipher() -> Fernet:
    """secrets.toml에서 암호화 키 로드"""
    key = st.secrets["security"]["encryption_key"]
    return Fernet(key.encode())


def encrypt_phone(phone: str) -> str:
    """전화번호 암호화"""
    if not phone:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(phone.encode()).decode()


def decrypt_phone(encrypted: str) -> str:
    """전화번호 복호화"""
    if not encrypted:
        return ""
    cipher = get_cipher()
    return cipher.decrypt(encrypted.encode()).decode()


def hash_phone_last4(phone: str) -> str:
    """전화번호 뒷 4자리 해시 (검색용)"""
    if not phone:
        return ""
    last4 = phone.replace("-", "")[-4:]
    return hashlib.sha256(last4.encode()).hexdigest()[:16]
