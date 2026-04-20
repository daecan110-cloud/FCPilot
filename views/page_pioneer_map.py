"""개척지도 탭 — 매장 등록/지도 표시/팔로업"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import STATUS_LABELS
from utils.kakao_map import pioneer_map_html
from services.geocoding import geocode, search_keyword
from config import CATEGORY_OPTIONS
from utils.helpers import safe_error


def render():
    st.header("개척지도")
    tab_map, tab_followup, tab_register, tab_excel, tab_share, tab_ocr = st.tabs(
        ["지도", "팔로업", "매장 등록", "엑셀 등록", "팀 공유", "간판 OCR"]
    )

    with tab_map:
        _render_map()
    with tab_followup:
        from views.page_pioneer_followup import render_followup
        render_followup()
    with tab_register:
        _render_register()
    with tab_excel:
        from views.page_pioneer_excel import render_excel_import
        render_excel_import()
    with tab_share:
        from views.page_pioneer_share import render_team_share
        render_team_share()
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

    # 공유받은 매장도 함께 표시
    from services.pioneer_share import get_shared_shops
    from views.page_pioneer_share import _get_user_names
    shared_by_owner = get_shared_shops(sb, fc_id)
    user_names = _get_user_names(sb, list(shared_by_owner.keys()))
    shared_all = []
    for oid, owner_shops in shared_by_owner.items():
        name = user_names.get(oid, "팀원")
        for s in owner_shops:
            s["_shared_from"] = name
            shared_all.append(s)

    all_shops = shops + shared_all

    if not all_shops:
        st.info("등록된 매장이 없습니다. '매장 등록' 탭에서 추가하세요.")
        return

    # 내 매장 / 공유 매장 토글
    show_shared = False
    if shared_all:
        show_shared = st.checkbox(f"팀원 공유 매장도 표시 ({len(shared_all)}건)", value=True)

    display_shops = shops + (shared_all if show_shared else [])

    status_filter = st.multiselect(
        "상태 필터",
        options=list(STATUS_LABELS.keys()),
        default=list(STATUS_LABELS.keys()),
        format_func=lambda x: STATUS_LABELS[x],
    )
    filtered = [s for s in display_shops if s.get("status") in status_filter]

    map_col, list_col = st.columns([7, 3])
    with map_col:
        mine_count = len([s for s in filtered if s.get("fc_id") == fc_id])
        shared_count = len(filtered) - mine_count
        caption = f"내 매장 {mine_count}개"
        if shared_count > 0:
            caption += f" + 공유 {shared_count}개"
        st.caption(caption)
        pioneer_map_html(filtered, height=480)
    with list_col:
        st.caption(f"매장 {len(filtered)}곳")
        STATUS_ICON = {"active": "🟡", "visited": "🔵", "contracted": "🟢", "rejected": "🔴"}
        for s in filtered[:30]:
            icon = STATUS_ICON.get(s.get("status", ""), "⚪")
            is_shared = s.get("_shared_from")
            with st.container(border=True):
                label = f"{icon} **{s.get('shop_name', '')}**"
                if is_shared:
                    label += f"  `{is_shared}`"
                st.markdown(label)
                st.caption(s.get("address", ""))
                # 내 매장만 상태 변경 가능
                if not is_shared:
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

    # 카카오 장소 검색
    search_q = st.text_input("장소 검색", placeholder="매장명 또는 주소로 검색")
    if search_q and st.button("검색", key="reg_search"):
        places = search_keyword(search_q)
        if places:
            st.session_state.reg_places = places
        else:
            st.warning("검색 결과가 없습니다.")

    reg_places = st.session_state.get("reg_places", [])
    prefill_name, prefill_addr = "", ""
    prefill_lat, prefill_lng = None, None
    if reg_places:
        options = [f"{p['place_name']} — {p.get('road_address_name') or p.get('address_name', '')}" for p in reg_places]
        selected = st.radio("검색 결과에서 선택", options, key="reg_place_select")
        idx = options.index(selected)
        picked = reg_places[idx]
        prefill_name = picked.get("place_name", "")
        prefill_addr = picked.get("road_address_name") or picked.get("address_name", "")
        prefill_lat = float(picked.get("y", 0))
        prefill_lng = float(picked.get("x", 0))

    with st.form("shop_form"):
        shop_name = st.text_input("매장명 *", value=prefill_name, placeholder="예: 커피빈 강남점")
        address = st.text_input("주소", value=prefill_addr, placeholder="예: 서울시 강남구 역삼동 123")
        category = st.selectbox("업종", CATEGORY_OPTIONS)
        memo = st.text_area("메모", placeholder="특이사항")

        if st.form_submit_button("등록", use_container_width=True, type="primary"):
            if not shop_name:
                st.error("매장명은 필수입니다.")
            else:
                lat, lng = prefill_lat, prefill_lng
                if (not lat or not lng) and address:
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
                    st.session_state.pop("reg_places", None)
                except Exception as e:
                    st.error(safe_error("등록", e))
