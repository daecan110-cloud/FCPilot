"""동선 기록 탭 — 일별 방문 기록 + 동선 지도"""
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import VISIT_RESULT_LABELS
from utils.naver_map import route_map_html
from services.geocoding import geocode


def render():
    st.header("동선 기록")
    st.caption("오늘 방문한 매장을 순서대로 기록하면 동선 지도가 생성됩니다.")

    tab_record, tab_history = st.tabs(["오늘 기록", "이전 기록"])

    with tab_record:
        _render_today()
    with tab_history:
        _render_history()


def _render_today():
    sb = get_supabase_client()
    fc_id = get_current_user_id()
    today = str(date.today())

    # 오늘 방문 기록 조회
    try:
        res = sb.table("pioneer_visits").select(
            "*, pioneer_shops(shop_name, lat, lng, address)"
        ).eq("fc_id", fc_id).eq("visit_date", today).order("created_at").execute()
        today_visits = res.data or []
    except Exception as e:
        st.error(f"조회 실패: {e}")
        return

    # 매장 목록 (방문 기록 추가용)
    try:
        shops_res = sb.table("pioneer_shops").select("id, shop_name").eq("fc_id", fc_id).order("shop_name").execute()
        shops = shops_res.data or []
    except Exception as e:
        st.error(f"매장 조회 실패: {e}")
        return

    # 새 방문 기록 추가
    st.subheader("방문 추가")
    if not shops:
        st.info("개척지도 탭에서 매장을 먼저 등록하세요.")
        return

    with st.form("visit_form"):
        shop_options = {s["id"]: s["shop_name"] for s in shops}
        shop_id = st.selectbox(
            "매장 선택",
            options=list(shop_options.keys()),
            format_func=lambda x: shop_options[x],
        )
        result = st.selectbox(
            "방문 결과",
            options=["", "interest", "rejected", "revisit", "contracted"],
            format_func=lambda x: VISIT_RESULT_LABELS.get(x, x),
        )
        memo = st.text_input("메모", placeholder="간단한 메모")

        if st.form_submit_button("기록 추가", use_container_width=True, type="primary"):
            try:
                sb.table("pioneer_visits").insert({
                    "fc_id": fc_id,
                    "shop_id": shop_id,
                    "visit_date": today,
                    "result": result,
                    "memo": memo.strip(),
                }).execute()

                # 매장 상태 업데이트
                if result == "contracted":
                    sb.table("pioneer_shops").update({"status": "contracted"}).eq("id", shop_id).execute()
                elif result:
                    sb.table("pioneer_shops").update({"status": "visited"}).eq("id", shop_id).execute()

                st.success("방문 기록이 추가되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

    # 오늘 동선 표시
    if today_visits:
        st.divider()
        st.subheader(f"오늘 동선 ({len(today_visits)}건)")

        visits_for_map = []
        no_coords = []
        for i, v in enumerate(today_visits, 1):
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
            st.warning(f"지도 미표시 매장 ({len(no_coords)}개): {', '.join(no_coords)} — 개척지도 탭에서 주소를 확인하세요.")
            if st.button("📍 좌표 없는 매장 재조회", key="regeo_today"):
                _regeocode_missing(sb, fc_id)

        m = create_route_map(visits_for_map)
        components.html(route_map_html(visits_for_map, height=420), height=420)

        for v in visits_for_map:
            result_text = VISIT_RESULT_LABELS.get(v["result"], "")
            loc = "" if (v["lat"] and v["lng"]) else " 📍위치 없음"
            st.markdown(
                f"**#{v['order']}** {v['shop_name']}{loc} — {result_text}"
                + (f" | {v['memo']}" if v["memo"] else "")
            )


def _render_history():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    # 최근 90일 방문 기록 있는 날짜 목록
    try:
        from datetime import timedelta
        since90 = str(date.today() - timedelta(days=90))
        date_rows = (sb.table("pioneer_visits").select("visit_date")
                     .eq("fc_id", fc_id).gte("visit_date", since90)
                     .order("visit_date", desc=True).execute().data or [])
        visited_dates = sorted({r["visit_date"] for r in date_rows}, reverse=True)
    except Exception:
        visited_dates = []

    if visited_dates:
        # 월별 그룹핑
        months: dict = {}
        for d in visited_dates:
            m = d[:7]  # "2026-03"
            months.setdefault(m, []).append(d[5:])  # "03-31"
        summary = " | ".join(
            f"{m}: {', '.join(days)}" for m, days in months.items()
        )
        st.caption(f"📅 방문 기록 있는 날  {summary}")
    else:
        st.caption("최근 90일 방문 기록이 없습니다.")

    target_date = st.date_input("날짜 선택", value=date.today())

    try:
        res = sb.table("pioneer_visits").select(
            "*, pioneer_shops(shop_name, lat, lng, address)"
        ).eq("fc_id", fc_id).eq("visit_date", str(target_date)).order("created_at").execute()
        visits = res.data or []
    except Exception as e:
        st.error(f"조회 실패: {e}")
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
        with st.expander(f"⚠️ 지도 미표시 매장 {len(no_coords)}개 — 좌표 없음"):
            for name in no_coords:
                st.caption(f"• {name}")
            if st.button("📍 좌표 재조회", key="regeo_hist"):
                _regeocode_missing(sb, fc_id)

    m = create_route_map(visits_for_map)
    components.html(route_map_html(visits_for_map, height=420), height=420)

    for v in visits_for_map:
        result_text = VISIT_RESULT_LABELS.get(v["result"], "")
        loc = "" if (v["lat"] and v["lng"]) else " 📍위치 없음"
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
        st.error(f"조회 실패: {e}")
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
                sb.table("pioneer_shops").update({"lat": coords[0], "lng": coords[1]}).eq("id", s["id"]).execute()
                ok += 1
            except Exception:
                fail += 1
        else:
            fail += 1
    st.success(f"좌표 재조회 완료: 성공 {ok}개 / 실패 {fail}개")
    st.rerun()
