---
name: new-page
description: >
  새 페이지/탭 추가 보일러플레이트 생성. "새 페이지 만들어줘", "탭 추가해줘" 요청 시 활성화.
  FCPilot 코딩 컨벤션에 맞는 파일 구조를 자동 생성한다.
---

## 절차

### 1. 정보 수집
영민에게 확인:
- 페이지 이름 (예: "비교표")
- 메뉴 위치 (예: "보장분석 다음")
- DB 테이블 필요 여부
- 주요 기능 설명

### 2. 파일 생성
`views/page_{name}.py` 생성:

```python
"""{한글 설명} 탭"""
import streamlit as st

from auth import get_current_user_id
from utils.supabase_client import get_supabase_client
from utils.helpers import safe_error


def render():
    st.header("{한글 제목}")
    sb = get_supabase_client()
    fc_id = get_current_user_id()
    if not fc_id:
        st.warning("로그인이 필요합니다.")
        return

    # TODO: 구현
    st.info("구현 예정")
```

### 3. app.py 라우팅 추가
기존 `elif tab ==` 패턴에 맞춰 추가:
```python
elif tab == "{이모지} {메뉴명}":
    from views.page_{name} import render
    render()
```

### 4. 메뉴 순서 반영
`app.py`의 `menu` 리스트 3개(영업모드별)에 새 탭 추가.

## 규칙 (CLAUDE.md 준수)
- 200줄 이하
- `safe_error()` 사용
- DB 쿼리에 `.eq("fc_id", fc_id)` 필수
- `unsafe_allow_html` 사용 시 `esc()` 필수
- 새 DB 테이블 필요 시 `sql/` 마이그레이션 + `db_migrate.py` 등록

## 주의사항
- app.py는 라우터 역할만. 로직 넣지 마.
- 필요하면 `services/` 파일도 함께 생성.
- 기존 페이지 import 패턴 참고: `from views.page_xxx import render`
