"""상담 메모 텍스트 → 날짜별 contact_log 항목 파싱

사용 예시 (앞으로 모든 상담 메모 저장 시 이 모듈 통해서 저장):

    from services.contact_log_parser import parse_memo_to_logs, save_contact_logs

    logs = parse_memo_to_logs(memo_text, fallback_date=date.today())
    save_contact_logs(client_id, fc_id, logs)

날짜 형식 지원:
    - YY/M/D  (예: 26/1/5)
    - YY/MM/DD (예: 26/01/05)
    - 날짜 없는 첫 줄 → fallback_date 사용
"""
import re
from datetime import date, datetime
from typing import Optional

from utils.supabase_client import get_supabase_client

# YY/M/D 또는 YY/MM/DD — 줄 맨 앞에 등장하는 패턴
_DATE_LINE_RE = re.compile(r"^\s*(\d{2})/(\d{1,2})/(\d{1,2})\s*(.*)")


def parse_memo_to_logs(
    text: str,
    fallback_date: Optional[date] = None,
    touch_method: str = "",
) -> list[dict]:
    """상담 메모 텍스트를 날짜별 로그 항목 목록으로 변환.

    Args:
        text: 상담 메모 원문 (여러 날짜가 섞인 자유 형식)
        fallback_date: 날짜 표시 없는 첫 항목에 사용할 기본 날짜
        touch_method: 터치 방식 (콜/문자/방문 등), 모든 항목에 공통 적용

    Returns:
        [{"contact_date": date | None, "memo": str, "touch_method": str}, ...]
    """
    if not text or not text.strip():
        return []

    entries: list[dict] = []
    current_date: Optional[date] = fallback_date
    current_lines: list[str] = []

    for line in text.splitlines():
        m = _DATE_LINE_RE.match(line)
        if m:
            # 이전 버퍼를 항목으로 확정
            if current_lines:
                entries.append(_make_entry(current_date, current_lines, touch_method))
            # 새 날짜 파싱
            yy, mo, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                current_date = date(2000 + yy, mo, dd)
            except ValueError:
                current_date = fallback_date
            rest = m.group(4).strip()
            current_lines = [rest] if rest else []
        else:
            stripped = line.strip()
            if stripped:
                current_lines.append(stripped)

    # 마지막 버퍼
    if current_lines:
        entries.append(_make_entry(current_date, current_lines, touch_method))

    return [e for e in entries if e["memo"]]


def save_contact_logs(
    client_id: str,
    fc_id: str,
    logs: list[dict],
) -> tuple[int, list[str]]:
    """파싱된 로그 목록을 contact_logs 테이블에 저장.

    Args:
        client_id: clients 테이블 UUID
        fc_id: FC 사용자 UUID
        logs: parse_memo_to_logs() 반환값

    Returns:
        (저장 건수, 에러 목록)
    """
    if not logs:
        return 0, []

    sb = get_supabase_client()
    success = 0
    errors: list[str] = []

    for log in logs:
        try:
            row: dict = {
                "client_id": client_id,
                "fc_id": fc_id,
                "memo": log["memo"],
                "touch_method": log.get("touch_method", ""),
            }
            contact_date = log.get("contact_date")
            if contact_date:
                # created_at을 상담 날짜로 덮어씀 (이력 정확도 유지)
                row["created_at"] = datetime.combine(
                    contact_date, datetime.min.time()
                ).isoformat()
            sb.table("contact_logs").insert(row).execute()
            success += 1
        except Exception as e:
            errors.append(str(e))

    return success, errors


# ── 내부 유틸 ────────────────────────────────────────────

def _make_entry(
    contact_date: Optional[date],
    lines: list[str],
    touch_method: str,
) -> dict:
    return {
        "contact_date": contact_date,
        "memo": "\n".join(lines).strip(),
        "touch_method": touch_method,
    }
