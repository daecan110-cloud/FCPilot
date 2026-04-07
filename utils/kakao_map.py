"""지도 컴포넌트 — folium + streamlit-folium 기반"""
import folium
from folium.plugins import PolyLineTextPath
import streamlit as st
from streamlit_folium import st_folium


_STATUS_COLORS = {
    "active": "#2196F3",
    "visited": "#FF9800",
    "contracted": "#4CAF50",
    "rejected": "#F44336",
}
_STATUS_LABELS = {
    "active": "등록",
    "visited": "방문",
    "contracted": "계약",
    "rejected": "거절",
}
_RESULT_LABELS = {
    "": "기록 없음",
    "interest": "관심",
    "rejected": "거절",
    "revisit": "재방문 예정",
    "contracted": "계약 성사",
}


def pioneer_map_html(shops: list, height: int = 500, key: str = "pioneer") -> None:
    """개척 매장 지도 (상태별 색상 마커)"""
    valid = [s for s in shops if s.get("lat") and s.get("lng")]

    if not valid:
        st.info("좌표가 있는 매장이 없습니다.")
        return

    avg_lat = sum(s["lat"] for s in valid) / len(valid)
    avg_lng = sum(s["lng"] for s in valid) / len(valid)

    m = folium.Map(location=[avg_lat, avg_lng], zoom_start=14, tiles="OpenStreetMap")

    for s in valid:
        status = _STATUS_LABELS.get(s.get("status", "active"), "등록")
        color = _STATUS_COLORS.get(s.get("status", "active"), "#2196F3")
        name = s.get("shop_name", "")
        cat = s.get("category", "")
        addr = s.get("address", "")
        memo = s.get("memo") or ""

        popup_html = (
            f"<b>{_esc(name)}</b><br>"
            f"상태: <span style='color:{color}'>{_esc(status)}</span><br>"
            + (f"업종: {_esc(cat)}<br>" if cat else "")
            + (f"<small>{_esc(addr)}</small><br>" if addr else "")
            + (f"<small>{_esc(memo)}</small>" if memo else "")
        )

        folium.CircleMarker(
            location=[s["lat"], s["lng"]],
            radius=8,
            color="#fff",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=name,
        ).add_to(m)

    _fit_bounds(m, valid)
    st_folium(m, height=height, use_container_width=True, returned_objects=[], key=key)


def route_map_html(visits: list, height: int = 420, key: str = "route") -> None:
    """방문 동선 지도 (번호 마커 + 폴리라인)"""
    valid = [v for v in visits if v.get("lat") and v.get("lng")]

    if not valid:
        st.info("좌표가 있는 방문 기록이 없습니다.")
        return

    avg_lat = sum(v["lat"] for v in valid) / len(valid)
    avg_lng = sum(v["lng"] for v in valid) / len(valid)

    m = folium.Map(location=[avg_lat, avg_lng], zoom_start=14, tiles="OpenStreetMap")

    coords = []
    for v in valid:
        lat, lng = v["lat"], v["lng"]
        coords.append([lat, lng])
        order = v.get("order", 0)
        name = v.get("shop_name", "")
        result = _RESULT_LABELS.get(v.get("result", ""), "")
        addr = v.get("address", "")
        memo = v.get("memo") or ""

        popup_html = (
            f"<b>#{order} {_esc(name)}</b><br>"
            + (f"결과: {_esc(result)}<br>" if result else "")
            + (f"{_esc(memo)}<br>" if memo else "")
            + (f"<small>{_esc(addr)}</small>" if addr else "")
        )

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=260),
            tooltip=f"#{order} {name}",
            icon=folium.DivIcon(
                html=f'<div style="background:#1E88E5;color:#fff;border-radius:50%;'
                     f'width:28px;height:28px;text-align:center;line-height:28px;'
                     f'font-weight:bold;font-size:13px;border:2px solid #fff;'
                     f'box-shadow:0 2px 6px rgba(0,0,0,.4)">{order}</div>',
                icon_size=(28, 28),
                icon_anchor=(14, 14),
            ),
        ).add_to(m)

    if len(coords) >= 2:
        folium.PolyLine(
            coords,
            color="#1E88E5",
            weight=4,
            opacity=0.8,
        ).add_to(m)

    _fit_bounds(m, valid)
    st_folium(m, height=height, use_container_width=True, returned_objects=[], key=key)


def _fit_bounds(m: folium.Map, items: list) -> None:
    """지도 범위를 데이터에 맞게 조정"""
    if len(items) == 1:
        m.location = [items[0]["lat"], items[0]["lng"]]
        m.zoom_start = 16
    else:
        lats = [i["lat"] for i in items]
        lngs = [i["lng"] for i in items]
        m.fit_bounds([[min(lats), min(lngs)], [max(lats), max(lngs)]])


def _esc(s: str) -> str:
    """HTML 특수문자 이스케이프"""
    if not s:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
