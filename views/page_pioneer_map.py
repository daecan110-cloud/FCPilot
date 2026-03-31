"""개척지도 탭 — 매장 등록/지도 표시/팔로업"""
import streamlit as st
from streamlit_folium import st_folium
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import create_map, STATUS_LABELS
from services.geocoding import geocode
from config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE_MB

CATEGORY_OPTIONS = ["음식점", "카페", "미용실/뷰티", "학원/교육", "병원/약국", "편의점/마트", "의류/패션", "사무실/오피스", "기타"]


def render():
    st.header("개척지도")
    tab_map, tab_followup, tab_register, tab_ocr = st.tabs(["지도", "팔로업", "매장 등록", "간판 OCR"])

    with tab_map:
        _render_map()
    with tab_followup:
        _render_followup()
    with tab_register:
        _render_register()
    with tab_ocr:
        _render_ocr()


def _render_map():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    try:
        res = sb.table("pioneer_shops").select("*").eq("fc_id", fc_id).order("created_at", desc=True).execute()
        shops = res.data or []
    except Exception as e:
        st.error(f"매장 조회 실패: {e}")
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
    st.caption(f"전체 {len(shops)}개 | 표시 {len(filtered)}개")

    # BUG-07: 선택 매장으로 지도 센터 이동
    selected_id = st.session_state.get("map_focus_shop")
    center_shop = next((s for s in filtered if s["id"] == selected_id), None)

    m = create_map(filtered, center_shop=center_shop)
    st_folium(m, width=700, height=500, key="pioneer_map")

    # 매장 목록 — 클릭 시 지도 포커스
    for s in filtered:
        status = STATUS_LABELS.get(s.get("status", ""), "등록")
        with st.expander(f"{s.get('shop_name', '')} ({status})"):
            st.text(f"주소: {s.get('address', '-')}")
            st.text(f"업종: {s.get('category', '-')}")
            if s.get("memo"):
                st.text(f"메모: {s['memo']}")

            col_focus, col_status = st.columns(2)
            with col_focus:
                if st.button("지도에서 보기", key=f"focus_{s['id']}"):
                    st.session_state.map_focus_shop = s["id"]
                    st.rerun()

            with col_status:
                new_status = st.selectbox(
                    "상태",
                    options=list(STATUS_LABELS.keys()),
                    index=list(STATUS_LABELS.keys()).index(s.get("status", "active")),
                    format_func=lambda x: STATUS_LABELS[x],
                    key=f"status_{s['id']}",
                )
                if new_status != s.get("status"):
                    if st.button("변경", key=f"change_{s['id']}"):
                        try:
                            sb.table("pioneer_shops").update({"status": new_status}).eq("id", s["id"]).execute()
                            st.success("변경되었습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"변경 실패: {e}")


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
                    st.error(f"등록 실패: {e}")


def _render_ocr():
    st.subheader("간판 OCR")
    st.caption("간판 사진을 업로드하면 AI가 가게명/업종을 자동 추출합니다.")

    photo = st.file_uploader("간판 사진", type=["jpg", "jpeg", "png"])

    if photo and st.button("간판 분석", type="primary"):
        from services.ocr_engine import extract_from_sign
        img_bytes = photo.read()
        media = f"image/{photo.name.rsplit('.', 1)[-1].lower()}"
        if media == "image/jpg":
            media = "image/jpeg"

        # BUG-06: EXIF GPS → 자동 주소
        gps_address = _extract_gps_address(img_bytes)

        with st.spinner("간판 분석 중..."):
            result = extract_from_sign(img_bytes, media)

        if gps_address and not result.get("address"):
            result["address"] = gps_address

        st.session_state.ocr_result = result
        st.image(img_bytes, width=300)

    result = st.session_state.get("ocr_result")
    if result:
        st.subheader("추출 결과 (수정 후 등록)")
        shop_name = st.text_input("매장명", value=result.get("shop_name", ""))
        address = st.text_input("주소", value=result.get("address", ""))

        # BUG-05: 업종 드롭다운 (OCR 추천값 기본 선택)
        ocr_cat = result.get("category", "")
        cat_idx = next((i for i, c in enumerate(CATEGORY_OPTIONS) if ocr_cat and ocr_cat[:3] in c), len(CATEGORY_OPTIONS) - 1)
        category = st.selectbox("업종", CATEGORY_OPTIONS, index=cat_idx)

        if st.button("이 매장 등록", use_container_width=True, type="primary"):
            lat, lng = None, None
            if address:
                coords = geocode(address)
                if coords:
                    lat, lng = coords
            try:
                sb = get_supabase_client()
                sb.table("pioneer_shops").insert({
                    "fc_id": get_current_user_id(),
                    "shop_name": shop_name.strip(),
                    "address": address.strip(),
                    "lat": lat,
                    "lng": lng,
                    "category": category,
                    "phone": result.get("phone", ""),
                }).execute()
                st.success(f"'{shop_name}' 등록 완료!")
                st.session_state.pop("ocr_result", None)
            except Exception as e:
                st.error(f"등록 실패: {e}")


def _extract_gps_address(image_bytes: bytes) -> str:
    """사진 EXIF GPS → Naver Reverse Geocoding → 주소 반환. 없으면 빈 문자열."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        import io

        img = Image.open(io.BytesIO(image_bytes))
        exif = img._getexif()
        if not exif:
            return ""

        gps_info = {}
        for tag_id, value in exif.items():
            if TAGS.get(tag_id) == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_info[GPSTAGS.get(gps_tag_id, gps_tag_id)] = gps_value

        if not gps_info:
            return ""

        lat = _dms_to_decimal(gps_info.get("GPSLatitude"), gps_info.get("GPSLatitudeRef"))
        lng = _dms_to_decimal(gps_info.get("GPSLongitude"), gps_info.get("GPSLongitudeRef"))
        if not lat or not lng:
            return ""

        return _reverse_geocode(lat, lng)
    except Exception:
        return ""


def _dms_to_decimal(dms, ref) -> float | None:
    try:
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        decimal = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None


def _reverse_geocode(lat: float, lng: float) -> str:
    try:
        import requests
        import streamlit as st
        client_id = st.secrets["naver"]["client_id"]
        client_secret = st.secrets["naver"]["client_secret"]
        r = requests.get(
            "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc",
            params={"coords": f"{lng},{lat}", "output": "json", "orders": "roadaddr,addr"},
            headers={"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret},
            timeout=5,
        )
        results = r.json().get("results", [])
        if results:
            region = results[0].get("region", {})
            land = results[0].get("land", {})
            area1 = region.get("area1", {}).get("name", "")
            area2 = region.get("area2", {}).get("name", "")
            area3 = region.get("area3", {}).get("name", "")
            number = land.get("number1", "")
            return " ".join(filter(None, [area1, area2, area3, number]))
    except Exception:
        pass
    return ""


# ── 팔로업 (BUG-08) ──

def _render_followup():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    st.subheader("팔로업 현황")

    try:
        shops_res = sb.table("pioneer_shops").select("*").eq("fc_id", fc_id).order("created_at", desc=True).execute()
        shops = shops_res.data or []
    except Exception as e:
        st.error(f"매장 조회 실패: {e}")
        return

    if not shops:
        st.info("등록된 매장이 없습니다.")
        return

    # 방문 이력 일괄 조회
    try:
        visits_res = sb.table("pioneer_visits").select("*").eq("fc_id", fc_id).order("visit_date", desc=True).execute()
        all_visits = visits_res.data or []
    except Exception:
        all_visits = []

    from collections import defaultdict
    visits_by_shop: dict = defaultdict(list)
    for v in all_visits:
        visits_by_shop[v["shop_id"]].append(v)

    status_filter = st.selectbox("상태 필터", ["전체"] + list(STATUS_LABELS.values()))

    for shop in shops:
        status_label = STATUS_LABELS.get(shop.get("status", ""), "등록")
        if status_filter != "전체" and status_label != status_filter:
            continue

        visits = visits_by_shop.get(shop["id"], [])
        visit_count = len(visits)
        last_visit = visits[0] if visits else None

        with st.expander(f"**{shop.get('shop_name', '')}** — {status_label} | 방문 {visit_count}회"):
            col1, col2 = st.columns(2)
            with col1:
                st.text(f"주소: {shop.get('address', '-')}")
                st.text(f"업종: {shop.get('category', '-')}")
                if last_visit:
                    st.text(f"최근 방문: {last_visit.get('visit_date', '-')}")
                    if last_visit.get("memo"):
                        st.caption(f"메모: {last_visit['memo']}")
            with col2:
                new_status = st.selectbox(
                    "상태 변경",
                    list(STATUS_LABELS.keys()),
                    index=list(STATUS_LABELS.keys()).index(shop.get("status", "active")),
                    format_func=lambda x: STATUS_LABELS[x],
                    key=f"fu_status_{shop['id']}",
                )
                if st.button("상태 저장", key=f"fu_save_{shop['id']}"):
                    try:
                        sb.table("pioneer_shops").update({"status": new_status}).eq("id", shop["id"]).execute()
                        st.success("저장됨")
                        st.rerun()
                    except Exception as e:
                        st.error(f"실패: {e}")
