"""상품 관리 섹션 — 설정 탭에서 호출 (이름 + 카테고리만)"""
import pandas as pd
import streamlit as st
from auth import get_current_user_id
from utils.helpers import safe_error
from config import INSURANCE_CATEGORIES as _CATEGORIES, INSURANCE_CAT_ICON as _CAT_ICON
from utils.supabase_client import get_supabase_client


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
        st.error(safe_error("조회", e))
        return

    # 상품 없고 초기화 미완료 → admin 상품 한 번만 복사
    if not rows and not _is_products_initialized(sb, fc_id):
        _copy_admin_products(sb, fc_id)
        try:
            rows = sb.table("fp_products").select("*").eq("fc_id", fc_id).order("name").execute().data or []
        except Exception:
            pass

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


def _is_products_initialized(sb, fc_id: str) -> bool:
    try:
        res = sb.table("users_settings").select("products_initialized").eq("id", fc_id).execute()
        return bool(res.data and res.data[0].get("products_initialized"))
    except Exception:
        return False


def _copy_admin_products(sb, fc_id: str):
    """admin 상품을 현재 사용자에게 한 번만 복사"""
    try:
        from utils.db_admin import get_admin_client
        admin_sb = get_admin_client()

        # admin fc_id 조회
        admin_res = admin_sb.table("users_settings").select("id").eq("role", "admin").execute()
        if not admin_res.data:
            return
        admin_id = admin_res.data[0]["id"]
        if admin_id == fc_id:
            # 본인이 admin이면 복사 불필요, 플래그만 세팅
            admin_sb.table("users_settings").update({"products_initialized": True}).eq("id", fc_id).execute()
            return

        # admin 상품 가져오기
        prod_res = admin_sb.table("fp_products").select("name, category, is_active").eq("fc_id", admin_id).execute()
        admin_products = prod_res.data or []

        # 현재 사용자 계정으로 복사
        if admin_products:
            rows_to_insert = [
                {"fc_id": fc_id, "name": p["name"], "category": p["category"], "is_active": p["is_active"]}
                for p in admin_products
            ]
            admin_sb.table("fp_products").insert(rows_to_insert).execute()

        # 초기화 완료 플래그 저장
        admin_sb.table("users_settings").update({"products_initialized": True}).eq("id", fc_id).execute()
    except Exception:
        pass


def _apply_changes(sb, fc_id: str, original_df: pd.DataFrame, edited_df: pd.DataFrame):
    orig_ids = original_df["_id"].tolist() if "_id" in original_df.columns else []
    orig_len = len(orig_ids)
    edited_len = len(edited_df)

    try:
        # 삭제된 행 처리: edited_df에 없는 원본 인덱스 찾기
        edited_indices = set(edited_df.index.tolist())
        for i, oid in enumerate(orig_ids):
            if i not in edited_indices:
                sb.table("fp_products").delete().eq("id", oid).eq("fc_id", fc_id).execute()

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
                from datetime import datetime, timezone
                sb.table("fp_products").update({
                    "name": name, "category": cat, "is_active": active,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", pid).eq("fc_id", fc_id).execute()
            else:  # 신규 행
                sb.table("fp_products").insert({
                    "fc_id": fc_id, "name": name, "category": cat, "is_active": active,
                }).execute()

        st.success("저장되었습니다.")
        st.rerun()
    except Exception as e:
        st.error(safe_error("저장", e))
