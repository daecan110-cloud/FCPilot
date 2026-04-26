"""고객 통합 타임라인 — 상담이력·리마인드·계약·보장분석을 시간순 통합"""
from datetime import date

import streamlit as st

from auth import get_current_user_id
from utils.helpers import esc
from utils.supabase_client import get_supabase_client


def render_timeline(sb, client_id: str, client_name: str):
    """고객의 모든 활동을 시간순으로 통합 표시"""
    fc_id = get_current_user_id()
    events = _collect_events(sb, fc_id, client_id, client_name)

    if not events:
        st.caption("아직 기록된 활동이 없습니다.")
        return

    st.caption(f"전체 {len(events)}건")

    for ev in events:
        _render_event(ev)


@st.cache_data(ttl=30, show_spinner=False)
def _collect_events(_sb, fc_id: str, client_id: str,
                    client_name: str) -> list[dict]:
    """4개 테이블에서 이벤트 수집 → 날짜 역순 정렬 (30초 캐싱)"""
    events = []

    # 1. 상담이력 (contact_logs)
    try:
        logs = (_sb.table("contact_logs")
                .select("created_at,touch_method,memo,proposed_product_ids,next_action,next_date")
                .eq("fc_id", fc_id).eq("client_id", client_id)
                .order("created_at", desc=True)
                .limit(50).execute().data or [])
    except Exception:
        logs = []
    for log in logs:
        events.append({
            "type": "contact",
            "icon": "📝",
            "label": "상담",
            "date": (log.get("created_at") or "")[:10],
            "sort_key": log.get("created_at") or "",
            "title": log.get("touch_method", ""),
            "detail": (log.get("memo") or "")[:100],
            "extra": _contact_extra(log),
        })

    # 2. 리마인드 (fp_reminders)
    try:
        reminders = (_sb.table("fp_reminders")
                     .select("created_at,reminder_date,purpose,memo,status,result,result_memo,completed_at")
                     .eq("fc_id", fc_id).eq("client_id", client_id)
                     .order("created_at", desc=True)
                     .limit(50).execute().data or [])
    except Exception:
        reminders = []
    for r in reminders:
        status = r.get("status", "")
        status_icon = {"pending": "🟡", "completed": "✅",
                       "cancelled": "❌"}.get(status, "🔔")
        events.append({
            "type": "reminder",
            "icon": "🔔",
            "label": "리마인드",
            "date": r.get("reminder_date") or (r.get("created_at") or "")[:10],
            "sort_key": r.get("created_at") or "",
            "title": f"{status_icon} {r.get('purpose', '')}",
            "detail": (r.get("memo") or "")[:100],
            "extra": _reminder_extra(r),
        })

    # 3. 계약정보 (client_contracts)
    try:
        contracts = (_sb.table("client_contracts")
                     .select("created_at,contract_date,company,product_name,monthly_premium,category,main_coverage,riders")
                     .eq("fc_id", fc_id).eq("client_id", client_id)
                     .order("created_at", desc=True)
                     .limit(50).execute().data or [])
    except Exception:
        contracts = []
    for c in contracts:
        premium = c.get("monthly_premium", 0)
        events.append({
            "type": "contract",
            "icon": "📄",
            "label": "계약",
            "date": (c.get("contract_date") or
                     (c.get("created_at") or "")[:10]),
            "sort_key": c.get("created_at") or "",
            "title": f"{c.get('company', '')} — {c.get('product_name', '')}",
            "detail": f"월 {premium:,}원" if premium else "",
            "extra": _contract_extra(c),
        })

    # 4. 보장분석 (analysis_records)
    try:
        analyses = (_sb.table("analysis_records")
                    .select("created_at,client_name,contract_count,result_summary,excel_path")
                    .eq("fc_id", fc_id).ilike("client_name", client_name)
                    .order("created_at", desc=True)
                    .limit(20).execute().data or [])
    except Exception:
        analyses = []
    for a in analyses:
        summary = a.get("result_summary") or {}
        count = a.get("contract_count", 0)
        events.append({
            "type": "analysis",
            "icon": "📊",
            "label": "보장분석",
            "date": (a.get("created_at") or "")[:10],
            "sort_key": a.get("created_at") or "",
            "title": f"계약 {count}건 분석",
            "detail": "",
            "extra": _analysis_extra(a, summary),
        })

    # 날짜 역순 정렬 (최신 먼저)
    events.sort(key=lambda e: e["sort_key"], reverse=True)
    return events


def _render_event(ev: dict):
    """이벤트 카드 1건 렌더링"""
    type_colors = {
        "contact": "#3b82f6",
        "reminder": "#f59e0b",
        "contract": "#10b981",
        "analysis": "#8b5cf6",
    }
    color = type_colors.get(ev["type"], "#6b7280")

    with st.container(border=True):
        col_marker, col_content = st.columns([1, 8])
        with col_marker:
            st.markdown(
                f"<div style='text-align:center;'>"
                f"<span style='font-size:20px;'>{ev['icon']}</span><br>"
                f"<span style='font-size:11px;color:{color};"
                f"font-weight:600;'>{esc(ev['label'])}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_content:
            st.markdown(
                f"<span style='font-size:12px;color:#9ca3af;'>"
                f"{esc(ev['date'])}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**{esc(ev['title'])}**")
            if ev["detail"]:
                st.caption(ev["detail"])
            if ev.get("extra"):
                st.caption(ev["extra"])


# ── 이벤트 타입별 extra 정보 ──


def _contact_extra(log: dict) -> str:
    parts = []
    if log.get("proposed_product_ids"):
        parts.append(f"제안 상품 {len(log['proposed_product_ids'])}건")
    if log.get("next_action"):
        parts.append(f"다음: {log['next_action']}")
    if log.get("next_date"):
        parts.append(f"예정: {log['next_date']}")
    return " · ".join(parts)


def _reminder_extra(r: dict) -> str:
    parts = []
    status = r.get("status", "")
    if status == "completed":
        from services.fp_reminder_service import RESULT_MAP
        result = RESULT_MAP.get(r.get("result", ""), "")
        if result:
            parts.append(f"결과: {result}")
        if r.get("result_memo"):
            parts.append(r["result_memo"][:60])
    if r.get("completed_at"):
        parts.append(f"완료: {r['completed_at'][:10]}")
    return " · ".join(parts)


def _contract_extra(c: dict) -> str:
    parts = []
    cat = c.get("category", "")
    if cat:
        parts.append(cat)
    if c.get("main_coverage"):
        parts.append(c["main_coverage"][:50])
    riders = c.get("riders") or []
    if riders:
        parts.append(f"특약 {len(riders)}건")
    return " · ".join(parts)


def _analysis_extra(a: dict, summary: dict) -> str:
    parts = []
    gender = summary.get("성별", "")
    age = summary.get("나이", "")
    if gender:
        parts.append(gender)
    if age:
        parts.append(f"{age}세")
    if a.get("excel_path"):
        parts.append("엑셀 저장됨")
    return " · ".join(parts)
