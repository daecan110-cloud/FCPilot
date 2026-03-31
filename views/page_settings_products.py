"""상품 관리 섹션 — 설정 탭에서 호출"""
import tomllib
from pathlib import Path

import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client

_CATEGORIES = ["종신보험", "건강보험", "연금보험", "저축보험", "변액보험", "기타"]
_BUCKET = "product-designs"


def _storage_client():
    """service_role_key 기반 Supabase 클라이언트 (Storage 접근용)"""
    try:
        from supabase import create_client
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["service_role_key"]
        return create_client(url, key)
    except Exception:
        try:
            from supabase import create_client
            secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
            with open(secrets_path, "rb") as f:
                s = tomllib.load(f)
            return create_client(s["supabase"]["url"], s["supabase"]["service_role_key"])
        except Exception:
            return get_supabase_client()


def _upload_pdf(fc_id: str, product_id: str, file_bytes: bytes) -> str | None:
    """설계서 PDF → Storage 업로드, 공개 URL 반환"""
    try:
        sb = _storage_client()
        path = f"{fc_id}/{product_id}.pdf"
        sb.storage.from_(_BUCKET).upload(
            path, file_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )
        # signed URL (24시간)
        res = sb.storage.from_(_BUCKET).create_signed_url(path, 86400)
        return res.get("signedURL") or res.get("signed_url")
    except Exception as e:
        st.error(f"PDF 업로드 실패: {e}")
        return None


def _get_signed_url(fc_id: str, product_id: str) -> str | None:
    try:
        res = _storage_client().storage.from_(_BUCKET).create_signed_url(f"{fc_id}/{product_id}.pdf", 86400)
        return res.get("signedURL") or res.get("signed_url")
    except Exception:
        return None


def _delete_pdf(fc_id: str, product_id: str):
    try:
        _storage_client().storage.from_(_BUCKET).remove([f"{fc_id}/{product_id}.pdf"])
    except Exception:
        pass

def render_product_section():
    """설정 탭에서 호출하는 상품 관리 섹션"""
    st.subheader("상품 관리")
    st.caption("리마인드 등록 시 '제안할 상품' 목록에 표시됩니다.")

    sb = get_supabase_client()
    fc_id = get_current_user_id()

    try:
        products = sb.table("fp_products").select("*").eq("fc_id", fc_id).order("created_at").execute().data or []
    except Exception as e:
        st.error(f"상품 목록 조회 실패: {e}")
        products = []

    # 등록된 상품 목록
    for p in products:
        _render_product_card(sb, fc_id, p)
    if not products:
        st.caption("등록된 상품이 없습니다.")
    st.divider()
    _render_add_form(sb, fc_id)


def _render_product_card(sb, fc_id: str, p: dict):
    pid = p["id"]
    edit_key = f"prod_edit_{pid}"
    confirm_key = f"prod_del_{pid}"

    icon = "🟢" if p.get("is_active", True) else "⚫"
    premium = f"{p['monthly_premium']:,}만원" if p.get("monthly_premium") else "-"
    with st.expander(f"{icon} {p['name']}  |  {p.get('category','기타')}  |  {premium}"):
        if p.get("coverage_summary"):
            st.caption(p["coverage_summary"])
        if p.get("design_pdf_url"):
            url = _get_signed_url(fc_id, pid)
            if url:
                st.markdown(f"[📄 설계서 보기]({url})")
        col_e, col_d = st.columns(2)

        if col_e.button("수정", key=f"edit_btn_{pid}", use_container_width=True):
            st.session_state[edit_key] = not st.session_state.get(edit_key, False)
            st.rerun()

        if st.session_state.get(confirm_key):
            st.warning("삭제하시겠습니까?")
            c1, c2 = st.columns(2)
            if c1.button("삭제 확인", key=f"del_ok_{pid}", type="primary", use_container_width=True):
                try:
                    _delete_pdf(fc_id, pid)
                    sb.table("fp_products").delete().eq("id", pid).execute()
                    st.session_state.pop(confirm_key, None)
                    st.session_state.pop(edit_key, None)
                    st.rerun()
                except Exception as e:
                    st.error(f"삭제 실패: {e}")
            if c2.button("취소", key=f"del_no_{pid}", use_container_width=True):
                st.session_state.pop(confirm_key, None)
                st.rerun()
        else:
            if col_d.button("삭제", key=f"del_btn_{pid}", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()

        if st.session_state.get(edit_key):
            _render_edit_form(sb, fc_id, p)


def _render_edit_form(sb, fc_id: str, p: dict):
    pid = p["id"]
    with st.form(f"edit_form_{pid}"):
        name = st.text_input("상품명", value=p.get("name", ""))
        cat_idx = _CATEGORIES.index(p["category"]) if p.get("category") in _CATEGORIES else len(_CATEGORIES) - 1
        category = st.selectbox("카테고리", _CATEGORIES, index=cat_idx)
        premium = st.number_input("월 보험료 예시 (만원)", value=p.get("monthly_premium") or 0, min_value=0, step=1)
        summary = st.text_area("주요 보장내용 요약", value=p.get("coverage_summary", ""), height=80)
        is_active = st.checkbox("활성 상품", value=p.get("is_active", True))

        pdf_toggle = st.toggle("설계서 PDF 교체", value=False)
        pdf_file = st.file_uploader("PDF 선택", type=["pdf"], key=f"pdf_edit_{pid}") if pdf_toggle else None

        if st.form_submit_button("저장", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("상품명을 입력하세요.")
                return
            update = {
                "name": name.strip(), "category": category,
                "monthly_premium": premium or None,
                "coverage_summary": summary.strip() or None,
                "is_active": is_active,
                "updated_at": "now()",
            }
            if pdf_file:
                pdf_url = _upload_pdf(fc_id, pid, pdf_file.read())
                if pdf_url:
                    update["design_pdf_url"] = pdf_url
            try:
                sb.table("fp_products").update(update).eq("id", pid).execute()
                st.session_state.pop(f"prod_edit_{pid}", None)
                st.success("저장되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")


def _render_add_form(sb, fc_id: str):
    st.markdown("**새 상품 추가**")
    with st.form("add_product_form"):
        name = st.text_input("상품명", placeholder="예: 신한 THE건강보험")
        category = st.selectbox("카테고리", _CATEGORIES)
        premium = st.number_input("월 보험료 예시 (만원)", min_value=0, step=1, value=0)
        summary = st.text_area("주요 보장내용 요약", placeholder="예: 3대 질병 진단비 5000만, 수술비 500만 ...", height=80)
        pdf_toggle = st.toggle("설계서 PDF 첨부")
        pdf_file = st.file_uploader("PDF 선택", type=["pdf"], key="pdf_add") if pdf_toggle else None

        if st.form_submit_button("추가", use_container_width=True, type="primary"):
            if not name.strip():
                st.error("상품명을 입력하세요.")
                return
            try:
                row = {
                    "fc_id": fc_id,
                    "name": name.strip(),
                    "category": category,
                    "monthly_premium": premium or None,
                    "coverage_summary": summary.strip() or None,
                    "is_active": True,
                }
                res = sb.table("fp_products").insert(row).execute()
                new_id = res.data[0]["id"]
                if pdf_file:
                    pdf_url = _upload_pdf(fc_id, new_id, pdf_file.read())
                    if pdf_url:
                        sb.table("fp_products").update({"design_pdf_url": pdf_url}).eq("id", new_id).execute()
                st.success(f"'{name}' 상품이 등록되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"등록 실패: {e}")
