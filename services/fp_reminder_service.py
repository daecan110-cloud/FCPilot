"""fp_reminders 테이블 CRUD — 홈 탭 / 고객 상세에서 사용"""
from datetime import date, timedelta
import calendar as _cal
import streamlit as st
from utils.supabase_client import get_supabase_client


_PURPOSES = ["초회 상담", "재상담", "설계 제안", "계약 체결", "점검", "기타"]

RESULT_OPTIONS = [
    ("contracted", "계약 체결"),
    ("interest", "관심/긍정"),
    ("revisit", "재방문 필요"),
    ("rejected", "거절"),
    ("no_show", "미방문/부재"),
    ("postponed", "연기"),
    ("other", "기타"),
]

RESULT_MAP = {k: v for k, v in RESULT_OPTIONS}


def purposes() -> list[str]:
    return _PURPOSES


@st.cache_data(ttl=30, show_spinner=False)
def get_bucketed(fc_id: str) -> dict:
    """pending 리마인드를 오늘 / 이번주 / 이번달 / 기간없음 4구역으로 분류 (30초 캐싱, 단일 쿼리)"""
    sb = get_supabase_client()
    today = date.today()
    today_str = str(today)
    week_end = str(today + timedelta(days=7))
    _, last_day = _cal.monthrange(today.year, today.month)
    month_end = f"{today.year}-{today.month:02d}-{last_day:02d}"

    # 단일 쿼리: 모든 pending 리마인드
    try:
        all_pending = (sb.table("fp_reminders")
                       .select("*, clients(name, prospect_grade)")
                       .eq("fc_id", fc_id)
                       .eq("status", "pending")
                       .order("reminder_date")
                       .execute().data or [])
    except Exception:
        all_pending = []

    today_list, this_week, this_month, no_date = [], [], [], []
    for r in all_pending:
        d = r.get("reminder_date")
        if not d:
            no_date.append(r)
        elif d <= today_str:
            today_list.append(r)
        elif d <= week_end:
            this_week.append(r)
        elif d <= month_end:
            this_month.append(r)
        # month_end 이후는 표시 안 함 (기존 동작 유지)

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


def _invalidate_reminder_cache():
    get_bucketed.clear()
    get_past_reminders.clear()


def create_reminder(fc_id: str, client_id: str, reminder_date: str | None,
                    purpose: str, product_ids: list | None, memo: str) -> bool:
    try:
        get_supabase_client().table("fp_reminders").insert({
            "fc_id": fc_id, "client_id": client_id,
            "reminder_date": reminder_date, "purpose": purpose,
            "product_ids": product_ids or None, "memo": memo or None,
            "status": "pending",
        }).execute()
        _invalidate_reminder_cache()
        return True
    except Exception:
        return False


def complete_reminder(fc_id: str, reminder_id: str,
                      result: str = "", result_memo: str = "") -> str | bool:
    """완료 처리. 성공 시 True, 실패 시 에러 메시지 문자열 반환."""
    from datetime import datetime
    data = {
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
    }
    if result:
        data["result"] = result
    if result_memo:
        data["result_memo"] = result_memo
    try:
        get_supabase_client().table("fp_reminders").update(
            data
        ).eq("id", reminder_id).eq("fc_id", fc_id).execute()
        _invalidate_reminder_cache()
        return True
    except Exception as e:
        return str(e)[:120]


def cancel_reminder(fc_id: str, reminder_id: str) -> bool:
    try:
        get_supabase_client().table("fp_reminders").update(
            {"status": "cancelled"}
        ).eq("id", reminder_id).eq("fc_id", fc_id).execute()
        _invalidate_reminder_cache()
        return True
    except Exception:
        return False


def delete_reminder(fc_id: str, reminder_id: str) -> bool:
    """리마인드 물리 삭제 (완료/취소된 건만)"""
    try:
        get_supabase_client().table("fp_reminders").delete().eq(
            "id", reminder_id
        ).eq("fc_id", fc_id).in_(
            "status", ["completed", "cancelled"]
        ).execute()
        _invalidate_reminder_cache()
        return True
    except Exception:
        return False


@st.cache_data(ttl=30, show_spinner=False)
def get_past_reminders(fc_id: str, limit: int = 50) -> list[dict]:
    """완료/취소된 리마인드 목록 (최신 완료순, 30초 캐싱)"""
    try:
        return (get_supabase_client()
                .table("fp_reminders")
                .select("*, clients(name, prospect_grade)")
                .eq("fc_id", fc_id)
                .in_("status", ["completed", "cancelled"])
                .order("completed_at", desc=True)
                .limit(limit)
                .execute().data or [])
    except Exception:
        return []


def update_reminder(fc_id: str, reminder_id: str, reminder_date: str | None,
                    purpose: str, product_ids: list | None, memo: str,
                    result: str = None, result_memo: str = None) -> str | bool:
    """수정. 성공 시 True, 실패 시 에러 메시지 문자열 반환."""
    data = {
        "reminder_date": reminder_date,
        "purpose": purpose,
        "product_ids": product_ids or None,
        "memo": memo or None,
    }
    if result is not None:
        data["result"] = result
    if result_memo is not None:
        data["result_memo"] = result_memo
    try:
        get_supabase_client().table("fp_reminders").update(
            data
        ).eq("id", reminder_id).eq("fc_id", fc_id).execute()
        _invalidate_reminder_cache()
        return True
    except Exception as e:
        return str(e)[:120]
