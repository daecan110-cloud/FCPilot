"""개척지도 탭 — 매장 등록/지도 표시"""
import streamlit as st
from streamlit_folium import st_folium
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import create_map, STATUS_LABELS
from services.geocoding import geocode
from config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE_MB


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
        res = sb.table("fp_pioneer_shops").select("*").eq("fc_id", fc_id).order("created_at", desc=True).execute()
        shops = res.data or []
    except Exception as e:
        st.error(f"매장 조회 실패: {e}")
        return

    if not shops:
        st.info("등록된 매장이 없습니다. '매장 등록' 탭에서 추가하세요.")
        return

    # 상태 필터
    status_filter = st.multiselect(
        "상태 필터",
        options=list(STATUS_LABELS.keys()),
        default=list(STATUS_LABELS.keys()),
        format_func=lambda x: STATUS_LABELS[x],
    )
    filtered = [s for s in shops if s.get("status") in status_filter]

    st.caption(f"전체 {len(shops)}개 | 표시 {len(filtered)}개")

    m = create_map(filtered)
    st_folium(m, width=700, height=500)

    # 매장 목록
    for s in filtered:
        status = STATUS_LABELS.get(s.get("status", ""), "등록")
        with st.expander(f"{s.get('shop_name', '')} ({status})"):
            st.text(f"주소: {s.get('address', '-')}")
            st.text(f"업종: {s.get('category', '-')}")
            if s.get("memo"):
                st.text(f"메모: {s['memo']}")

            new_status = st.selectbox(
                "상태 변경",
                options=list(STATUS_LABELS.keys()),
                index=list(STATUS_LABELS.keys()).index(s.get("status", "active")),
                format_func=lambda x: STATUS_LABELS[x],
                key=f"status_{s['id']}",
            )
            if new_status != s.get("status"):
                if st.button("변경", key=f"change_{s['id']}"):
                    try:
                        sb.table("fp_pioneer_shops").update(
                            {"status": new_status}
                        ).eq("id", s["id"]).execute()
                        st.success("변경되었습니다.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"변경 실패: {e}")


def _render_register():
    st.subheader("매장 등록")

    with st.form("shop_form"):
        shop_name = st.text_input("매장명 *", placeholder="예: 커피빈 강남점")
        address = st.text_input("주소", placeholder="예: 서울시 강남구 역삼동 123")
        category = st.selectbox("업종", ["", "음식점", "카페", "미용실", "병원", "약국", "마트", "기타"])
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
                        st.warning("주소를 좌표로 변환하지 못했습니다. 지도에 표시되지 않을 수 있습니다.")

                try:
                    sb = get_supabase_client()
                    sb.table("fp_pioneer_shops").insert({
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

        with st.spinner("간판 분석 중..."):
            result = extract_from_sign(img_bytes, media)

        st.session_state.ocr_result = result
        st.image(img_bytes, width=300)

    result = st.session_state.get("ocr_result")
    if result:
        st.subheader("추출 결과")
        shop_name = st.text_input("매장명", value=result.get("shop_name", ""))
        address = st.text_input("주소", value=result.get("address", ""))
        category = st.text_input("업종", value=result.get("category", ""))

        if st.button("이 매장 등록", use_container_width=True, type="primary"):
            lat, lng = None, None
            if address:
                coords = geocode(address)
                if coords:
                    lat, lng = coords

            try:
                sb = get_supabase_client()
                sb.table("fp_pioneer_shops").insert({
                    "fc_id": get_current_user_id(),
                    "shop_name": shop_name.strip(),
                    "address": address.strip(),
                    "lat": lat,
                    "lng": lng,
                    "category": category.strip(),
                    "phone": result.get("phone", ""),
                }).execute()
                st.success(f"'{shop_name}' 등록 완료!")
                st.session_state.pop("ocr_result", None)
            except Exception as e:
                st.error(f"등록 실패: {e}")


# ── 팔로업 ──

def _render_followup():
    from services.followup import get_followup_list
    from utils.map_utils import VISIT_RESULT_LABELS

    st.subheader("팔로업 현황")
    fc_id = get_current_user_id()
    followups = get_followup_list(fc_id)

    if not followups:
        st.info("팔로업 대상이 없습니다.")
        return

    priority_icons = {"high": "!!!", "medium": "!!", "low": ""}

    for f in followups:
        shop = f["shop"]
        icon = priority_icons.get(f["priority"], "")
        name = shop.get("shop_name", "")

        if f["overdue"]:
            st.error(f"{icon} **{name}** — {f['action']}")
        elif f["priority"] == "medium":
            st.warning(f"{icon} **{name}** — {f['action']} (D-{f.get('days_left', '?')})")
        else:
            st.info(f"**{name}** — {f['action']} (D-{f.get('days_left', '?')})")

        if f.get("last_visit"):
            lv = f["last_visit"]
            result_text = VISIT_RESULT_LABELS.get(lv.get("result", ""), "")
            st.caption(f"최근 방문: {lv.get('visit_date', '')} | {result_text}")

    st.caption(f"총 {len(followups)}건")
