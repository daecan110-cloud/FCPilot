"""Admin 전용 섹션 — 회원 승인 + 역할 관리 + DB 통계"""
import streamlit as st
from utils.helpers import safe_error


def render_admin_section(sb):
    from utils.db_admin import get_admin_client
    try:
        admin_sb = get_admin_client()
    except Exception:
        admin_sb = sb
    st.divider()
    st.subheader("🔧 Admin 관리")
    _render_members(admin_sb)
    _render_db_stats(sb)


def _render_members(sb):
    with st.expander("회원 관리", expanded=True):
        try:
            users = sb.table("users_settings").select("id, display_name, status, role").execute().data or []
        except Exception as e:
            st.error(safe_error("사용자 조회", e))
            return

        pending  = [u for u in users if u.get("status") == "pending"]
        approved = [u for u in users if u.get("status") == "approved"]
        rejected = [u for u in users if u.get("status") == "rejected"]

        # ── 승인 대기 ──
        if pending:
            st.warning(f"승인 대기 {len(pending)}명")
            for u in pending:
                name = u.get("display_name") or u["id"][:8]
                c1, c2, c3 = st.columns([4, 1, 1])
                c1.markdown(f"⏳ **{name}**")
                if c2.button("승인", key=f"appr_{u['id']}", type="primary", use_container_width=True):
                    try:
                        sb.table("users_settings").update({"status": "approved", "role": "user"}).eq("id", u["id"]).execute()
                        st.success(f"{name} 승인 완료")
                        st.rerun()
                    except Exception as e:
                        st.error(safe_error("승인", e))
                if c3.button("거절", key=f"rejt_{u['id']}", use_container_width=True):
                    try:
                        sb.table("users_settings").update({"status": "rejected"}).eq("id", u["id"]).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(safe_error("거절", e))
            st.divider()
        else:
            st.caption("승인 대기 없음")

        # ── 승인된 유저 ──
        if approved:
            st.caption(f"승인된 회원 {len(approved)}명")
            for u in approved:
                name = u.get("display_name") or u["id"][:8]
                role = u.get("role") or "user"
                del_key = f"del_confirm_{u['id']}"

                if st.session_state.get(del_key):
                    st.error(f"**{name}** 계정을 완전 삭제합니다. 복구 불가.")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("삭제 확인", key=f"del_ok_{u['id']}", type="primary", use_container_width=True):
                        _delete_user(sb, u["id"])
                        st.session_state.pop(del_key, None)
                        st.rerun()
                    if dc2.button("취소", key=f"del_cancel_{u['id']}", use_container_width=True):
                        st.session_state.pop(del_key, None)
                        st.rerun()
                else:
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
                    c1.markdown(f"✅ {name}")
                    new_role = c2.selectbox(
                        "역할",
                        ["user", "admin"],
                        index=0 if role != "admin" else 1,
                        key=f"role_{u['id']}",
                        label_visibility="collapsed",
                    )
                    if c3.button("역할 변경", key=f"role_btn_{u['id']}", use_container_width=True):
                        try:
                            sb.table("users_settings").update({"role": new_role}).eq("id", u["id"]).execute()
                            st.success("변경됨")
                            st.rerun()
                        except Exception as e:
                            st.error(safe_error("처리", e))
                    if c4.button("비활성화", key=f"deact_{u['id']}", use_container_width=True):
                        try:
                            sb.table("users_settings").update({"status": "rejected"}).eq("id", u["id"]).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(safe_error("처리", e))
                    if c5.button("삭제", key=f"del_btn_{u['id']}", use_container_width=True):
                        st.session_state[del_key] = True
                        st.rerun()

        # ── 거절/비활성화 유저 ──
        if rejected:
            st.divider()
            st.caption(f"거절/비활성화 {len(rejected)}명")
            for u in rejected:
                name = u.get("display_name") or u["id"][:8]
                del_key = f"del_confirm_{u['id']}"

                if st.session_state.get(del_key):
                    st.error(f"**{name}** 계정을 완전 삭제합니다. 복구 불가.")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("삭제 확인", key=f"del_ok_{u['id']}", type="primary", use_container_width=True):
                        _delete_user(sb, u["id"])
                        st.session_state.pop(del_key, None)
                        st.rerun()
                    if dc2.button("취소", key=f"del_cancel_{u['id']}", use_container_width=True):
                        st.session_state.pop(del_key, None)
                        st.rerun()
                else:
                    c1, c2, c3 = st.columns([4, 1, 1])
                    c1.markdown(f"❌ {name}")
                    if c2.button("재승인", key=f"re_appr_{u['id']}", use_container_width=True):
                        try:
                            sb.table("users_settings").update({"status": "approved", "role": "user"}).eq("id", u["id"]).execute()
                            st.rerun()
                        except Exception as e:
                            st.error(safe_error("처리", e))
                    if c3.button("삭제", key=f"del_btn_{u['id']}", use_container_width=True):
                        st.session_state[del_key] = True
                        st.rerun()


def _delete_user(sb, user_id: str):
    """users_settings 삭제 + Supabase Auth 계정 삭제"""
    try:
        sb.table("users_settings").delete().eq("id", user_id).execute()
    except Exception as e:
        st.error(safe_error("설정 삭제", e))
        return
    try:
        sb.auth.admin.delete_user(user_id)
    except Exception as e:
        st.warning(f"Auth 계정 삭제 실패 (설정은 삭제됨): {e}")
    st.success("삭제 완료")


def _render_db_stats(sb):
    with st.expander("DB 통계"):
        try:
            tables = ["clients", "contact_logs", "pioneer_shops", "pioneer_visits",
                      "analysis_records", "yakwan_records", "command_queue", "fp_products"]
            for t in tables:
                res = sb.table(t).select("id", count="exact").execute()
                st.text(f"{t}: {res.count}건")
        except Exception as e:
            st.error(safe_error("통계 조회", e))
