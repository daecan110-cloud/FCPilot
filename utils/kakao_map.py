"""Kakao Maps — 정적 HTML + postMessage 방식 지도 컴포넌트"""
import json
import hashlib
import urllib.parse
import streamlit as st


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


def _app_key() -> str:
    try:
        return st.secrets["kakao"]["js_key"]
    except Exception:
        return ""


def _safe_json(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")


def route_map_html(visits: list, height: int = 420) -> str:
    """방문 동선 지도 (번호 마커 + 폴리라인)"""
    js_data = [
        {
            "order": v.get("order", 0),
            "lat": v.get("lat"),
            "lng": v.get("lng"),
            "name": v.get("shop_name", ""),
            "addr": v.get("address", ""),
            "result": _RESULT_LABELS.get(v.get("result", ""), ""),
            "memo": (v.get("memo") or ""),
        }
        for v in visits
    ]
    return _render(js_data, "route", height)


def pioneer_map_html(shops: list, height: int = 500) -> str:
    """개척 매장 지도 (상태별 색상 마커)"""
    js_data = [
        {
            "lat": s.get("lat"),
            "lng": s.get("lng"),
            "name": s.get("shop_name", ""),
            "addr": s.get("address", ""),
            "status": _STATUS_LABELS.get(s.get("status", "active"), "등록"),
            "color": _STATUS_COLORS.get(s.get("status", "active"), "#2196F3"),
            "cat": s.get("category", ""),
            "memo": (s.get("memo") or ""),
        }
        for s in shops
    ]
    return _render(js_data, "pioneer", height)


def _render(data: list, mode: str, height: int) -> None:
    """정적 HTML iframe으로 지도 렌더링 (앱 도메인에서 서빙)"""
    key = _app_key()
    data_json = _safe_json(data)
    encoded = urllib.parse.quote(data_json)

    iframe_url = f"/_stcore/static/kakao_map.html#key={key}&mode={mode}&data={encoded}"

    st.iframe(iframe_url, height=height)
