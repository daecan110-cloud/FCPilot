"""Kakao Maps JavaScript API 기반 지도 컴포넌트"""
import json
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


def route_map_html(visits: list, height: int = 420) -> None:
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
    _render(_safe_json(js_data), "route", height)


def pioneer_map_html(shops: list, height: int = 500) -> None:
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
    _render(_safe_json(js_data), "pioneer", height)


def _render(data_json: str, mode: str, height: int) -> None:
    key = _app_key()
    script = _ROUTE_SCRIPT if mode == "route" else _PIONEER_SCRIPT

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<meta name="referrer" content="origin">
<style>
  html,body{{margin:0;padding:0;width:100%;height:{height}px}}
  #map{{width:100%;height:{height}px}}
  #err{{color:red;padding:10px;font-size:14px;position:absolute;z-index:999}}
  .iw{{padding:10px;font-size:13px;line-height:1.6;min-width:160px;max-width:260px}}
  .iw b{{font-size:14px;display:block;margin-bottom:2px}}
  .iw small{{color:#888}}
</style>
</head><body>
<div id="err"></div>
<div id="map"></div>
<script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={key}&autoload=false"
  onerror="document.getElementById('err').innerText='SDK 로드 실패'"></script>
<script>
var DATA={data_json};
if(typeof kakao==='undefined'){{document.getElementById('err').innerText='SDK 미로드';}}
else{{kakao.maps.load(function(){{try{{{script}}}catch(e){{document.getElementById('err').innerText=e.message;}}}});}};
</script>
</body></html>"""
    st.html(html)


_ESC = "function _e(s){if(!s)return'';var d=document.createElement('div');d.appendChild(document.createTextNode(s));return d.innerHTML;}"

_ROUTE_SCRIPT = _ESC + """
var valid=DATA.filter(function(v){return v.lat&&v.lng;});
var cLat=valid.length?valid.reduce(function(s,v){return s+v.lat;},0)/valid.length:37.5665;
var cLng=valid.length?valid.reduce(function(s,v){return s+v.lng;},0)/valid.length:126.9780;
var map=new kakao.maps.Map(document.getElementById('map'),{center:new kakao.maps.LatLng(cLat,cLng),level:5});
map.addControl(new kakao.maps.MapTypeControl(),kakao.maps.ControlPosition.TOPRIGHT);
map.addControl(new kakao.maps.ZoomControl(),kakao.maps.ControlPosition.RIGHT);
var coords=[];
valid.forEach(function(v){
  var pos=new kakao.maps.LatLng(v.lat,v.lng);coords.push(pos);
  var content='<div style="background:#1E88E5;color:#fff;border-radius:50%;width:30px;height:30px;text-align:center;line-height:30px;font-weight:bold;font-size:14px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.4);cursor:pointer">'+v.order+'</div>';
  new kakao.maps.CustomOverlay({position:pos,content:content,yAnchor:0.5,xAnchor:0.5,map:map});
  var iwC='<div class="iw"><b>#'+v.order+' '+_e(v.name)+'</b>'+(v.result?'\\uacb0\\uacfc: '+_e(v.result)+'<br>':'')+(v.memo?_e(v.memo)+'<br>':'')+(v.addr?'<small>'+_e(v.addr)+'</small>':'')+'</div>';
  var iw=new kakao.maps.InfoWindow({content:iwC,removable:true});
  var mk=new kakao.maps.Marker({position:pos,map:map,opacity:0});
  kakao.maps.event.addListener(mk,'click',(function(m,w){return function(){w.open(map,m);};})(mk,iw));
});
if(coords.length>=2){new kakao.maps.Polyline({map:map,path:coords,strokeWeight:4,strokeColor:'#1E88E5',strokeOpacity:0.8,strokeStyle:'solid'});}
if(coords.length>0){var b=new kakao.maps.LatLngBounds();coords.forEach(function(c){b.extend(c);});map.setBounds(b,50,50,50,50);}
"""

_PIONEER_SCRIPT = _ESC + """
var valid=DATA.filter(function(s){return s.lat&&s.lng;});
var cLat=valid.length?valid.reduce(function(s,v){return s+v.lat;},0)/valid.length:37.5665;
var cLng=valid.length?valid.reduce(function(s,v){return s+v.lng;},0)/valid.length:126.9780;
var map=new kakao.maps.Map(document.getElementById('map'),{center:new kakao.maps.LatLng(cLat,cLng),level:6});
map.addControl(new kakao.maps.MapTypeControl(),kakao.maps.ControlPosition.TOPRIGHT);
map.addControl(new kakao.maps.ZoomControl(),kakao.maps.ControlPosition.RIGHT);
DATA.forEach(function(s){
  if(!s.lat||!s.lng)return;
  var pos=new kakao.maps.LatLng(s.lat,s.lng);
  var dot='<div style="background:'+s.color+';width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4);cursor:pointer"></div>';
  new kakao.maps.CustomOverlay({position:pos,content:dot,yAnchor:0.5,xAnchor:0.5,map:map});
  var iwC='<div class="iw"><b>'+_e(s.name)+'</b>'+'\\uc0c1\\ud0dc: <span style="color:'+s.color+'">'+_e(s.status)+'</span><br>'+(s.cat?'\\uc5c5\\uc885: '+_e(s.cat)+'<br>':'')+(s.addr?'<small>'+_e(s.addr)+'</small>':'')+(s.memo?'<br><small>'+_e(s.memo)+'</small>':'')+'</div>';
  var iw=new kakao.maps.InfoWindow({content:iwC,removable:true});
  var mk=new kakao.maps.Marker({position:pos,map:map,opacity:0});
  kakao.maps.event.addListener(mk,'click',(function(m,w){return function(){w.open(map,m);};})(mk,iw));
});
if(valid.length>0){var b=new kakao.maps.LatLngBounds();valid.forEach(function(s){b.extend(new kakao.maps.LatLng(s.lat,s.lng));});map.setBounds(b,50,50,50,50);}
"""
