"""공통 유틸리티"""


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
