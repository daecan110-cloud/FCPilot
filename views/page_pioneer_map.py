"""개척지도 탭 — 매장 등록/지도 표시/팔로업"""
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import STATUS_LABELS
from utils.kakao_map import pioneer_map_html
from services.geocoding import geocode, search_keyword
from config import CATEGORY_OPTIONS
from utils.helpers import safe_error

_SHOP_COLS = "id,fc_id,shop_name,address,lat,lng,status,category,memo,photo_url,created_at"


@st.cache_data(ttl=30, show_spinner=False)
def _load_my_shops(_sb, fc_id: str) -> list[dict]:
    """내 매장 조회 (30초 캐싱)"""
    res = (_sb.table("pioneer_shops")
           .select(_SHOP_COLS)
           .eq("fc_id", fc_id)
           .order("created_at", desc=True)
           .execute())
    return res.data or []


@st.cache_data(ttl=30, show_spinner=False)
def _load_shared_shops(_sb, fc_id: str) -> tuple[list[dict], dict[str, str]]:
    """공유 매장 + 소유자 이름 (30초 캐싱, 배치 쿼리)"""
    from services.pioneer_share import get_shared_to_me
    shares = get_shared_to_me(_sb, fc_id)
    if not shares:
        return [], {}

    owner_ids = list({s["owner_id"] for s in shares})
    # 배치 쿼리: N+1 제거 → .in_() 한 번에 조회
    res = (_sb.table("pioneer_shops")
           .select(_SHOP_COLS)
           .in_("fc_id", owner_ids)
           .order("created_at", desc=True)
           .execute())
    all_shared = res.data or []

    # 소유자 이름 한 번에 조회
    from views.page_pioneer_share import _get_user_names
    user_names = _get_user_names(_sb, owner_ids)
    return all_shared, user_names


@st.cache_data(ttl=30, show_spinner=False)
def _load_visits(_sb, fc_id: str) -> list[dict]:
    """방문 기록 조회 (30초 캐싱)"""
    res = (_sb.table("pioneer_visits")
           .select("id,shop_id,fc_id,visit_date,memo,result")
           .eq("fc_id", fc_id)
           .order("visit_date", desc=True)
           .execute())
    return res.data or []


def _invalidate_cache():
    """매장/방문 캐시 초기화"""
    _load_my_shops.clear()
    _load_shared_shops.clear()
    _load_visits.clear()


@st.fragment
def _lazy_followup():
    from views.page_pioneer_followup import render_followup
    render_followup()


@st.fragment
def _lazy_excel():
    from views.page_pioneer_excel import render_excel_import
    render_excel_import()


@st.fragment
def _lazy_share():
    from views.page_pioneer_share import render_team_share
    render_team_share()


@st.fragment
def _lazy_ocr():
    from views.page_pioneer_ocr import render_ocr
    render_ocr()


def render():
    st.header("개척지도")
    tab_map, tab_followup, tab_register, tab_excel, tab_share, tab_ocr = st.tabs(
        ["지도", "팔로업", "매장 등록", "엑셀 등록", "팀 공유", "간판 OCR"]
    )

    with tab_map:
        _render_map()
    with tab_followup:
        _lazy_followup()
    with tab_register:
        _render_register()
    with tab_excel:
        _lazy_excel()
    with tab_share:
        _lazy_share()
    with tab_ocr:
        _lazy_ocr()


@st.fragment
def _render_map():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    try:
        shops = _load_my_shops(sb, fc_id)
    except Exception as e:
        st.error(safe_error("매장 조회", e))
        return

    # 공유받은 매장도 함께 표시 (캐싱된 배치 쿼리)
    try:
        shared_raw, user_names = _load_shared_shops(sb, fc_id)
    except Exception:
        shared_raw, user_names = [], {}
    shared_all = []
    for s in shared_raw:
        s_copy = dict(s)
        s_copy["_shared_from"] = user_names.get(s["fc_id"], "팀원")
        shared_all.append(s_copy)

    all_shops = shops + shared_all

    if not all_shops:
        st.info("등록된 매장이 없습니다. '매장 등록' 탭에서 추가하세요.")
        return

    # 내 매장 / 공유 매장 토글
    show_shared = False
    if shared_all:
        show_shared = st.checkbox(f"팀원 공유 매장도 표시 ({len(shared_all)}건)", value=True)

    display_shops = shops + (shared_all if show_shared else [])

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        status_filter = st.multiselect(
            "상태 필터",
            options=list(STATUS_LABELS.keys()),
            default=list(STATUS_LABELS.keys()),
            format_func=lambda x: STATUS_LABELS[x],
        )
    with filter_col2:
        all_cats = sorted({s.get("category", "기타") for s in display_shops})
        cat_filter = st.multiselect("업종 필터", options=all_cats, default=all_cats)
    with filter_col3:
        franchise_opt = st.selectbox(
            "매장 구분",
            ["전체", "개인매장만", "프랜차이즈만"],
        )

    filtered = []
    for s in display_shops:
        if s.get("status") not in status_filter:
            continue
        if s.get("category", "기타") not in cat_filter:
            continue
        memo = s.get("memo", "")
        is_fr = "프랜차이즈:" in memo
        if franchise_opt == "개인매장만" and is_fr:
            continue
        if franchise_opt == "프랜차이즈만" and not is_fr:
            continue
        filtered.append(s)

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
            memo = s.get("memo", "")
            is_fr = "프랜차이즈:" in memo
            with st.container(border=True):
                fr_tag = " `FC`" if is_fr else ""
                label = f"{icon} **{s.get('shop_name', '')}**{fr_tag}"
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
                                _invalidate_cache()
                                st.rerun()
                            except Exception as e:
                                st.error(safe_error("변경", e))


@st.fragment
def _render_register():
    st.subheader("매장 등록")

    # 카카오 장소 검색
    search_q = st.text_input("장소 검색", placeholder="매장명 또는 주소로 검색")
    if search_q and st.button("검색", key="reg_search"):
        with st.spinner("검색 중..."):
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
                    _invalidate_cache()
                    st.session_state.pop("reg_places", None)
                    st.rerun()
                except Exception as e:
                    st.error(safe_error("등록", e))
