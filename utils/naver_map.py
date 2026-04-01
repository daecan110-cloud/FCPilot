"""Naver Maps JavaScript API v3 기반 지도 컴포넌트 HTML 생성기"""
import json
import streamlit as st


def _safe_json(data) -> str:
    """JSON 직렬화 + HTML 특수문자 이스케이프 (script 태그 인젝션 방지)"""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")

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


def _client_id() -> str:
    try:
        return st.secrets["naver"]["client_id"]
    except Exception:
        return ""


def route_map_html(visits: list, height: int = 420) -> str:
    """방문 동선 지도 HTML (번호 마커 + 화살표 폴리라인)

    visits: [{"lat", "lng", "shop_name", "address", "result", "memo", "order"}]
    """
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
    return _html(_safe_json(js_data), "route", height)


def pioneer_map_html(shops: list, height: int = 500) -> str:
    """개척 매장 지도 HTML (상태별 색상 마커)

    shops: pioneer_shops 테이블 rows
    """
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
    return _html(_safe_json(js_data), "pioneer", height)


def _html(data_json: str, mode: str, height: int) -> str:
    cid = _client_id()
    if mode == "route":
        map_script = _ROUTE_SCRIPT
    else:
        map_script = _PIONEER_SCRIPT

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  html,body{{margin:0;padding:0;width:100%;height:100%}}
  #map{{width:100%;height:{height}px}}
  .iw{{padding:8px;font-size:13px;line-height:1.6;min-width:160px}}
  .iw b{{font-size:14px;display:block;margin-bottom:2px}}
  .iw small{{color:#888}}
</style>
</head><body>
<div id="map"></div>
<script src="https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId={cid}"></script>
<script>
var DATA = {data_json};
{map_script}
</script>
</body></html>"""


_ROUTE_SCRIPT = """
var valid = DATA.filter(function(v){return v.lat && v.lng;});
var center = valid.length
  ? new naver.maps.LatLng(
      valid.reduce(function(s,v){return s+v.lat;},0)/valid.length,
      valid.reduce(function(s,v){return s+v.lng;},0)/valid.length)
  : new naver.maps.LatLng(37.5665,126.9780);

var map = new naver.maps.Map('map',{
  center:center, zoom:14,
  mapTypeControl:true,
  mapTypeControlOptions:{style:naver.maps.MapTypeControlStyle.BUTTON,position:naver.maps.Position.TOP_RIGHT},
  zoomControl:true,
  zoomControlOptions:{position:naver.maps.Position.TOP_RIGHT}
});

var coords=[];
valid.forEach(function(v){
  var pos=new naver.maps.LatLng(v.lat,v.lng);
  coords.push(pos);
  var m=new naver.maps.Marker({position:pos,map:map,icon:{
    content:'<div style="background:#1E88E5;color:#fff;border-radius:50%;width:30px;height:30px;text-align:center;line-height:30px;font-weight:bold;font-size:14px;border:2px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.4)">'+v.order+'</div>',
    anchor:new naver.maps.Point(15,15)
  }});
  var iw=new naver.maps.InfoWindow({content:
    '<div class="iw"><b>#'+v.order+' '+v.name+'</b>'+
    (v.result?'결과: '+v.result+'<br>':'')+
    (v.memo?v.memo+'<br>':'')+
    (v.addr?'<small>'+v.addr+'</small>':'')+
    '</div>'
  });
  naver.maps.Event.addListener(m,'click',(function(m,iw){return function(){iw.getMap()?iw.close():iw.open(map,m);};})(m,iw));
});
if(coords.length>=2){
  new naver.maps.Polyline({map:map,path:coords,strokeColor:'#1E88E5',strokeWeight:4,strokeOpacity:.8,
    endIcon:naver.maps.PointingIcon.BLOCK_ARROW,endIconSize:12});
}
if(coords.length>0){
  var b=new naver.maps.LatLngBounds();
  coords.forEach(function(c){b.extend(c);});
  map.fitBounds(b,{top:50,right:50,bottom:50,left:50});
}
"""

_PIONEER_SCRIPT = """
var valid = DATA.filter(function(s){return s.lat && s.lng;});
var center = valid.length
  ? new naver.maps.LatLng(
      valid.reduce(function(s,v){return s+v.lat;},0)/valid.length,
      valid.reduce(function(s,v){return s+v.lng;},0)/valid.length)
  : new naver.maps.LatLng(37.5665,126.9780);

var map = new naver.maps.Map('map',{
  center:center, zoom:13,
  mapTypeControl:true,
  mapTypeControlOptions:{style:naver.maps.MapTypeControlStyle.BUTTON,position:naver.maps.Position.TOP_RIGHT},
  zoomControl:true,
  zoomControlOptions:{position:naver.maps.Position.TOP_RIGHT}
});

DATA.forEach(function(s){
  if(!s.lat||!s.lng) return;
  var pos=new naver.maps.LatLng(s.lat,s.lng);
  var m=new naver.maps.Marker({position:pos,map:map,icon:{
    content:'<div style="background:'+s.color+';width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>',
    anchor:new naver.maps.Point(7,7)
  }});
  var iw=new naver.maps.InfoWindow({content:
    '<div class="iw"><b>'+s.name+'</b>'+
    '상태: <span style="color:'+s.color+'">'+s.status+'</span><br>'+
    (s.cat?'업종: '+s.cat+'<br>':'')+
    (s.addr?'<small>'+s.addr+'</small>':'')+
    (s.memo?'<br><small>'+s.memo+'</small>':'')+
    '</div>'
  });
  naver.maps.Event.addListener(m,'click',(function(m,iw){return function(){iw.getMap()?iw.close():iw.open(map,m);};})(m,iw));
});

if(valid.length>0){
  var b=new naver.maps.LatLngBounds();
  valid.forEach(function(s){b.extend(new naver.maps.LatLng(s.lat,s.lng));});
  map.fitBounds(b,{top:50,right:50,bottom:50,left:50});
}
"""
