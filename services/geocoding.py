"""Naver Maps 지오코딩 — 주소→좌표"""
import streamlit as st
import requests


def geocode(address: str) -> tuple[float, float] | None:
    """주소 → (lat, lng). 실패 시 None."""
    if not address:
        return None

    headers = {
        "X-NCP-APIGW-API-KEY-ID": st.secrets["naver"]["client_id"],
        "X-NCP-APIGW-API-KEY": st.secrets["naver"]["client_secret"],
    }
    params = {"query": address}

    try:
        res = requests.get(
            "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode",
            headers=headers,
            params=params,
            timeout=5,
        )
        data = res.json()
        if data.get("addresses"):
            addr = data["addresses"][0]
            return float(addr["y"]), float(addr["x"])
    except Exception:
        pass
    return None


def search_local(query: str, display: int = 5) -> list[dict]:
    """Naver 지역 검색 API"""
    headers = {
        "X-Naver-Client-Id": st.secrets["naver"]["client_id"],
        "X-Naver-Client-Secret": st.secrets["naver"]["client_secret"],
    }
    params = {"query": query, "display": display}

    try:
        res = requests.get(
            "https://openapi.naver.com/v1/search/local.json",
            headers=headers,
            params=params,
            timeout=5,
        )
        data = res.json()
        return data.get("items", [])
    except Exception:
        return []
