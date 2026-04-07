"""개척지도 탭 — 매장 등록/지도 표시/팔로업"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import STATUS_LABELS
from utils.kakao_map import pioneer_map_html
from services.geocoding import geocode
from utils.helpers import safe_error

CATEGORY_OPTIONS = ["음식점", "카페", "미용실/뷰티", "학원/교육", "병원/약국", "편의점/마트", "의류/패션", "사무실/오피스", "기타"]


def render():
    st.header("개척지도")
    tab_map, tab_followup, tab_register, tab_ocr = st.tabs(["지도", "팔로업", "매장 등록", "간판 OCR"])

    with tab_map:
        _render_map()
    with tab_followup:
        from views.page_pioneer_followup import render_followup
        render_followup()
    with tab_register:
        _render_register()
    with tab_ocr:
        from views.page_pioneer_ocr import render_ocr
        render_ocr()


def _render_map():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    try:
        res = sb.table("pioneer_shops").select("*").eq("fc_id", fc_id).order("created_at", desc=True).execute()
        shops = res.data or []
    except Exception as e:
        st.error(safe_error("매장 조회", e))
        return

    if not shops:
        st.info("등록된 매장이 없습니다. '매장 등록' 탭에서 추가하세요.")
        return

    status_filter = st.multiselect(
        "상태 필터",
        options=list(STATUS_LABELS.keys()),
        default=list(STATUS_LABELS.keys()),
        format_func=lambda x: STATUS_LABELS[x],
    )
    filtered = [s for s in shops if s.get("status") in status_filter]

    map_col, list_col = st.columns([7, 3])
    with map_col:
        st.caption(f"전체 {len(shops)}개 | 표시 {len(filtered)}개")
        st.html(pioneer_map_html(filtered, height=480), height=480)
    with list_col:
        st.caption(f"매장 {len(filtered)}곳")
        STATUS_ICON = {"active": "🟡", "visited": "🔵", "contracted": "🟢", "rejected": "🔴"}
        for s in filtered[:20]:
            icon = STATUS_ICON.get(s.get("status", ""), "⚪")
            with st.container(border=True):
                st.markdown(f"{icon} **{s.get('shop_name', '')}**")
                st.caption(s.get("address", ""))
                new_status = st.selectbox(
                    "상태",
                    options=list(STATUS_LABELS.keys()),
                    index=list(STATUS_LABELS.keys()).index(s.get("status", "active")) if s.get("status", "active") in STATUS_LABELS else 0,
                    format_func=lambda x: STATUS_LABELS.get(x, x),
                    key=f"status_{s['id']}",
                    label_visibility="collapsed",
                )
                if new_status != s.get("status"):
                    if st.button("변경", key=f"change_{s['id']}", use_container_width=True):
                        try:
                            sb.table("pioneer_shops").update({"status": new_status}).eq("id", s["id"]).eq("fc_id", fc_id).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(safe_error("변경", e))


def _render_register():
    st.subheader("매장 등록")
    with st.form("shop_form"):
        shop_name = st.text_input("매장명 *", placeholder="예: 커피빈 강남점")
        address = st.text_input("주소", placeholder="예: 서울시 강남구 역삼동 123")
        category = st.selectbox("업종", CATEGORY_OPTIONS)
        memo = st.text_area("메모", placeholder="특이사항")

        if st.form_submit_button("등록", use_container_width=True, type="primary"):
            if not shop_name:
                st.error("매장명은 필수입니다.")
            else:
                lat, lng = None, None
                if address:
                    coords = geocode(address)
                    if coords:
                        lat, lng = coords
                    else:
                        st.warning("주소 좌표 변환 실패. 지도 표시가 안 될 수 있습니다.")
                try:
                    sb = get_supabase_client()
                    sb.table("pioneer_shops").insert({
                        "fc_id": get_current_user_id(),
                        "shop_name": shop_name.strip(),
                        "address": address.strip(),
                        "lat": lat,
                        "lng": lng,
                        "category": category,
                        "memo": memo.strip(),
                    }).execute()
                    st.success(f"'{shop_name}' 등록 완료!")
                except Exception as e:
                    st.error(safe_error("등록", e))


