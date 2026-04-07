"""Kakao Maps — 정적 HTML + postMessage 방식 지도 컴포넌트"""
import json
import hashlib
import streamlit as st
import streamlit.components.v1 as components


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
    """정적 HTML iframe + postMessage로 지도 데이터 전달"""
    key = _app_key()
    data_json = _safe_json(data)
    # 데이터 해시로 고유 iframe key 생성 (중복 방지)
    data_hash = hashlib.md5(data_json.encode()).hexdigest()[:8]

    iframe_url = f"/_stcore/static/kakao_map.html#key={key}&mode={mode}"

    # 부모 페이지에서 iframe에 postMessage로 데이터 전달
    wrapper_html = f"""
    <iframe id="kakaoMap_{data_hash}" src="{iframe_url}"
      width="100%" height="{height}" frameborder="0"
      style="border:none;border-radius:8px"></iframe>
    <script>
    (function(){{
      var iframe = document.getElementById('kakaoMap_{data_hash}');
      var data = {data_json};
      function sendData(){{
        iframe.contentWindow.postMessage({{type:'mapData', items:data}}, '*');
      }}
      // SDK 준비 완료 메시지 수신 시 데이터 전송
      window.addEventListener('message', function(e){{
        if(e.data && e.data.type === 'mapReady') sendData();
      }});
      // iframe 이미 로드된 경우 대비
      iframe.addEventListener('load', function(){{
        setTimeout(sendData, 500);
      }});
    }})();
    </script>
    """
    components.html(wrapper_html, height=height + 10)
