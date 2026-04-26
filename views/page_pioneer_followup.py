"""개척지도 — 팔로업 탭"""
import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.map_utils import STATUS_LABELS
from services.geocoding import geocode
from config import CATEGORY_OPTIONS
from utils.helpers import safe_error


def render_followup():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    st.subheader("팔로업 현황")

    from views.page_pioneer_map import _load_my_shops, _load_visits

    try:
        shops = _load_my_shops(sb, fc_id)
    except Exception as e:
        st.error(safe_error("매장 조회", e))
        return

    if not shops:
        st.info("등록된 매장이 없습니다.")
        return

    _render_delete_all(sb, fc_id, shops)

    try:
        all_visits = _load_visits(sb, fc_id)
    except Exception:
        st.warning("방문 기록을 불러오지 못했습니다.")
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
            photo_url = shop.get("photo_url", "")
            if photo_url:
                st.image(photo_url, width=200, caption="간판 사진")
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
                    index=list(STATUS_LABELS.keys()).index(shop.get("status", "active")) if shop.get("status", "active") in STATUS_LABELS else 0,
                    format_func=lambda x: STATUS_LABELS.get(x, x),
                    key=f"fu_status_{shop['id']}",
                )
                if st.button("상태 저장", key=f"fu_save_{shop['id']}"):
                    try:
                        sb.table("pioneer_shops").update({"status": new_status}).eq("id", shop["id"]).eq("fc_id", fc_id).execute()
                        from views.page_pioneer_map import _invalidate_cache
                        _invalidate_cache()
                        st.success("저장됨")
                        st.rerun()
                    except Exception as e:
                        st.error(safe_error("처리", e))

            st.divider()
            _render_shop_actions(sb, fc_id, shop, visit_count)


def _render_delete_all(sb, fc_id: str, shops: list):
    """전체 매장 삭제 UI"""
    if st.session_state.get("delete_all_confirm"):
        total = len(shops)
        st.error(f"등록된 매장 {total}개와 모든 방문 기록을 삭제합니다. 되돌릴 수 없습니다.")
        c1, c2 = st.columns(2)
        if c1.button("전체 삭제 확인", type="primary", use_container_width=True):
            try:
                shop_ids = [s["id"] for s in shops]
                for sid in shop_ids:
                    sb.table("pioneer_visits").delete().eq("shop_id", sid).eq("fc_id", fc_id).execute()
                    sb.table("pioneer_shops").delete().eq("id", sid).eq("fc_id", fc_id).execute()
                from views.page_pioneer_map import _invalidate_cache
                _invalidate_cache()
                st.session_state.pop("delete_all_confirm", None)
                st.rerun()
            except Exception as e:
                st.error(safe_error("전체 삭제", e))
        if c2.button("취소", key="del_all_cancel", use_container_width=True):
            st.session_state.pop("delete_all_confirm", None)
            st.rerun()
    else:
        if st.button("전체 삭제", type="secondary", use_container_width=False):
            st.session_state["delete_all_confirm"] = True
            st.rerun()


def _render_shop_actions(sb, fc_id: str, shop: dict, visit_count: int):
    """매장 수정/삭제 UI"""
    edit_key = f"edit_shop_{shop['id']}"
    del_key = f"del_shop_{shop['id']}"

    if st.session_state.get(edit_key):
        with st.form(f"shop_edit_{shop['id']}"):
            new_name = st.text_input("매장명", value=shop.get("shop_name", ""))
            new_addr = st.text_input("주소", value=shop.get("address", ""))
            cat_list = CATEGORY_OPTIONS
            cat_idx = cat_list.index(shop.get("category", "기타")) if shop.get("category") in cat_list else len(cat_list) - 1
            new_cat = st.selectbox("업종", cat_list, index=cat_idx)
            new_memo = st.text_area("메모", value=shop.get("memo") or "")
            sc1, sc2 = st.columns(2)
            if sc1.form_submit_button("저장", type="primary", use_container_width=True):
                try:
                    upd = {"shop_name": new_name.strip(), "address": new_addr.strip(),
                           "category": new_cat, "memo": new_memo.strip()}
                    if new_addr.strip() and new_addr.strip() != shop.get("address", ""):
                        coords = geocode(new_addr.strip())
                        if coords:
                            upd["lat"], upd["lng"] = coords
                    sb.table("pioneer_shops").update(upd).eq("id", shop["id"]).eq("fc_id", fc_id).execute()
                    from views.page_pioneer_map import _invalidate_cache
                    _invalidate_cache()
                    st.session_state.pop(edit_key, None)
                    st.rerun()
                except Exception as e:
                    st.error(safe_error("수정", e))
            if sc2.form_submit_button("취소", use_container_width=True):
                st.session_state.pop(edit_key, None)
                st.rerun()

    elif st.session_state.get(del_key):
        st.warning(f"'{shop.get('shop_name','')}' 매장과 모든 방문 기록({visit_count}건)을 삭제합니다.")
        dc1, dc2 = st.columns(2)
        if dc1.button("삭제 확인", key=f"del_confirm_{shop['id']}", type="primary", use_container_width=True):
            try:
                sb.table("pioneer_visits").delete().eq("shop_id", shop["id"]).eq("fc_id", fc_id).execute()
                sb.table("pioneer_shops").delete().eq("id", shop["id"]).eq("fc_id", fc_id).execute()
                from views.page_pioneer_map import _invalidate_cache
                _invalidate_cache()
                st.session_state.pop(del_key, None)
                st.rerun()
            except Exception as e:
                st.error(safe_error("삭제", e))
        if dc2.button("취소", key=f"del_cancel_{shop['id']}", use_container_width=True):
            st.session_state.pop(del_key, None)
            st.rerun()

    else:
        bc1, bc2 = st.columns(2)
        if bc1.button("수정", key=f"edit_btn_{shop['id']}", use_container_width=True):
            st.session_state[edit_key] = True
            st.rerun()
        if bc2.button("삭제", key=f"del_btn_{shop['id']}", use_container_width=True):
            st.session_state[del_key] = True
            st.rerun()
