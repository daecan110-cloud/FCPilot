"""개척지도 — 팀 공유 관리 탭"""
import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.pioneer_share import (
    get_all_users, get_my_shares, get_shared_to_me,
    create_share, delete_share,
)


def render_team_share():
    sb = get_supabase_client()
    fc_id = get_current_user_id()

    st.subheader("팀원 공유 관리")
    st.caption("내 개척 리스트를 팀원에게 공유하거나, 공유받은 리스트를 확인합니다.")

    # ── 내가 공유한 목록 ──
    st.markdown("#### 내가 공유한 팀원")
    my_shares = get_my_shares(sb, fc_id)
    shared_ids = [s["shared_with_id"] for s in my_shares]
    names = _get_user_names(sb, shared_ids)

    if my_shares:
        for share in my_shares:
            tid = share["shared_with_id"]
            name = names.get(tid, "알 수 없음")
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(f"{name}")
            with col2:
                if st.button("끊기", key=f"unshr_{share['id']}", use_container_width=True):
                    ok, err = delete_share(sb, share["id"], fc_id)
                    if ok:
                        st.success(f"{name} 공유 해제됨")
                        st.rerun()
                    else:
                        st.error(err)
    else:
        st.info("공유한 팀원이 없습니다.")

    # ── 새 팀원 공유 ──
    st.divider()
    st.markdown("#### 팀원 추가 공유")
    all_users = get_all_users(sb, fc_id)
    already_shared = set(shared_ids)
    available = [u for u in all_users if u["id"] not in already_shared]

    if available:
        options = {f"{u.get('display_name', '(이름없음)')}": u["id"] for u in available}
        selected_name = st.selectbox("공유할 팀원 선택", list(options.keys()))
        if st.button("공유하기", type="primary", use_container_width=True):
            selected_id = options[selected_name]
            ok, err = create_share(sb, fc_id, selected_id)
            if ok:
                st.success(f"{selected_name}에게 공유 완료!")
                st.rerun()
            else:
                st.error(err)
    else:
        st.info("공유 가능한 팀원이 없습니다.")

    # ── 나에게 공유된 목록 ──
    st.divider()
    st.markdown("#### 나에게 공유된 리스트")
    shared_to_me = get_shared_to_me(sb, fc_id)
    owner_ids = [s["owner_id"] for s in shared_to_me]
    owner_names = _get_user_names(sb, owner_ids)

    if shared_to_me:
        for share in shared_to_me:
            oid = share["owner_id"]
            name = owner_names.get(oid, "알 수 없음")
            col1, col2 = st.columns([4, 1])
            with col1:
                try:
                    cnt_res = sb.table("pioneer_shops").select("id", count="exact").eq("fc_id", oid).execute()
                    cnt = cnt_res.count or 0
                except Exception:
                    cnt = "?"
                st.text(f"{name} ({cnt}개 매장)")
            with col2:
                if st.button("끊기", key=f"unshr_from_{share['id']}", use_container_width=True):
                    ok, err = delete_share(sb, share["id"], fc_id)
                    if ok:
                        st.success(f"{name} 공유 해제됨")
                        st.rerun()
                    else:
                        st.error(err)
    else:
        st.info("공유받은 리스트가 없습니다.")


def _get_user_names(sb, user_ids: list[str]) -> dict[str, str]:
    """user_id → display_name 매핑"""
    if not user_ids:
        return {}
    try:
        res = sb.table("users_settings").select("id, display_name").in_("id", user_ids).execute()
        return {r["id"]: r.get("display_name") or "팀원" for r in (res.data or [])}
    except Exception:
        return {}
