"""fp_reminders 테이블 CRUD — 홈 탭 / 고객 상세에서 사용"""
from datetime import date, timedelta
import calendar as _cal
from utils.supabase_client import get_supabase_client


_PURPOSES = ["초회 상담", "재상담", "설계 제안", "계약 체결", "점검", "기타"]


def purposes() -> list[str]:
    return _PURPOSES


def get_bucketed(fc_id: str) -> dict:
    """pending 리마인드를 오늘 / 이번주 / 이번달 / 기간없음 4구역으로 분류"""
    sb = get_supabase_client()
    today = date.today()
    today_str = str(today)
    week_end = str(today + timedelta(days=7))
    _, last_day = _cal.monthrange(today.year, today.month)
    month_end = f"{today.year}-{today.month:02d}-{last_day:02d}"

    # 날짜 있는 pending (이번달 이내 + 지연 포함)
    try:
        dated = (sb.table("fp_reminders")
                 .select("*, clients(name, prospect_grade)")
                 .eq("fc_id", fc_id)
                 .eq("status", "pending")
                 .not_.is_("reminder_date", "null")
                 .lte("reminder_date", month_end)
                 .order("reminder_date")
                 .execute().data or [])
    except Exception:
        dated = []

    # 날짜 없는 pending
    try:
        no_date = (sb.table("fp_reminders")
                   .select("*, clients(name, prospect_grade)")
                   .eq("fc_id", fc_id)
                   .eq("status", "pending")
                   .is_("reminder_date", "null")
                   .execute().data or [])
    except Exception:
        no_date = []

    today_list, this_week, this_month = [], [], []
    for r in dated:
        d = r.get("reminder_date", "")
        if d <= today_str:          # 오늘 + 지연
            today_list.append(r)
        elif d <= week_end:         # 이번 주
            this_week.append(r)
        else:                       # 이번 달 (주 이후)
            this_month.append(r)

    return {
        "today": today_list,
        "this_week": this_week,
        "this_month": this_month,
        "no_date": no_date,
    }


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


def create_reminder(fc_id: str, client_id: str, reminder_date: str | None,
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


def update_reminder(fc_id: str, reminder_id: str, reminder_date: str | None,
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
