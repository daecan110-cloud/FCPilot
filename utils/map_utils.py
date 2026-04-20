"""folium 지도 헬퍼 — 상수만 제공 (지도 렌더링은 kakao_map.py)"""

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
