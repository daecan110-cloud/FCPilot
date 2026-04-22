"""팔로업 상태머신 — 개척 매장 후속 관리"""
from datetime import date, timedelta
from utils.supabase_client import get_supabase_client


# 방문 결과별 다음 액션
FOLLOWUP_RULES = {
    "interest": {"days": 3, "action": "재방문 (관심 고객 — 3일 내)"},
    "revisit": {"days": 7, "action": "재방문 (예정 — 1주 내)"},
    "rejected": {"days": 30, "action": "재시도 (1개월 후)"},
    "contracted": {"days": 0, "action": "계약 완료 — 팔로업 불필요"},
}


def get_followup_list(fc_id: str) -> list[dict]:
    """팔로업 대상 매장 목록 (기한 내 재방문 필요한 곳)"""
    sb = get_supabase_client()

    # 전체 매장 + 최근 방문 기록 조회
    try:
        shops_res = sb.table("pioneer_shops").select("*").eq("fc_id", fc_id).neq("status", "contracted").execute()
        shops = shops_res.data or []
    except Exception:
        return []

    followups = []
    today = date.today()

    # 전체 방문 기록을 1회 벌크 조회 → Python에서 매장별 매칭
    try:
        all_visits = (sb.table("pioneer_visits")
                      .select("*")
                      .eq("fc_id", fc_id)
                      .order("created_at", desc=True)
                      .execute().data or [])
    except Exception:
        all_visits = []

    # shop_id별 최신 방문 1건만 매핑
    latest_by_shop: dict = {}
    for v in all_visits:
        sid = v.get("shop_id")
        if sid and sid not in latest_by_shop:
            latest_by_shop[sid] = v

    for shop in shops:
        last_visit = latest_by_shop.get(shop["id"])

        if not last_visit:
            # 방문 기록 없음 → 첫 방문 필요
            followups.append({
                "shop": shop,
                "last_visit": None,
                "action": "첫 방문 필요",
                "due_date": None,
                "overdue": True,
                "priority": "high",
            })
            continue

        result = last_visit.get("result", "")
        if result == "contracted":
            continue

        rule = FOLLOWUP_RULES.get(result, {"days": 14, "action": "상태 확인 (2주 후)"})
        if rule["days"] == 0:
            continue

        vd = last_visit.get("visit_date")
        if not vd:
            continue
        visit_date = date.fromisoformat(vd)
        due = visit_date + timedelta(days=rule["days"])
        overdue = today >= due
        days_left = (due - today).days

        priority = "high" if overdue else ("medium" if days_left <= 3 else "low")

        followups.append({
            "shop": shop,
            "last_visit": last_visit,
            "action": rule["action"],
            "due_date": str(due),
            "days_left": days_left,
            "overdue": overdue,
            "priority": priority,
        })

    # 우선순위 정렬: high → medium → low
    order = {"high": 0, "medium": 1, "low": 2}
    followups.sort(key=lambda x: (order.get(x["priority"], 3), x.get("days_left", 999)))
    return followups
