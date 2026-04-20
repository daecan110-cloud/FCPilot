"""지오코딩 — 주소→좌표 (Kakao → Nominatim 폴백)"""
import streamlit as st
import requests


def geocode(address: str) -> tuple[float, float] | None:
    """주소 → (lat, lng). Kakao 시도 → 실패 시 Nominatim 폴백."""
    if not address:
        return None
    return _geocode_kakao(address) or _geocode_nominatim(address)


def _geocode_kakao(address: str) -> tuple[float, float] | None:
    try:
        res = requests.get(
            "https://dapi.kakao.com/v2/local/search/address.json",
            headers={"Authorization": f"KakaoAK {st.secrets['kakao']['rest_key']}"},
            params={"query": address},
            timeout=5,
        )
        docs = res.json().get("documents")
        if docs:
            return float(docs[0]["y"]), float(docs[0]["x"])
    except Exception:
        pass
    return None


def _geocode_nominatim(address: str) -> tuple[float, float] | None:
    """OpenStreetMap Nominatim — API 키 불필요, 한국 주소 지원"""
    try:
        res = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "kr"},
            headers={"User-Agent": "FCPilot/1.0"},
            timeout=8,
        )
        data = res.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def reverse_geocode(lat: float, lng: float) -> str:
    """좌표 → 주소 (Kakao Reverse Geocoding)"""
    try:
        res = requests.get(
            "https://dapi.kakao.com/v2/local/geo/coord2address.json",
            headers={"Authorization": f"KakaoAK {st.secrets['kakao']['rest_key']}"},
            params={"x": lng, "y": lat},
            timeout=5,
        )
        docs = res.json().get("documents")
        if docs:
            addr = docs[0].get("road_address") or docs[0].get("address")
            if addr:
                return addr.get("address_name", "")
    except Exception:
        pass
    return ""


def search_keyword(query: str, size: int = 5) -> list[dict]:
    """카카오 키워드 검색"""
    try:
        key = st.secrets["kakao"]["rest_key"]
        res = requests.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            headers={"Authorization": f"KakaoAK {key}"},
            params={"query": query, "size": size},
            timeout=5,
        )
        data = res.json()
        return data.get("documents", [])
    except Exception as e:
        st.warning("주소 검색에 실패했습니다. 다시 시도해주세요.")
        return []
