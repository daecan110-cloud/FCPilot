"""동선 기록 — 이전 기록 탭"""
from datetime import date, timedelta

import streamlit as st
import streamlit.components.v1 as components

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import VISIT_RESULT_LABELS
from utils.kakao_map import route_map_html
from services.geocoding import geocode
from utils.helpers import safe_error


def render_history():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    try:
        since90 = str(date.today() - timedelta(days=90))
        date_rows = (sb.table("pioneer_visits").select("visit_date")
                     .eq("fc_id", fc_id).gte("visit_date", since90)
                     .order("visit_date", desc=True).execute().data or [])
        visited_dates = sorted({r["visit_date"] for r in date_rows}, reverse=True)
    except Exception:
        visited_dates = []

    if visited_dates:
        months: dict = {}
        for d in visited_dates:
            m = d[:7]
            months.setdefault(m, []).append(d[5:])
        summary = " | ".join(
            f"{m}: {', '.join(days)}" for m, days in months.items()
        )
        st.caption(f"방문 기록 있는 날  {summary}")
    else:
        st.caption("최근 90일 방문 기록이 없습니다.")

    target_date = st.date_input("날짜 선택", value=date.today())

    try:
        res = sb.table("pioneer_visits").select(
            "*, pioneer_shops(shop_name, lat, lng, address)"
        ).eq("fc_id", fc_id).eq("visit_date", str(target_date)).order("created_at").execute()
        visits = res.data or []
    except Exception as e:
        st.error(safe_error("조회", e))
        return

    if not visits:
        st.info(f"{target_date} 방문 기록이 없습니다.")
        return

    st.subheader(f"{target_date} 동선 ({len(visits)}건)")

    visits_for_map = []
    no_coords = []
    for i, v in enumerate(visits, 1):
        shop = v.get("pioneer_shops", {}) or {}
        entry = {
            "lat": shop.get("lat"),
            "lng": shop.get("lng"),
            "shop_name": shop.get("shop_name", ""),
            "address": shop.get("address", ""),
            "visit_date": v.get("visit_date", ""),
            "result": v.get("result", ""),
            "memo": (v.get("memo") or ""),
            "order": i,
        }
        visits_for_map.append(entry)
        if not shop.get("lat") or not shop.get("lng"):
            no_coords.append(shop.get("shop_name", ""))

    if no_coords:
        with st.expander(f"지도 미표시 매장 {len(no_coords)}개 — 좌표 없음"):
            for name in no_coords:
                st.caption(f"• {name}")
            if st.button("좌표 재조회", key="regeo_hist"):
                _regeocode_missing(sb, fc_id)

    components.html(route_map_html(visits_for_map, height=420), height=420)

    for v in visits_for_map:
        result_text = VISIT_RESULT_LABELS.get(v["result"], "")
        loc = "" if (v["lat"] and v["lng"]) else " 위치 없음"
        st.markdown(
            f"**#{v['order']}** {v['shop_name']}{loc} — {result_text}"
            + (f" | {v['memo']}" if v["memo"] else "")
        )


def _regeocode_missing(sb, fc_id: str):
    """주소는 있으나 좌표가 없는 매장을 일괄 재조회"""
    try:
        shops = (sb.table("pioneer_shops").select("id, shop_name, address")
                 .eq("fc_id", fc_id).is_("lat", "null").execute().data or [])
    except Exception as e:
        st.error(safe_error("조회", e))
        return
    if not shops:
        st.info("좌표 없는 매장이 없습니다.")
        return
    ok, fail = 0, 0
    for s in shops:
        addr = s.get("address", "")
        if not addr:
            fail += 1
            continue
        coords = geocode(addr)
        if coords:
            try:
                sb.table("pioneer_shops").update({"lat": coords[0], "lng": coords[1]}).eq("id", s["id"]).eq("fc_id", fc_id).execute()
                ok += 1
            except Exception:
                fail += 1
        else:
            fail += 1
    st.success(f"좌표 재조회 완료: 성공 {ok}개 / 실패 {fail}개")
    st.rerun()
