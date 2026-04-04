"""동선 기록 탭 — 일별 방문 기록 + 동선 지도"""
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import VISIT_RESULT_LABELS
from utils.kakao_map import route_map_html
from utils.helpers import safe_error


def render():
    st.header("동선 기록")
    st.caption("오늘 방문한 매장을 순서대로 기록하면 동선 지도가 생성됩니다.")

    tab_record, tab_history = st.tabs(["오늘 기록", "이전 기록"])

    with tab_record:
        _render_today()
    with tab_history:
        from views.page_pioneer_history import render_history
        render_history()


def _render_today():
    sb = get_supabase_client()
    fc_id = get_current_user_id()
    today = str(date.today())

    try:
        res = sb.table("pioneer_visits").select(
            "*, pioneer_shops(shop_name, lat, lng, address)"
        ).eq("fc_id", fc_id).eq("visit_date", today).order("created_at").execute()
        today_visits = res.data or []
    except Exception as e:
        st.error(safe_error("조회", e))
        return

    try:
        shops_res = sb.table("pioneer_shops").select("id, shop_name").eq("fc_id", fc_id).order("shop_name").execute()
        shops = shops_res.data or []
    except Exception as e:
        st.error(safe_error("매장 조회", e))
        return

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

                if result == "contracted":
                    sb.table("pioneer_shops").update({"status": "contracted"}).eq("id", shop_id).eq("fc_id", fc_id).execute()
                elif result:
                    sb.table("pioneer_shops").update({"status": "visited"}).eq("id", shop_id).eq("fc_id", fc_id).execute()

                st.success("방문 기록이 추가되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(safe_error("저장", e))

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

        components.html(route_map_html(visits_for_map, height=420), height=420)

        for v in visits_for_map:
            result_text = VISIT_RESULT_LABELS.get(v["result"], "")
            loc = "" if (v["lat"] and v["lng"]) else " 위치 없음"
            st.markdown(
                f"**#{v['order']}** {v['shop_name']}{loc} — {result_text}"
                + (f" | {v['memo']}" if v["memo"] else "")
            )
