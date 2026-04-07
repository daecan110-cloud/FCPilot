"""개척지도 — 간판 OCR 탭"""
import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.geocoding import geocode
from utils.helpers import safe_error

CATEGORY_OPTIONS = ["음식점", "카페", "미용실/뷰티", "학원/교육", "병원/약국", "편의점/마트", "의류/패션", "사무실/오피스", "기타"]


def render_ocr():
    st.subheader("간판 OCR")
    st.caption("간판 사진을 업로드하면 AI가 가게명/업종을 자동 추출합니다.")

    photo = st.file_uploader("간판 사진", type=["jpg", "jpeg", "png"])

    if photo:
        from utils.helpers import validate_file
        photo_err = validate_file(photo, ["jpg", "jpeg", "png"], 10)
        if photo_err:
            st.error(photo_err)
            photo = None

    if photo and st.button("간판 분석", type="primary"):
        from services.ocr_engine import extract_from_sign
        img_bytes = photo.read()
        ext = photo.name.rsplit(".", 1)[-1].lower()
        media = f"image/{ext}"
        if media == "image/jpg":
            media = "image/jpeg"

        gps_address = _extract_gps_address(img_bytes)

        with st.spinner("간판 분석 중..."):
            result = extract_from_sign(img_bytes, media)

        if gps_address and not result.get("address"):
            result["address"] = gps_address

        st.session_state.ocr_result = result
        st.session_state.ocr_photo_bytes = img_bytes
        st.session_state.ocr_photo_ext = ext if ext != "jpg" else "jpeg"
        st.image(img_bytes, width=300)

    result = st.session_state.get("ocr_result")
    if result:
        st.subheader("추출 결과 (수정 후 등록)")
        shop_name = st.text_input("매장명", value=result.get("shop_name", ""))
        address = st.text_input("주소", value=result.get("address", ""))

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
                fc_id = get_current_user_id()
                photo_url = _upload_photo(sb, fc_id, st.session_state.get("ocr_photo_bytes"), st.session_state.get("ocr_photo_ext", "jpeg"))
                sb.table("pioneer_shops").insert({
                    "fc_id": fc_id,
                    "shop_name": shop_name.strip(),
                    "address": address.strip(),
                    "lat": lat,
                    "lng": lng,
                    "category": category,
                    "phone": result.get("phone", ""),
                    "photo_url": photo_url,
                }).execute()
                st.success(f"'{shop_name}' 등록 완료!")
                st.session_state.pop("ocr_result", None)
                st.session_state.pop("ocr_photo_bytes", None)
                st.session_state.pop("ocr_photo_ext", None)
            except Exception as e:
                st.error(safe_error("등록", e))


def _upload_photo(sb, fc_id: str, img_bytes: bytes | None, ext: str) -> str:
    """간판 사진을 Supabase Storage에 업로드, public URL 반환"""
    if not img_bytes:
        return ""
    try:
        import uuid
        filename = f"{fc_id}/{uuid.uuid4().hex}.{ext}"
        sb.storage.from_("pioneer-photos").upload(
            filename, img_bytes,
            file_options={"content-type": f"image/{ext}"},
        )
        url = sb.storage.from_("pioneer-photos").get_public_url(filename)
        return url
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
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        decimal = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None
