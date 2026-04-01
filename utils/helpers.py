"""공통 유틸리티"""
import html as _html


def esc(text: str) -> str:
    """HTML 이스케이프 — unsafe_allow_html=True 컨텍스트에서 사용자 입력 보호"""
    return _html.escape(str(text)) if text else ""


def mask_name(name: str) -> str:
    """김영민 → 김**"""
    if not name or len(name) < 2:
        return "***"
    return name[0] + "*" * (len(name) - 1)


def mask_phone(phone: str) -> str:
    """010-1234-5678 → ***-****-5678"""
    if not phone:
        return "***"
    parts = phone.replace("-", "")
    return f"***-****-{parts[-4:]}"


def safe_error(action: str, e: Exception) -> str:
    """사용자에게 보여줄 안전한 에러 메시지 (DB 스키마/내부 정보 숨김)"""
    err = str(e)
    # 일반적인 사용자 실수 메시지는 그대로 표시
    for keyword in ["already exists", "duplicate", "violates check", "null value"]:
        if keyword in err.lower():
            return f"{action}: 데이터 형식을 확인해주세요."
    return f"{action}: 오류가 발생했습니다. 다시 시도해주세요."


def validate_file(uploaded_file, allowed_types: list, max_mb: int) -> str | None:
    """파일 검증. 문제 있으면 에러 메시지 반환, 정상이면 None"""
    if uploaded_file is None:
        return "파일을 선택해주세요."

    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in allowed_types:
        return f"허용되지 않는 파일 형식입니다. ({', '.join(allowed_types)}만 가능)"

    if uploaded_file.size > max_mb * 1024 * 1024:
        return f"파일 크기가 {max_mb}MB를 초과합니다."

    return None
