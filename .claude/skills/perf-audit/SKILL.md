---
name: perf-audit
description: >
  성능 병목 자동 탐지. "성능 점검", "느린 곳", "캐싱 점검", "최적화 확인" 요청 시 활성화.
  캐싱 누락, N+1, 무거운 렌더링 등을 자동으로 찾아낸다.
---

## 점검 항목

### 1. 캐싱 누락 DB 쿼리 탐지
views/ 전체에서 `.execute()` 호출을 찾아, 해당 함수에 `@st.cache_data`가 없으면 보고:
```bash
# 패턴: .execute()가 있지만 @st.cache_data가 없는 함수
grep -n ".execute()" views/*.py | ...
```

### 2. N+1 쿼리 패턴 탐지
for 루프 안에서 `.execute()`가 호출되는 패턴:
```
for ... in ...:
    sb.table(...).select(...).execute()  # N+1!
```

### 3. @st.fragment 미적용 탐지
`st.tabs()` 사용 시 각 탭 내용이 `@st.fragment`로 감싸져 있는지 확인.
무거운 탭(DB 쿼리, 지도 렌더링 포함)이 fragment 없이 매 rerun마다 실행되면 보고.

### 4. 캐시 TTL 일관성
`@st.cache_data(ttl=...)` 값 수집하여 테이블로 표시:
| 함수 | TTL | 위치 |
동일 데이터를 다른 TTL로 캐싱하는 경우 경고.

### 5. 무거운 import 확인
`render()` 함수 내부에서 무거운 모듈을 import하는 패턴:
```python
def render():
    from heavy_module import ...  # 매 rerun 실행
```

## 출력 형식
```
🔍 성능 점검 결과
─────────────────
캐싱 누락: N건
  - views/page_xxx.py:NN — sb.table("...").execute() 캐싱 없음
N+1 패턴: N건
  - views/page_xxx.py:NN — for 루프 내 execute()
fragment 미적용: N건
TTL 불일치: N건
```

## 주의사항
- 코드 수정하지 마. 보고만 한다.
- services/ 레이어의 쿼리는 호출처(views/)에서 캐싱하는 패턴이므로 false positive 주의.
- `_sb` prefix 파라미터는 st.cache_data의 해시 제외 규칙이므로 정상.
