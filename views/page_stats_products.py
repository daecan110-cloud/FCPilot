"""상품 판매 통계 (page_stats에서 분리)"""
import streamlit as st


def render_product_stats(sb, fc_id: str, since, period: str):
    """상품 판매 현황"""
    st.subheader("상품 판매 현황")

    contracts = _load_contracts(sb, fc_id, since)
    contact_logs = _load_contact_logs_with_products(sb, fc_id, since)
    clients_map = _load_clients_map(sb, fc_id)

    if not contracts and not contact_logs:
        st.caption("계약 데이터가 없습니다. 고객 상세에서 계약 정보를 등록하세요.")
        return

    view = st.selectbox(
        "보기", ["판매 랭킹", "제안 vs 실제 판매", "나이대별 상품", "가격대별 분포"],
        key="product_stats_view", label_visibility="collapsed",
    )

    if view == "판매 랭킹":
        _render_sales_ranking(contracts)
    elif view == "제안 vs 실제 판매":
        _render_proposed_vs_actual(sb, fc_id, contact_logs, contracts)
    elif view == "나이대별 상품":
        _render_age_product(contracts, clients_map)
    elif view == "가격대별 분포":
        _render_price_distribution(contracts)


def _load_contracts(sb, fc_id: str, since) -> list:
    try:
        q = sb.table("client_contracts").select("*").eq("fc_id", fc_id)
        if since:
            q = q.gte("created_at", since)
        return q.execute().data or []
    except Exception:
        return []


def _load_contact_logs_with_products(sb, fc_id: str, since) -> list:
    try:
        q = sb.table("contact_logs").select("proposed_product_ids, client_id, created_at").eq("fc_id", fc_id)
        if since:
            q = q.gte("created_at", since)
        rows = q.execute().data or []
        return [r for r in rows if r.get("proposed_product_ids")]
    except Exception:
        return []


def _load_clients_map(sb, fc_id: str) -> dict:
    """client_id → {age_group, name} 매핑"""
    try:
        rows = sb.table("clients").select("id, name, age_group").eq("fc_id", fc_id).execute().data or []
        return {r["id"]: r for r in rows}
    except Exception:
        return {}


def _render_sales_ranking(contracts: list):
    """상품별 판매 건수 랭킹"""
    if not contracts:
        st.caption("계약 데이터가 없습니다.")
        return

    product_counts: dict = {}
    product_premium: dict = {}
    for c in contracts:
        name = c.get("product_name") or "미지정"
        company = c.get("company", "")
        key = f"{company} {name}".strip()
        product_counts[key] = product_counts.get(key, 0) + 1
        product_premium[key] = product_premium.get(key, 0) + (c.get("monthly_premium", 0))

    st.caption(f"총 {len(contracts)}건 계약")
    total = len(contracts)
    for key in sorted(product_counts, key=lambda k: -product_counts[k]):
        cnt = product_counts[key]
        premium = product_premium[key]
        pct = round(cnt / total * 100, 1)
        col_l, col_bar, col_c = st.columns([3, 4, 2])
        col_l.caption(key)
        col_bar.progress(min(pct / 100, 1.0))
        col_c.caption(f"{cnt}건 · 월 {premium:,}원")


def _render_proposed_vs_actual(sb, fc_id: str, contact_logs: list, contracts: list):
    """제안 상품 vs 실제 판매 비교"""
    from views.page_settings_products import get_active_products
    all_prods = {p["id"]: p["name"] for p in get_active_products(sb, fc_id)}

    proposed_counts: dict = {}
    for log in contact_logs:
        for pid in (log.get("proposed_product_ids") or []):
            name = all_prods.get(pid, pid[:8])
            proposed_counts[name] = proposed_counts.get(name, 0) + 1

    actual_counts: dict = {}
    for c in contracts:
        name = c.get("product_name") or "미지정"
        actual_counts[name] = actual_counts.get(name, 0) + 1

    if not proposed_counts and not actual_counts:
        st.caption("데이터가 없습니다.")
        return

    all_names = sorted(set(list(proposed_counts.keys()) + list(actual_counts.keys())))

    st.caption("제안 vs 실제 판매 비교")
    for name in all_names:
        p_cnt = proposed_counts.get(name, 0)
        a_cnt = actual_counts.get(name, 0)
        col_l, col_p, col_a = st.columns([3, 3, 3])
        col_l.caption(name)
        col_p.caption(f"제안 {p_cnt}건")
        col_a.caption(f"판매 {a_cnt}건")
        if p_cnt > 0:
            rate = round(a_cnt / p_cnt * 100, 1)
            st.caption(f"  → 전환율 {rate}%")


def _render_age_product(contracts: list, clients_map: dict):
    """나이대별 상품 분포"""
    if not contracts:
        st.caption("계약 데이터가 없습니다.")
        return

    age_product: dict = {}
    for c in contracts:
        client = clients_map.get(c.get("client_id"), {})
        age = client.get("age_group") or "미지정"
        product = c.get("product_name") or "미지정"
        if age not in age_product:
            age_product[age] = {}
        age_product[age][product] = age_product[age].get(product, 0) + 1

    age_order = ["10대", "20대", "30대", "40대", "50대", "60대 이상", "미지정"]
    sorted_ages = [a for a in age_order if a in age_product]
    sorted_ages += [a for a in age_product if a not in age_order]

    for age in sorted_ages:
        products = age_product[age]
        total = sum(products.values())
        st.markdown(f"**{age}** ({total}건)")
        for prod in sorted(products, key=lambda k: -products[k]):
            cnt = products[prod]
            premium_sum = sum(
                c.get("monthly_premium", 0) for c in contracts
                if (c.get("product_name") or "미지정") == prod
                and (clients_map.get(c.get("client_id"), {}).get("age_group") or "미지정") == age
            )
            st.caption(f"  · {prod}: {cnt}건 (월 평균 {premium_sum // max(cnt, 1):,}원)")


def _render_price_distribution(contracts: list):
    """월보험료 가격대별 분포"""
    if not contracts:
        st.caption("계약 데이터가 없습니다.")
        return

    brackets = [
        ("5만원 미만", 0, 50000),
        ("5~10만원", 50000, 100000),
        ("10~20만원", 100000, 200000),
        ("20~30만원", 200000, 300000),
        ("30~50만원", 300000, 500000),
        ("50만원 이상", 500000, float("inf")),
    ]

    dist = {label: 0 for label, _, _ in brackets}
    for c in contracts:
        premium = c.get("monthly_premium", 0)
        for label, lo, hi in brackets:
            if lo <= premium < hi:
                dist[label] += 1
                break

    total = len(contracts)
    st.caption(f"총 {total}건 · 평균 월보험료 {sum(c.get('monthly_premium', 0) for c in contracts) // max(total, 1):,}원")
    for label, _, _ in brackets:
        cnt = dist[label]
        if cnt == 0:
            continue
        pct = round(cnt / total * 100, 1)
        col_l, col_bar, col_c = st.columns([2, 5, 1])
        col_l.caption(label)
        col_bar.progress(min(pct / 100, 1.0))
        col_c.caption(f"{cnt}건 ({pct}%)")
