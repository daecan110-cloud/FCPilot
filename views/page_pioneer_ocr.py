"""개척지도 — 간판 OCR 탭"""
import re
import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.geocoding import geocode, search_keyword
from config import CATEGORY_OPTIONS
from utils.helpers import safe_error


def render_ocr():
    st.subheader("간판 OCR")
    st.caption("간판 사진을 업로드하면 AI가 가게명/업종을 자동 추출합니다.")

    msg = st.session_state.pop("ocr_msg", None)
    if msg:
        st.success(msg)

    photo = st.file_uploader("간판 사진", type=["jpg", "jpeg", "png"])

    if photo:
        from utils.helpers import validate_file
        photo_err = validate_file(photo, ["jpg", "jpeg", "png"], 10)
        if photo_err:
            st.error(photo_err)
            photo = None

    if photo and st.button("간판 분석", type="primary"):
        _run_ocr(photo)
        return

    ocr = st.session_state.get("ocr_data")
    if not ocr:
        return

    # 사진 표시
    if ocr.get("photo_bytes"):
        st.image(ocr["photo_bytes"], width=300)

    st.subheader("추출 결과 (수정 후 등록)")

    # 매장명
    shop_name = st.text_input("매장명", value=ocr.get("shop_name", ""))

    # 주소 검색
    address = ocr.get("address", "")
    lat, lng = ocr.get("lat"), ocr.get("lng")

    sc1, sc2 = st.columns([4, 1])
    with sc1:
        search_q = st.text_input("주소 검색", value=shop_name, placeholder="매장명 또는 주소 입력")
    with sc2:
        st.write("")
        st.write("")
        do_search = st.button("검색")

    if do_search and search_q:
        found = search_keyword(search_q)
        if found:
            ocr["places"] = found
        else:
            st.warning("검색 결과 없음")

    places = ocr.get("places", [])
    if places:
        place_options = ["직접 입력"] + [
            f"{p['place_name']} — {p.get('road_address_name') or p.get('address_name', '')}"
            for p in places
        ]
        choice = st.selectbox("검색 결과에서 선택", place_options)
        if choice != "직접 입력":
            idx = place_options.index(choice) - 1
            picked = places[idx]
            address = picked.get("road_address_name") or picked.get("address_name", "")
            lat = float(picked.get("y", 0))
            lng = float(picked.get("x", 0))

    address = st.text_input("주소", value=address)

    # 업종
    ocr_cat = ocr.get("category", "")
    cat_idx = next(
        (i for i, c in enumerate(CATEGORY_OPTIONS) if ocr_cat and ocr_cat[:3] in c),
        len(CATEGORY_OPTIONS) - 1,
    )
    category = st.selectbox("업종", CATEGORY_OPTIONS, index=cat_idx)

    # 등록
    if st.button("이 매장 등록", use_container_width=True, type="primary"):
        if not lat or not lng:
            if address:
                coords = geocode(address)
                if coords:
                    lat, lng = coords
        try:
            sb = get_supabase_client()
            fc_id = get_current_user_id()
            photo_url = _upload_photo(
                fc_id, ocr.get("photo_bytes"), ocr.get("photo_ext", "jpeg"),
            )
            sb.table("pioneer_shops").insert({
                "fc_id": fc_id,
                "shop_name": shop_name.strip(),
                "address": address.strip(),
                "lat": lat,
                "lng": lng,
                "category": category,
                "phone": ocr.get("phone", ""),
                "photo_url": photo_url,
            }).execute()
            st.session_state.pop("ocr_data", None)
            st.session_state["ocr_msg"] = f"'{shop_name}' 등록 완료!"
            st.rerun()
        except Exception as e:
            st.error(safe_error("등록", e))


def _run_ocr(photo):
    """OCR 실행 + 카카오 검색 + 결과를 단일 dict로 저장"""
    from services.ocr_engine import extract_from_sign

    img_bytes = photo.read()
    ext = photo.name.rsplit(".", 1)[-1].lower()
    media = f"image/{ext}"
    if media == "image/jpg":
        media = "image/jpeg"

    gps_address = _extract_gps_address(img_bytes)

    with st.spinner("간판 분석 중..."):
        result = extract_from_sign(img_bytes, media)

    # 주소 결정: GPS > OCR (유효한 경우만)
    address = ""
    if gps_address:
        address = gps_address
    elif result.get("address") and _is_korean_address(result["address"]):
        address = result["address"]

    # 카카오 자동 검색
    places = []
    if result.get("shop_name"):
        places = search_keyword(result["shop_name"])

    # 단일 dict로 저장
    st.session_state.ocr_data = {
        "shop_name": result.get("shop_name", ""),
        "category": result.get("category", ""),
        "phone": result.get("phone", ""),
        "address": address,
        "lat": None,
        "lng": None,
        "places": places,
        "photo_bytes": img_bytes,
        "photo_ext": ext if ext != "jpg" else "jpeg",
    }
    st.rerun()


def _is_korean_address(text: str) -> bool:
    return bool(re.search(r"(시|군|구|동|읍|면|리|로|길|번지)", text))


def _upload_photo(fc_id: str, img_bytes: bytes | None, ext: str) -> str:
    """간판 사진을 Supabase Storage에 업로드, public URL 반환"""
    if not img_bytes:
        return ""
    try:
        import uuid
        from utils.db_admin import get_admin_client
        admin_sb = get_admin_client()
        filename = f"{fc_id}/{uuid.uuid4().hex}.{ext}"
        admin_sb.storage.from_("pioneer-photos").upload(
            filename, img_bytes,
            file_options={"content-type": f"image/{ext}"},
        )
        return admin_sb.storage.from_("pioneer-photos").get_public_url(filename)
    except Exception:
        return ""


def _extract_gps_address(image_bytes: bytes) -> str:
    """사진 EXIF GPS → Reverse Geocoding → 주소 반환"""
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

        from services.geocoding import reverse_geocode
        return reverse_geocode(lat, lng)
    except Exception:
        return ""


def _dms_to_decimal(dms, ref) -> float | None:
    try:
        d, m, s = float(dms[0]), float(dms[1]), float(dms[2])
        decimal = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None
