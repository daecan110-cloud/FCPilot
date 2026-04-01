"""FCPilot 통계 대시보드"""
from datetime import date, timedelta
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client

_GRADE_ORDER = ["VIP", "S", "A", "B", "C", "D"]
_GRADE_ICON = {"VIP": "🟣", "S": "🟢", "A": "🔴", "B": "🟠", "C": "🔵", "D": "⚫"}


def render():
    st.header("통계 대시보드")
    fc_id = get_current_user_id()
    if not fc_id:
        st.warning("로그인이 필요합니다.")
        return

    period = st.radio("기간", ["오늘", "최근 3일", "최근 7일", "최근 30일", "최근 3개월", "전체"],
                      horizontal=True, label_visibility="collapsed")
    since = _since(period)
    days = {"오늘": 1, "최근 3일": 3, "최근 7일": 7, "최근 30일": 30, "최근 3개월": 90}.get(period)

    sb = get_supabase_client()
    _render_crm(sb, fc_id, since, days, period)
    st.divider()
    _render_distribution(sb, fc_id)
    st.divider()
    _render_pioneer(sb, fc_id, since)
    st.divider()
    _render_analysis(sb, fc_id, since)


_PERIOD_DAYS = {"오늘": 0, "최근 3일": 3, "최근 7일": 7, "최근 30일": 30, "최근 3개월": 90}


def _since(period: str) -> str | None:
    if period not in _PERIOD_DAYS:
        return None
    return str(date.today() - timedelta(days=_PERIOD_DAYS[period]))


def _q(sb, table: str, fields: str, fc_id: str, since: str | None):
    q = sb.table(table).select(fields).eq("fc_id", fc_id)
    return (q.gte("created_at", since) if since else q)


def _render_crm(sb, fc_id: str, since, days, period: str):
    st.subheader("고객 관리")
    try:
        total_cnt = sb.table("clients").select("id", count="exact").eq("fc_id", fc_id).execute().count or 0
    except Exception:
        total_cnt = 0
    try:
        new_clients = _q(sb, "clients", "prospect_grade", fc_id, since).execute().data or []
    except Exception:
        new_clients = []
    try:
        logs = _q(sb, "contact_logs", "touch_method", fc_id, since).execute().data or []
    except Exception:
        logs = []

    total_logs = len(logs)
    if days and days > 1:
        contact_str = f"{period}: 총 {total_logs}건 (일 평균 {round(total_logs/days,1)}건)"
    elif days == 1:
        contact_str = f"오늘: 총 {total_logs}건"
    else:
        contact_str = f"전체: 총 {total_logs}건"

    c1, c2, c3 = st.columns(3)
    c1.metric("전체 고객", f"{total_cnt}명")
    c2.metric("신규 등록", f"{period} {len(new_clients)}명" if days else f"전체 {len(new_clients)}명")
    c3.metric("상담 기록", contact_str)

    # 등급 카드 6개 — 기간 내 신규 등록 고객 기준
    grades = {g: 0 for g in _GRADE_ORDER}
    for c in new_clients:
        g = c.get("prospect_grade") or "C"
        if g in grades:
            grades[g] += 1
    period_label = period if days else "전체"
    st.caption(f"신규 등록 등급 분포 ({period_label} 기준)")
    cols = st.columns(6)
    for i, g in enumerate(_GRADE_ORDER):
        cols[i].metric(f"{_GRADE_ICON.get(g,'')} {g}등급", f"{grades[g]}명")

    if logs:
        methods: dict = {}
        for log in logs:
            m = log.get("touch_method") or "기타"
            methods[m] = methods.get(m, 0) + 1
        st.caption("터치방식: " + " | ".join(f"{m}: {v}건" for m, v in sorted(methods.items(), key=lambda x: -x[1])))


def _render_distribution(sb, fc_id: str):
    st.subheader("고객 분포 (전체)")
    view_by = st.selectbox("보기 기준", ["등급별", "유입경로별", "나이대별", "지역별"],
                           key="stats_dist_by", label_visibility="collapsed")
    try:
        clients = (sb.table("clients")
                   .select("prospect_grade,db_source,age_group,address")
                   .eq("fc_id", fc_id).execute().data or [])
    except Exception:
        clients = []
    if not clients:
        st.caption("해당 기간 고객 데이터가 없습니다.")
        return

    if view_by == "등급별":
        dist = {g: 0 for g in _GRADE_ORDER}
        for c in clients:
            g = c.get("prospect_grade") or "C"
            if g in dist:
                dist[g] += 1
        _dist_cards(dist, _GRADE_ORDER, lambda k: f"{_GRADE_ICON.get(k,'')} {k}등급")

    elif view_by == "유입경로별":
        dist: dict = {}
        for c in clients:
            k = c.get("db_source") or "미지정"
            dist[k] = dist.get(k, 0) + 1
        _dist_cards(dist, sorted(dist, key=lambda k: -dist[k]), lambda k: k)

    elif view_by == "나이대별":
        _AGE_ORDER = ["10대", "20대", "30대", "40대", "50대", "60대 이상", "기타"]
        dist: dict = {}
        for c in clients:
            ag = c.get("age_group") or "기타"
            if ag.startswith("60"):
                ag = "60대 이상"
            dist[ag] = dist.get(ag, 0) + 1
        keys = [k for k in _AGE_ORDER if k in dist] + [k for k in dist if k not in _AGE_ORDER]
        _dist_cards(dist, keys, lambda k: k)

    elif view_by == "지역별":
        dist: dict = {}
        for c in clients:
            addr = (c.get("address") or "").strip()
            token = addr.split()[0] if addr else ""
            region = token if (len(token) >= 2 and token[-1] in "시군구동") else "기타"
            dist[region] = dist.get(region, 0) + 1
        _dist_cards(dist, sorted(dist, key=lambda k: -dist[k]), lambda k: k)


def _dist_cards(dist: dict, keys: list, label_fn):
    total = sum(dist.values())
    items = [(k, dist[k]) for k in keys if k in dist]
    for row_start in range(0, len(items), 4):
        row = items[row_start: row_start + 4]
        cols = st.columns(4)
        for i, (k, cnt) in enumerate(row):
            cols[i].metric(label_fn(k), f"{cnt}명", f"{round(cnt/total*100,1)}%" if total else "0%")


def _render_pioneer(sb, fc_id: str, since):
    st.subheader("개척 영업")
    try:
        shops = sb.table("pioneer_shops").select("status").eq("fc_id", fc_id).execute().data or []
    except Exception:
        shops = []
    try:
        visits = _q(sb, "pioneer_visits", "result", fc_id, since).execute().data or []
    except Exception:
        visits = []

    contracted = sum(1 for s in shops if s.get("status") == "contracted")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("등록 매장", f"{len(shops)}곳")
    c2.metric("방문 기록", f"{len(visits)}건")
    c3.metric("계약 성사", f"{contracted}곳")
    c4.metric("계약 전환율", f"{round(contracted/max(len(shops),1)*100,1)}%")

    if shops:
        labels = {"active": "등록", "visited": "방문", "contracted": "계약", "rejected": "거절"}
        statuses: dict = {}
        for s in shops:
            k = s.get("status", "active")
            statuses[k] = statuses.get(k, 0) + 1
        st.caption("매장 현황: " + " | ".join(f"{labels.get(k,k)}: {v}곳" for k, v in statuses.items()))


def _render_analysis(sb, fc_id: str, since):
    st.subheader("보장분석")
    try:
        aq = sb.table("analysis_records").select("id", count="exact").eq("fc_id", fc_id)
        a_cnt = (aq.gte("created_at", since) if since else aq).execute().count or 0
    except Exception:
        a_cnt = 0
    try:
        yq = sb.table("yakwan_records").select("id", count="exact").eq("fc_id", fc_id)
        y_cnt = (yq.gte("created_at", since) if since else yq).execute().count or 0
    except Exception:
        y_cnt = 0
    c1, c2 = st.columns(2)
    c1.metric("보장분석 실행", f"{a_cnt}건")
    c2.metric("약관분석 실행", f"{y_cnt}건")
