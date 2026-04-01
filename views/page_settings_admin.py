"""Admin 전용 섹션 — 회원 승인 + 역할 관리 + DB 통계"""
import streamlit as st


def render_admin_section(sb):
    from utils.db_admin import get_admin_client
    try:
        admin_sb = get_admin_client()
    except Exception:
        admin_sb = sb  # fallback
    st.divider()
    st.subheader("🔧 Admin 관리")
    _render_approval(admin_sb)
    _render_roles(admin_sb)
    _render_db_stats(sb)


def _render_approval(sb):
    with st.expander("회원가입 승인 관리"):
        try:
            users = sb.table("users_settings").select("id, display_name, status").execute().data or []
        except Exception as e:
            st.error(f"사용자 조회 실패: {e}")
            return

        pending = [u for u in users if u.get("status") == "pending"]
        if pending:
            st.warning(f"승인 대기 {len(pending)}명")
            for u in pending:
                name = u.get("display_name") or u["id"][:8]
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.text(name)
                if c2.button("승인", key=f"appr_{u['id']}", type="primary", use_container_width=True):
                    try:
                        sb.table("users_settings").update({"status": "approved"}).eq("id", u["id"]).execute()
                        st.success(f"{name} 승인 완료")
                        st.rerun()
                    except Exception as e:
                        st.error(f"승인 실패: {e}")
                if c3.button("거절", key=f"rejt_{u['id']}", use_container_width=True):
                    try:
                        sb.table("users_settings").update({"status": "rejected"}).eq("id", u["id"]).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"거절 실패: {e}")
        else:
            st.caption("승인 대기 중인 회원이 없습니다.")

        st.divider()
        _STATUS_BADGE = {"approved": "✅", "pending": "⏳", "rejected": "❌"}
        for u in users:
            status = u.get("status", "approved")
            badge = _STATUS_BADGE.get(status, "✅")
            name = u.get("display_name") or u["id"][:8]
            c1, c2 = st.columns([4, 1])
            c1.text(f"{badge} {name}")
            if status != "approved":
                if c2.button("승인", key=f"re_appr_{u['id']}", use_container_width=True):
                    try:
                        sb.table("users_settings").update({"status": "approved"}).eq("id", u["id"]).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(f"승인 실패: {e}")


def _render_roles(sb):
    with st.expander("사용자 역할 관리"):
        try:
            users = sb.table("users_settings").select("id, display_name, role").execute().data or []
        except Exception as e:
            st.error(f"사용자 조회 실패: {e}")
            return
        for u in users:
            col1, col2, col3 = st.columns([3, 2, 2])
            col1.text(u.get("display_name") or u["id"][:8])
            col2.text(u.get("role", "user"))
            new_role = col3.selectbox(
                "역할", ["user", "admin"],
                index=0 if u.get("role") != "admin" else 1,
                key=f"role_{u['id']}", label_visibility="collapsed",
            )
            if st.button("변경", key=f"btn_{u['id']}"):
                try:
                    sb.table("users_settings").update({"role": new_role}).eq("id", u["id"]).execute()
                    st.success("역할 변경 완료")
                    st.rerun()
                except Exception as e:
                    st.error(f"변경 실패: {e}")


def _render_db_stats(sb):
    with st.expander("DB 통계"):
        try:
            tables = ["clients", "contact_logs", "pioneer_shops", "pioneer_visits",
                      "analysis_records", "yakwan_records", "command_queue", "fp_products"]
            for t in tables:
                res = sb.table(t).select("id", count="exact").execute()
                st.text(f"{t}: {res.count}건")
        except Exception as e:
            st.error(f"통계 조회 실패: {e}")
