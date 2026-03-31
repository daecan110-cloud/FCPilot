"""상품 관리 섹션 — 설정 탭에서 호출 (이름 + 카테고리만)"""
import pandas as pd
import streamlit as st
from auth import get_current_user_id
from utils.supabase_client import get_supabase_client

_CATEGORIES = ["종신보험", "건강보험", "연금보험", "저축보험", "변액보험", "기타"]
_CAT_ICON = {
    "종신보험": "🔵", "건강보험": "🟢", "연금보험": "🟡",
    "저축보험": "🟠", "변액보험": "🟣", "기타": "⚪",
}


def get_active_products(sb, fc_id: str) -> list[dict]:
    """활성 상품 목록 반환 — 다른 탭에서도 호출 가능"""
    try:
        return (sb.table("fp_products").select("id, name, category")
                .eq("fc_id", fc_id).eq("is_active", True).order("name")
                .execute().data or [])
    except Exception:
        return []


def render_product_section():
    st.subheader("상품 관리")
    st.caption("셀을 직접 클릭해서 수정 · + 버튼으로 추가 · 행 선택 후 Delete로 삭제")

    sb = get_supabase_client()
    fc_id = get_current_user_id()

    try:
        rows = sb.table("fp_products").select("*").eq("fc_id", fc_id).order("name").execute().data or []
    except Exception as e:
        st.error(f"조회 실패: {e}")
        return

    # id는 숨기고, 아이콘 컬럼(표시용) 추가
    df = pd.DataFrame([{
        "_id": r["id"],
        "아이콘": _CAT_ICON.get(r.get("category", "기타"), "⚪"),
        "상품명": r.get("name", ""),
        "카테고리": r.get("category", "기타"),
        "활성": r.get("is_active", True),
    } for r in rows]) if rows else pd.DataFrame(
        columns=["_id", "아이콘", "상품명", "카테고리", "활성"]
    )

    edited = st.data_editor(
        df.drop(columns=["_id"]),
        column_config={
            "아이콘": st.column_config.TextColumn("", width="small", disabled=True),
            "상품명": st.column_config.TextColumn("상품명", width="large"),
            "카테고리": st.column_config.SelectboxColumn("카테고리", options=_CATEGORIES, width="medium"),
            "활성": st.column_config.CheckboxColumn("활성", width="small"),
        },
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="product_editor",
    )

    if st.button("변경사항 저장", type="primary", use_container_width=True):
        _apply_changes(sb, fc_id, df, edited)


def _apply_changes(sb, fc_id: str, original_df: pd.DataFrame, edited_df: pd.DataFrame):
    orig_ids = original_df["_id"].tolist() if "_id" in original_df.columns else []
    orig_len = len(orig_ids)
    edited_len = len(edited_df)

    try:
        # 삭제된 행 처리 (편집 후 행 수가 줄어든 경우)
        if edited_len < orig_len:
            # data_editor는 삭제된 행 인덱스를 알 수 없으므로 상품명 기준 비교
            edited_names = set(edited_df["상품명"].tolist())
            for r in original_df.itertuples():
                if r.상품명 not in edited_names:
                    sb.table("fp_products").delete().eq("id", r._id).execute()

        # 기존 행 수정 + 신규 행 추가
        for i, row in edited_df.iterrows():
            name = str(row["상품명"]).strip() if pd.notna(row["상품명"]) else ""
            if not name:
                continue
            cat = row["카테고리"] if pd.notna(row["카테고리"]) else "기타"
            active = bool(row["활성"]) if pd.notna(row["활성"]) else True
            icon = _CAT_ICON.get(cat, "⚪")

            if i < orig_len:  # 기존 행
                pid = orig_ids[i]
                sb.table("fp_products").update({
                    "name": name, "category": cat, "is_active": active, "updated_at": "now()",
                }).eq("id", pid).execute()
            else:  # 신규 행
                sb.table("fp_products").insert({
                    "fc_id": fc_id, "name": name, "category": cat, "is_active": active,
                }).execute()

        st.success("저장되었습니다.")
        st.rerun()
    except Exception as e:
        st.error(f"저장 실패: {e}")
