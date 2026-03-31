"""fp_reminders 테이블 CRUD — 홈 탭 / 고객 상세에서 사용"""
from datetime import date, timedelta
from utils.supabase_client import get_supabase_client


_PURPOSES = ["초회 상담", "재상담", "설계 제안", "계약 체결", "점검", "기타"]


def purposes() -> list[str]:
    return _PURPOSES


def get_bucketed(fc_id: str) -> dict:
    """pending 리마인드를 지연 / 오늘 / 이번주 3구역으로 분류"""
    sb = get_supabase_client()
    today = date.today()
    week_end = str(today + timedelta(days=7))
    today_str = str(today)

    try:
        rows = (sb.table("fp_reminders")
                .select("*, clients(name, prospect_grade)")
                .eq("fc_id", fc_id)
                .eq("status", "pending")
                .lte("reminder_date", week_end)
                .order("reminder_date")
                .execute().data or [])
    except Exception:
        return {"overdue": [], "today": [], "this_week": []}

    overdue, today_list, this_week = [], [], []
    for r in rows:
        d = r.get("reminder_date", "")
        if d < today_str:
            overdue.append(r)
        elif d == today_str:
            today_list.append(r)
        else:
            this_week.append(r)

    return {"overdue": overdue, "today": today_list, "this_week": this_week}


def get_client_reminders(fc_id: str, client_id: str) -> list[dict]:
    """특정 고객의 리마인드 목록 (최신순)"""
    try:
        return (get_supabase_client()
                .table("fp_reminders")
                .select("*")
                .eq("fc_id", fc_id)
                .eq("client_id", client_id)
                .order("reminder_date", desc=True)
                .limit(20)
                .execute().data or [])
    except Exception:
        return []


def create_reminder(fc_id: str, client_id: str, reminder_date: str,
                    purpose: str, product_ids: list | None, memo: str) -> bool:
    try:
        get_supabase_client().table("fp_reminders").insert({
            "fc_id": fc_id, "client_id": client_id,
            "reminder_date": reminder_date, "purpose": purpose,
            "product_ids": product_ids or None, "memo": memo or None,
            "status": "pending",
        }).execute()
        return True
    except Exception:
        return False


def complete_reminder(fc_id: str, reminder_id: str) -> bool:
    try:
        from datetime import datetime
        get_supabase_client().table("fp_reminders").update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
        }).eq("id", reminder_id).eq("fc_id", fc_id).execute()
        return True
    except Exception:
        return False


def cancel_reminder(fc_id: str, reminder_id: str) -> bool:
    try:
        get_supabase_client().table("fp_reminders").update(
            {"status": "cancelled"}
        ).eq("id", reminder_id).eq("fc_id", fc_id).execute()
        return True
    except Exception:
        return False


def update_reminder(fc_id: str, reminder_id: str, reminder_date: str,
                    purpose: str, product_ids: list | None, memo: str) -> bool:
    try:
        get_supabase_client().table("fp_reminders").update({
            "reminder_date": reminder_date,
            "purpose": purpose,
            "product_ids": product_ids or None,
            "memo": memo or None,
        }).eq("id", reminder_id).eq("fc_id", fc_id).execute()
        return True
    except Exception:
        return False
