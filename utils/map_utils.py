"""folium 지도 헬퍼"""
import folium
from folium.plugins import AntPath

STATUS_COLORS = {
    "active": "blue",
    "visited": "orange",
    "contracted": "green",
    "rejected": "red",
}

STATUS_LABELS = {
    "active": "등록",
    "visited": "방문",
    "contracted": "계약",
    "rejected": "거절",
}

VISIT_RESULT_LABELS = {
    "": "기록 없음",
    "interest": "관심",
    "rejected": "거절",
    "revisit": "재방문 예정",
    "contracted": "계약 성사",
}


def create_map(shops: list, center: tuple = (37.5665, 126.9780), zoom: int = 13) -> folium.Map:
    """매장 목록으로 folium 지도 생성"""
    if shops:
        lats = [s["lat"] for s in shops if s.get("lat")]
        lngs = [s["lng"] for s in shops if s.get("lng")]
        if lats and lngs:
            center = (sum(lats) / len(lats), sum(lngs) / len(lngs))

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    for s in shops:
        if not s.get("lat") or not s.get("lng"):
            continue
        color = STATUS_COLORS.get(s.get("status", "active"), "blue")
        status = STATUS_LABELS.get(s.get("status", "active"), "등록")
        popup = f"<b>{s.get('shop_name', '')}</b><br>{s.get('address', '')}<br>상태: {status}"
        folium.Marker(
            location=[s["lat"], s["lng"]],
            popup=folium.Popup(popup, max_width=250),
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(m)

    return m


def create_route_map(
    visits: list,
    center: tuple = (37.5665, 126.9780),
    zoom: int = 14,
) -> folium.Map:
    """방문 기록으로 동선 지도 생성 (번호 마커 + polyline)

    visits: [{"lat", "lng", "shop_name", "visit_date", "result", "memo", "order"}]
    """
    coords = [(v["lat"], v["lng"]) for v in visits if v.get("lat") and v.get("lng")]
    if coords:
        center = (sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords))

    m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    # 번호 마커
    for v in visits:
        if not v.get("lat") or not v.get("lng"):
            continue
        order = v.get("order", 0)
        result = VISIT_RESULT_LABELS.get(v.get("result", ""), "")
        popup_html = (
            f"<b>#{order} {v.get('shop_name', '')}</b><br>"
            f"날짜: {v.get('visit_date', '')}<br>"
            f"결과: {result}<br>"
            f"{v.get('memo', '')}"
        )
        folium.Marker(
            location=[v["lat"], v["lng"]],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.DivIcon(
                html=f'<div style="background:#1E88E5;color:white;border-radius:50%;'
                     f'width:28px;height:28px;text-align:center;line-height:28px;'
                     f'font-weight:bold;font-size:14px;border:2px solid white;'
                     f'box-shadow:0 2px 4px rgba(0,0,0,0.3)">{order}</div>',
                icon_size=(28, 28),
                icon_anchor=(14, 14),
            ),
        ).add_to(m)

    # 동선 연결 (polyline)
    if len(coords) >= 2:
        AntPath(
            locations=coords,
            color="#1E88E5",
            weight=3,
            opacity=0.7,
            dash_array=[10, 20],
        ).add_to(m)

    return m
