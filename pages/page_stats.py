"""FCPilot 통계 대시보드"""
from datetime import date, timedelta

import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client


def render():
    st.header("통계 대시보드")

    fc_id = get_current_user_id()
    if not fc_id:
        st.warning("로그인이 필요합니다.")
        return

    period = st.radio(
        "기간", ["최근 7일", "최근 30일", "전체"],
        horizontal=True, label_visibility="collapsed",
    )
    since = _period_to_date(period)

    sb = get_supabase_client()
    _render_crm_stats(sb, fc_id, since)
    st.divider()
    _render_pioneer_stats(sb, fc_id, since)
    st.divider()
    _render_analysis_stats(sb, fc_id, since)


def _period_to_date(period: str) -> str | None:
    if period == "최근 7일":
        return str(date.today() - timedelta(days=7))
    if period == "최근 30일":
        return str(date.today() - timedelta(days=30))
    return None


def _render_crm_stats(sb, fc_id: str, since: str | None):
    """고객/상담 통계"""
    st.subheader("고객 관리")

    try:
        q = sb.table("fp_clients").select("id, prospect_grade").eq("fc_id", fc_id)
        if since:
            q = q.gte("created_at", since)
        clients = q.execute().data or []
    except Exception:
        clients = []

    try:
        q = sb.table("fp_contact_logs").select("id, touch_method").eq("fc_id", fc_id)
        if since:
            q = q.gte("created_at", since)
        logs = q.execute().data or []
    except Exception:
        logs = []

    c1, c2, c3 = st.columns(3)
    c1.metric("등록 고객", f"{len(clients)}명")
    c2.metric("상담 기록", f"{len(logs)}건")
    avg = round(len(logs) / max(len(clients), 1), 1)
    c3.metric("인당 평균 상담", f"{avg}회")

    # 등급별 분포
    if clients:
        grades = {}
        for c in clients:
            g = c.get("prospect_grade", "미지정") or "미지정"
            grades[g] = grades.get(g, 0) + 1
        cols = st.columns(len(grades))
        for i, (grade, count) in enumerate(sorted(grades.items())):
            cols[i % len(cols)].metric(f"{grade}등급", f"{count}명")

    # 터치방식별 분포
    if logs:
        methods = {}
        for log in logs:
            m = log.get("touch_method", "기타") or "기타"
            methods[m] = methods.get(m, 0) + 1
        st.caption("터치방식 분포: " + " | ".join(
            f"{m}: {cnt}건" for m, cnt in sorted(methods.items(), key=lambda x: -x[1])
        ))


def _render_pioneer_stats(sb, fc_id: str, since: str | None):
    """개척 통계"""
    st.subheader("개척 영업")

    try:
        shops = sb.table("fp_pioneer_shops").select(
            "id, status"
        ).eq("fc_id", fc_id).execute().data or []
    except Exception:
        shops = []

    try:
        q = sb.table("fp_pioneer_visits").select("id, result").eq("fc_id", fc_id)
        if since:
            q = q.gte("created_at", since)
        visits = q.execute().data or []
    except Exception:
        visits = []

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("등록 매장", f"{len(shops)}곳")
    c2.metric("방문 기록", f"{len(visits)}건")

    contracted = sum(1 for s in shops if s.get("status") == "contracted")
    c3.metric("계약 성사", f"{contracted}곳")

    rate = round(contracted / max(len(shops), 1) * 100, 1)
    c4.metric("계약 전환율", f"{rate}%")

    # 매장 상태별 분포
    if shops:
        statuses = {}
        labels = {"active": "등록", "visited": "방문", "contracted": "계약", "rejected": "거절"}
        for s in shops:
            status = s.get("status", "active")
            statuses[status] = statuses.get(status, 0) + 1
        st.caption("매장 현황: " + " | ".join(
            f"{labels.get(k, k)}: {v}곳" for k, v in statuses.items()
        ))


def _render_analysis_stats(sb, fc_id: str, since: str | None):
    """보장분석 통계"""
    st.subheader("보장분석")

    try:
        q = sb.table("fp_analysis_records").select("id").eq("fc_id", fc_id)
        if since:
            q = q.gte("created_at", since)
        analyses = q.execute().data or []
    except Exception:
        analyses = []

    try:
        q = sb.table("fp_yakwan_records").select("id").eq("fc_id", fc_id)
        if since:
            q = q.gte("created_at", since)
        yakwans = q.execute().data or []
    except Exception:
        yakwans = []

    c1, c2 = st.columns(2)
    c1.metric("보장분석 실행", f"{len(analyses)}건")
    c2.metric("약관분석 실행", f"{len(yakwans)}건")
