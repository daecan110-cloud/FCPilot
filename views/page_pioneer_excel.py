"""개척지도 — 엑셀 파일 일괄 등록 탭"""
import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from services.pioneer_import import parse_pioneer_excel, bulk_insert_shops


def render_excel_import():
    st.subheader("엑셀 파일로 매장 일괄 등록")
    st.caption("'전체' 시트에서 상호명, 도로명주소, 업태 등을 읽어 자동 등록합니다.")

    uploaded = st.file_uploader(
        "엑셀 파일 업로드 (.xlsx)",
        type=["xlsx"],
        key="pioneer_excel_upload",
    )

    if uploaded is None:
        return

    file_bytes = uploaded.read()
    rows, parse_errors = parse_pioneer_excel(file_bytes)

    if parse_errors:
        for err in parse_errors:
            st.warning(err)
    if not rows:
        st.error("등록할 매장 데이터가 없습니다.")
        return

    st.success(f"파싱 완료: **{len(rows)}건** 매장 발견")

    # 미리보기
    with st.expander("미리보기 (상위 10건)", expanded=True):
        preview = rows[:10]
        st.dataframe(
            [{"상호명": r["shop_name"], "주소": r["address"],
              "업종": r["category"], "메모": r["memo"]} for r in preview],
            use_container_width=True,
        )

    # 중복 체크
    sb = get_supabase_client()
    fc_id = get_current_user_id()
    try:
        existing = sb.table("pioneer_shops").select("shop_name").eq("fc_id", fc_id).execute()
        existing_names = {r["shop_name"] for r in (existing.data or [])}
    except Exception:
        existing_names = set()

    new_rows = [r for r in rows if r["shop_name"] not in existing_names]
    dup_count = len(rows) - len(new_rows)

    if dup_count > 0:
        st.info(f"이미 등록된 매장 **{dup_count}건** 제외 → 신규 **{len(new_rows)}건** 등록 예정")

    if not new_rows:
        st.warning("모든 매장이 이미 등록되어 있습니다.")
        return

    if st.button(f"신규 {len(new_rows)}건 등록", type="primary", use_container_width=True):
        with st.spinner("등록 중..."):
            inserted, insert_errors = bulk_insert_shops(sb, fc_id, new_rows)

        if insert_errors:
            for err in insert_errors:
                st.warning(err)
        if inserted > 0:
            st.success(f"**{inserted}건** 등록 완료!")
            st.balloons()
