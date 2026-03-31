"""Naver Maps 지오코딩 — 주소→좌표 (Nominatim 폴백)"""
import streamlit as st
import requests


def geocode(address: str) -> tuple[float, float] | None:
    """주소 → (lat, lng). Naver NCP 시도 → 실패 시 Nominatim 폴백."""
    if not address:
        return None
    return _geocode_naver(address) or _geocode_nominatim(address)


def _geocode_naver(address: str) -> tuple[float, float] | None:
    try:
        res = requests.get(
            "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode",
            headers={
                "X-NCP-APIGW-API-KEY-ID": st.secrets["naver"]["client_id"],
                "X-NCP-APIGW-API-KEY": st.secrets["naver"]["client_secret"],
            },
            params={"query": address},
            timeout=5,
        )
        addresses = res.json().get("addresses")
        if addresses:
            return float(addresses[0]["y"]), float(addresses[0]["x"])
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


def search_local(query: str, display: int = 5) -> list[dict]:
    """Naver 지역 검색 API"""
    try:
        res = requests.get(
            "https://openapi.naver.com/v1/search/local.json",
            headers={
                "X-Naver-Client-Id": st.secrets["naver"]["client_id"],
                "X-Naver-Client-Secret": st.secrets["naver"]["client_secret"],
            },
            params={"query": query, "display": display},
            timeout=5,
        )
        return res.json().get("items", [])
    except Exception:
        return []
