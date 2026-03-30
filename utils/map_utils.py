"""folium 지도 헬퍼"""
import folium

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
