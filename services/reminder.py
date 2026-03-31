"""리마인드 대상 조회 — 발송 트리거는 Sprint 4"""
from datetime import date, timedelta
from utils.supabase_client import get_supabase_client


def get_contact_reminders(fc_id: str) -> list[dict]:
    """다음 상담 예정일이 오늘이거나 지난 고객 목록"""
    sb = get_supabase_client()
    today = str(date.today())

    try:
        res = sb.table("contact_logs").select(
            "*, fp_clients(name, prospect_grade)"
        ).eq("fc_id", fc_id).lte("next_date", today).not_.is_("next_date", "null").order("next_date").execute()
        logs = res.data or []
    except Exception:
        return []

    reminders = []
    seen_clients = set()

    for log in logs:
        client = log.get("clients", {}) or {}
        client_id = log.get("client_id", "")
        if client_id in seen_clients:
            continue
        seen_clients.add(client_id)

        next_date = log.get("next_date", "")
        overdue = next_date < today if next_date else False

        reminders.append({
            "client_id": client_id,
            "client_name": client.get("name", ""),
            "grade": client.get("prospect_grade", ""),
            "next_date": next_date,
            "next_action": log.get("next_action", ""),
            "overdue": overdue,
        })

    return reminders


def get_pioneer_reminders(fc_id: str) -> list[dict]:
    """팔로업 기한이 지난 개척 매장 목록"""
    from services.followup import get_followup_list
    followups = get_followup_list(fc_id)
    return [f for f in followups if f.get("overdue")]


def get_all_reminders(fc_id: str) -> dict:
    """전체 리마인드 요약"""
    contacts = get_contact_reminders(fc_id)
    pioneers = get_pioneer_reminders(fc_id)
    return {
        "contacts": contacts,
        "pioneers": pioneers,
        "total": len(contacts) + len(pioneers),
    }
