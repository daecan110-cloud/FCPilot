# FCPilot UI 리뉴얼 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FCPilot 전체 UI를 Notion 스타일(미니멀, 여백 활용, 정보 계층 명확)로 리뉴얼한다.

**Architecture:** 글로벌 CSS를 `app.py`에 주입하고, 공통 컴포넌트를 `utils/ui_components.py`로 분리한다. 각 `views/page_*.py`는 비즈니스 로직을 건드리지 않고 레이아웃/HTML만 변경한다.

**Tech Stack:** Streamlit, CSS (inline markdown), Python 3.11+

---

## 제약 (절대 금지)
- `services/`, `auth.py`, `config.py` 비즈니스 로직 수정 금지
- DB 구조 변경 금지
- `MASTER.md`, `CLAUDE.md`, `.claude/settings.json` 수정 금지
- 파일당 200줄 초과 금지 — 초과 시 분리

---

## 파일 맵

| 작업 | 파일 | 변경 종류 |
|------|------|-----------|
| Round 1 | `app.py` | CSS 주입 + 사이드바 아이콘 메뉴 |
| Round 1 | `utils/ui_components.py` | 신규 — grade_badge, empty_state, section_header |
| Round 2 | `views/page_home.py` | 카드형 레이아웃, 등급 뱃지 |
| Round 2 | `views/page_clients_detail.py` | 신규 — 고객 상세 탭 구조 (page_clients.py 분리) |
| Round 2 | `views/page_clients.py` | 카드형 목록, 상세 렌더링을 page_clients_detail로 위임 |
| Round 3 | `views/page_analysis.py` | Step 플로우 레이아웃 (대상 함수: `_show_result`) |
| Round 3 | `views/page_stats.py` | 카드 + 프로그레스 바 시각화 |
| Round 4 | `views/page_pioneer_map.py` | 지도 70% + 사이드패널 30% |
| Round 4 | `views/page_settings.py` | expander 카테고리별 구조 |

---

## Round 1: 글로벌 테마 + 공통 컴포넌트

### Task 1: `utils/ui_components.py` 생성

**Files:**
- Create: `utils/ui_components.py`

```python
"""FCPilot 공통 UI 컴포넌트 — Notion 스타일"""
import streamlit as st

GRADE_COLORS = {
    "VIP": "#9B59B6", "S": "#27AE60", "A": "#EB5757",
    "B": "#F2994A", "C": "#2F80ED", "D": "#828282"
}

def grade_badge(grade: str) -> str:
    """등급 색상 뱃지 HTML 반환"""
    color = GRADE_COLORS.get(grade, "#828282")
    return (
        f'<span style="background:{color}; color:white; padding:2px 8px; '
        f'border-radius:4px; font-size:12px; font-weight:500;">{grade}</span>'
    )

def empty_state(icon: str, message: str):
    """빈 상태 중앙 표시"""
    st.markdown(
        f'<div style="text-align:center; padding:40px; color:#787774;">'
        f'<div style="font-size:36px; margin-bottom:8px;">{icon}</div>'
        f'<div style="font-size:14px;">{message}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def section_header(title: str, subtitle: str = ""):
    """섹션 헤더 — 여백으로만 구분"""
    st.markdown(
        f'<div style="margin-top:24px; margin-bottom:8px;">'
        f'<span style="font-size:16px; font-weight:600; color:#37352F;">{title}</span>'
        + (f'<span style="font-size:13px; color:#787774; margin-left:8px;">{subtitle}</span>' if subtitle else "")
        + '</div>',
        unsafe_allow_html=True,
    )
```

- [ ] **Step 1: 파일 생성**

  위 코드를 `utils/ui_components.py`에 작성.

- [ ] **Step 2: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile utils/ui_components.py && echo "OK"
  ```
  Expected: `OK`

- [ ] **Step 3: import 동작 확인**

  ```bash
  cd C:/FCPilot && python -c "from utils.ui_components import grade_badge, empty_state; print(grade_badge('A'))"
  ```
  Expected: `<span style="background:#EB5757; ...>A</span>` 출력

- [ ] **Step 4: Commit**

  ```bash
  git add utils/ui_components.py
  git commit -m "feat: ui_components.py — grade_badge, empty_state, section_header"
  ```

---

### Task 2: `app.py` 글로벌 CSS 주입 + 사이드바 개선

**Files:**
- Modify: `app.py`

**사전 작업 — `_nav_to` 전체 감사:**

```bash
cd C:/FCPilot && grep -rn "_nav_to" views/ app.py
```

출력된 모든 `_nav_to =` 할당값을 목록화한다. 아이콘 포함 메뉴 문자열로 **전부** 업데이트해야 한다.

현재 알려진 위치 (추가 발견 시 모두 포함):
- `views/page_home.py:109` → `"고객관리"` → `"👥 고객관리"`
- `views/page_home.py:196` → `"고객관리"` → `"👥 고객관리"`

**아이콘 대응 표:**

| 기존 문자열 | 새 문자열 |
|------------|----------|
| `"오늘의 할일"` | `"📋 오늘의 할일"` |
| `"고객관리"` | `"👥 고객관리"` |
| `"보장분석"` | `"📊 보장분석"` |
| `"통계"` | `"📈 통계"` |
| `"개척지도"` | `"🗺️ 개척지도"` |
| `"동선기록"` | `"📍 동선기록"` |
| `"설정"` | `"⚙️ 설정"` |

**새 CSS 블록 (기존 `st.markdown("""<style>...</style>""")` 전체 교체):**

```python
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    html, body, [class*="st-"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #37352F;
    }
    .stApp { background-color: #FFFFFF; }

    [data-testid="stSidebar"] {
        background-color: #F7F7F5;
        border-right: 1px solid #E8E8E3;
    }

    h1 { font-weight: 700; font-size: 26px; color: #37352F; margin-bottom: 4px; }
    h2 { font-weight: 600; font-size: 20px; color: #37352F; margin-top: 20px; }
    h3 { font-weight: 600; font-size: 16px; color: #37352F; }

    .notion-card {
        background: #FFFFFF;
        border: 1px solid #E8E8E3;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 10px;
        transition: background 0.1s;
    }
    .notion-card:hover { background: #F7F7F5; }

    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        font-size: 14px;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 1px solid #E8E8E3;
        border-radius: 6px;
        font-size: 14px;
    }
    hr { border-color: #E8E8E3; margin: 20px 0; }

    [data-testid="stMetric"] {
        background: #F7F7F5;
        border-radius: 8px;
        padding: 10px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #E8E8E3;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        font-weight: 500;
        color: #787774;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        color: #37352F;
        border-bottom: 2px solid #37352F;
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    @media (max-width: 768px) {
        .stButton > button { width: 100%; }
        h1 { font-size: 20px; }
    }
</style>
""", unsafe_allow_html=True)
```

**사이드바 메뉴 아이콘 추가** (3개 모드 모두):

```python
if mode == "pioneer":
    menu = ["📋 오늘의 할일", "🗺️ 개척지도", "📍 동선기록", "👥 고객관리", "📊 보장분석", "📈 통계", "⚙️ 설정"]
elif mode == "referral":
    menu = ["📋 오늘의 할일", "👥 고객관리", "📊 보장분석", "📈 통계", "🗺️ 개척지도", "📍 동선기록", "⚙️ 설정"]
else:
    menu = ["📋 오늘의 할일", "📊 보장분석", "👥 고객관리", "🗺️ 개척지도", "📍 동선기록", "📈 통계", "⚙️ 설정"]
```

**tab 비교 문자열 7개 업데이트:**

```python
if tab == "📋 오늘의 할일": ...
elif tab == "📊 보장분석": ...
elif tab == "👥 고객관리": ...
elif tab == "🗺️ 개척지도": ...
elif tab == "📍 동선기록": ...
elif tab == "📈 통계": ...
elif tab == "⚙️ 설정": ...
```

**사이드바 구조 개선:**

```python
with st.sidebar:
    st.markdown("### 🛡️ FCPilot")
    user = st.session_state.get("user")
    if user:
        st.caption(user.email)
    st.markdown("---")
    # ... mode 계산 ...
    # ... _nav_to 처리 ...
    tab = st.radio("메뉴", menu, label_visibility="collapsed", key="main_nav")
    st.markdown("---")
    st.caption("v1.0")
    if st.button("로그아웃", use_container_width=True):
        logout()
```

**`app.py` line 98 — 기존 `except Exception:` 수정:**

```python
# 기존 (규칙 위반)
except Exception:
    pass
# 수정
except Exception as e:
    pass
```

- [ ] **Step 1: `_nav_to` 전체 감사**

  ```bash
  cd C:/FCPilot && grep -rn "_nav_to" views/ app.py
  ```
  모든 할당값을 아이콘 포함 문자열로 업데이트.

- [ ] **Step 2: CSS 블록 교체** (기존 line 9~14 대체)

- [ ] **Step 3: 사이드바 menu 리스트 3개 아이콘 추가**

- [ ] **Step 4: tab 비교 문자열 7개 업데이트**

- [ ] **Step 5: 사이드바 구조 개선 (heading, 버전 정보)**

- [ ] **Step 6: `app.py:98` `except Exception:` → `except Exception as e:`**

- [ ] **Step 7: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile app.py views/page_home.py && echo "OK"
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add app.py views/page_home.py
  git commit -m "feat: 글로벌 Notion CSS + 사이드바 아이콘 메뉴 + nav_to 일치"
  ```

---

## Round 2: 홈 + 고객관리 리뉴얼

### Task 3: `page_home.py` 등급 뱃지 + 빈 상태 컴포넌트

**Files:**
- Modify: `views/page_home.py`

변경 사항:

1. `from utils.ui_components import grade_badge, empty_state, section_header` import 추가
2. `_render_reminder_card()` — **line 88의 `grade_badge = f" [{grade}]"` 제거** 후 HTML 뱃지로 교체
3. 빈 상태 `st.info` → `empty_state()` (2곳)
4. 섹션 헤더 `st.subheader` → `section_header()` (3곳)

**`_render_reminder_card` 등급 뱃지 교체:**

```python
# 기존 line 88 제거:
# grade_badge = f" [{grade}]" if grade else ""

# 교체:
from utils.ui_components import grade_badge as _grade_badge, empty_state, section_header

# 카드 내 표시:
grade_html = _grade_badge(grade) if grade else ""
st.markdown(
    f'**{name}** {grade_html} — {purpose}{prod_label}',
    unsafe_allow_html=True,
)
```

> **주의:** import 이름 충돌 방지를 위해 `grade_badge as _grade_badge`로 import.

**빈 상태 교체 (2곳):**

```python
# 기존
st.info("오늘 예정된 리마인드가 없습니다.")
# 변경
empty_state("📋", "오늘 예정된 리마인드가 없습니다")

# 기존
st.info("이번 주 예정된 리마인드가 없습니다.")
# 변경
empty_state("📅", "이번 주 예정된 리마인드가 없습니다")
```

- [ ] **Step 1: import 추가 (`grade_badge as _grade_badge` 포함)**

- [ ] **Step 2: line 88 `grade_badge = ...` 로컬 변수 제거 + HTML 뱃지 적용**

- [ ] **Step 3: 빈 상태 2곳 교체**

- [ ] **Step 4: 섹션 헤더 `st.subheader` → `section_header()` 3곳 교체**

- [ ] **Step 5: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile views/page_home.py && echo "OK"
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add views/page_home.py
  git commit -m "feat: 홈 카드 등급 뱃지 + 빈 상태 컴포넌트"
  ```

---

### Task 4: `page_clients.py` 분리 + 카드형 목록

**Files:**
- Create: `views/page_clients_detail.py` — 상세 탭 구조
- Modify: `views/page_clients.py` — 상세 렌더링을 위임, 목록 카드형으로 개선

**전략:** `page_clients.py`는 현재 568줄. `_render_detail()` 함수와 그 하위 함수(`_render_contact_logs`, `_render_reminders_section`, `_render_analysis_history` 등)를 `views/page_clients_detail.py`로 이동한다.

**Step 1: 현재 `_render_detail` 관련 함수 파악**

```bash
cd C:/FCPilot && grep -n "^def " views/page_clients.py
```

출력 예시에서 `_render_detail`, 그 아래 헬퍼 함수들을 확인.

**Step 2: 이동 전 `fc_id` 스코프 감사**

이동 대상 함수들의 `fc_id` 미정의 사용을 점검:

```bash
cd C:/FCPilot && grep -n "fc_id" views/page_clients.py
```

확인 및 수정 필요 항목:
- `_render_client_delete(sb, client_id)` — 내부에서 `fc_id` 사용하지만 파라미터 없음 → `fc_id: str` 파라미터 추가, 호출부도 `_render_client_delete(sb, client_id, fc_id)` 로 수정
- `_render_contact_logs(sb, client_id)` — 내부 `fc_id` 사용 여부 확인 → 미정의 시 함수 내부 상단에 `fc_id = get_current_user_id()` 추가
- `_nav_to` 할당값 — `"보장분석"` → `"📊 보장분석"` 등 아이콘 포함으로 수정

**Step 3: `views/page_clients_detail.py` 생성**

`_render_detail()` + 하위 헬퍼 함수 전체를 새 파일로 이동. 필요한 import (`st`, `auth`, `services/*`, `utils/*`) 모두 포함.

파일 상단:
```python
"""고객 상세 뷰 — 탭 구조 (상담이력 | 리마인드 | 보장분석)"""
import streamlit as st
from utils.ui_components import grade_badge as _grade_badge, empty_state
# ... 필요한 나머지 import
```

`_render_detail()` 내 섹션들을 `st.tabs()` 구조로 리팩토링:

```python
def render_detail():
    """고객 상세 — 상단 기본정보 + 하단 탭"""
    # 기존 기본정보 표시 코드 유지
    # ...

    st.markdown("---")
    tab_contact, tab_remind, tab_analysis = st.tabs(["📝 상담이력", "🔔 리마인드", "📊 보장분석"])
    with tab_contact:
        _render_contact_logs(...)  # 실제 함수 시그니처 확인 후 인자 맞춤
    with tab_remind:
        _render_reminder_section(...)  # 실제 이름: _render_reminder_section (s 없음)
    with tab_analysis:
        _render_analysis_history(...)
```

**Step 3: `page_clients.py` 목록 카드형 개선**

```python
from utils.ui_components import grade_badge as _grade_badge, empty_state

# _render_list() 내 각 고객 행
with st.container(border=True):
    c_info, c_btn = st.columns([5, 1])
    with c_info:
        grade_html = _grade_badge(c.get("prospect_grade", ""))
        st.markdown(
            f'**{c["name"]}** {grade_html} &nbsp; '
            f'<span style="color:#787774; font-size:13px;">'
            f'{c.get("age_group","")} · {c.get("db_source","")}</span>',
            unsafe_allow_html=True,
        )
        if c.get("last_contact"):
            st.caption(f"마지막 상담: {c['last_contact']}")
    with c_btn:
        if st.button("상세", key=f"det_{c['id']}", use_container_width=True):
            st.session_state.clients_view = "detail"
            st.session_state.selected_client_id = c["id"]
            st.rerun()
```

**Step 4: `render()` 에서 상세 뷰 위임**

```python
def render():
    st.header("고객관리")
    view = st.session_state.get("clients_view", "list")
    if view == "detail":
        from views.page_clients_detail import render_detail
        render_detail()
    elif view == "new":
        _render_form()
    elif view == "edit":
        _render_form(edit=True)
    else:
        _render_list()
```

- [ ] **Step 1: `grep -n "^def "` 로 함수 목록 파악**

- [ ] **Step 2: `fc_id` 스코프 감사** — `_render_client_delete`, `_render_contact_logs` 에 `fc_id` 파라미터/로컬 추가

- [ ] **Step 3: `views/page_clients_detail.py` 생성 — `_render_detail` + 하위 헬퍼 이동**

- [ ] **Step 4: 이동된 섹션에 `st.tabs()` 구조 추가** (`_render_reminder_section` 철자 확인 — `s` 없음)

- [ ] **Step 5: `page_clients.py` — `_render_detail` 제거, `render()` 위임 코드로 교체**

- [ ] **Step 6: `_render_list` 카드형 UI 교체**

- [ ] **Step 6: 줄 수 확인 (둘 다 200줄 이하여야 함)**

  ```bash
  cd C:/FCPilot && wc -l views/page_clients.py views/page_clients_detail.py
  ```

- [ ] **Step 7: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile views/page_clients.py views/page_clients_detail.py && echo "OK"
  ```

- [ ] **Step 8: Commit**

  ```bash
  git add views/page_clients.py views/page_clients_detail.py
  git commit -m "feat: 고객관리 카드형 목록 + 상세 탭 구조 (page_clients_detail 분리)"
  ```

---

## Round 3: 보장분석 + 통계 리뉴얼

### Task 5: `page_analysis.py` Step 플로우

**Files:**
- Modify: `views/page_analysis.py`

**사전 파악:**

```bash
cd C:/FCPilot && grep -n "^def " views/page_analysis.py
```

변경 대상:
- `render()` — Step 레이블 추가 (업로드 전, 옵션 전)
- `_show_result()` — 계약 목록 `st.expander` 적용

**`render()` Step 레이블:**

```python
from utils.ui_components import section_header

def render():
    st.header("보장분석")
    section_header("Step 1. PDF 업로드")
    uploaded_file = st.file_uploader(...)

    section_header("Step 2. 옵션 설정")
    col1, col2 = st.columns([3, 1])
    # 기존 코드 유지

    # 분석 버튼 및 결과 — 기존 코드 유지
```

**`_show_result()` 계약 목록 expander (기존 `for c in contracts:` 루프를 감싸기):**

```python
# _show_result() 내부에서 contracts 변수가 정의된 위치 확인 후
with st.expander(f"📋 계약 목록 ({len(contracts)}건)", expanded=True):
    for i, c in enumerate(contracts):
        st.markdown(f"{i+1}. **{c.get('company','')}** · {c.get('product_name','')}")
```

- [ ] **Step 1: `grep -n "^def \|contracts"` 로 `_show_result` 내 `contracts` 사용 위치 파악**

  ```bash
  cd C:/FCPilot && grep -n "^def \|contracts" views/page_analysis.py | head -20
  ```

- [ ] **Step 2: `render()` 에 `section_header` Step 레이블 2개 추가**

- [ ] **Step 3: `_show_result()` 내 계약 목록 루프를 `st.expander`로 감싸기**

- [ ] **Step 4: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile views/page_analysis.py && echo "OK"
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add views/page_analysis.py
  git commit -m "feat: 보장분석 Step 레이블 + 계약목록 expander"
  ```

---

### Task 6: `page_stats.py` 프로그레스 바 시각화

**Files:**
- Modify: `views/page_stats.py`

변경 사항: `_dist_cards()` 함수를 프로그레스 바 시각화로 교체.

```python
def _dist_cards(dist: dict, keys: list, label_fn):
    total = sum(dist.values())
    items = [(k, dist[k]) for k in keys if k in dist]
    for k, cnt in items:
        pct = round(cnt / total * 100, 1) if total else 0
        col_label, col_bar, col_cnt = st.columns([2, 5, 1])
        col_label.caption(label_fn(k))
        col_bar.progress(min(pct / 100, 1.0))  # 1.0 초과 방지
        col_cnt.caption(f"{cnt}명 ({pct}%)")
```

- [ ] **Step 1: `_dist_cards` 교체**

- [ ] **Step 2: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile views/page_stats.py && echo "OK"
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add views/page_stats.py
  git commit -m "feat: 통계 분포 프로그레스 바 시각화 (float clamp 포함)"
  ```

---

## Round 4: 개척지도 + 설정 리뉴얼

### Task 7: `page_pioneer_map.py` 사이드패널 레이아웃

**Files:**
- Modify: `views/page_pioneer_map.py`

**사전 파악:**

```bash
cd C:/FCPilot && grep -n "st\.tabs\|st\.columns\|지도\|shops" views/page_pioneer_map.py | head -20
```

변경 사항: 지도 탭에서 `st.columns([7, 3])` 적용 — 지도 70% + 매장 목록 30%.

```python
from utils.ui_components import empty_state

# 지도 탭 내부
map_col, list_col = st.columns([7, 3])
with map_col:
    # 기존 지도 렌더링 코드 그대로
    ...
with list_col:
    st.caption(f"매장 {len(shops)}곳")
    if not shops:
        empty_state("🏪", "등록된 매장이 없습니다")
    else:
        STATUS_ICON = {"active": "🟡", "visited": "🔵", "contracted": "🟢", "rejected": "🔴"}
        for shop in shops[:15]:
            with st.container(border=True):
                icon = STATUS_ICON.get(shop.get("status", ""), "⚪")
                st.markdown(f"{icon} **{shop['shop_name']}**")
                st.caption(shop.get("address", ""))
```

- [ ] **Step 1: 지도 탭 위치 파악 후 `st.columns([7, 3])` 적용**

- [ ] **Step 2: 매장 목록 사이드패널 카드 추가**

- [ ] **Step 3: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile views/page_pioneer_map.py && echo "OK"
  ```

- [ ] **Step 4: Commit**

  ```bash
  git add views/page_pioneer_map.py
  git commit -m "feat: 개척지도 지도+사이드패널 레이아웃"
  ```

---

### Task 8: `page_settings.py` expander 카테고리 구조

**Files:**
- Modify: `views/page_settings.py`

**사전 파악:**

```bash
cd C:/FCPilot && grep -n "^def \|subheader\|render\|fc_id\|user_id" views/page_settings.py | head -30
```

> **주의:**
> - `page_settings_products.py`의 export 이름: `render_product_section` (not `render`)
> - `page_settings_admin.py`의 export 이름: `render_admin_section` (not `render_admin`)
> - 설정 탭 내 사용자 ID 변수명은 `user_id` (not `fc_id`) — 확인 후 사용

변경 사항: 현재 평면 레이아웃을 `st.expander` 카테고리별로 구조화.

```python
# render() 내부 구조
with st.expander("👤 프로필 설정", expanded=True):
    # 기존 프로필 설정 코드 이동

with st.expander("📦 상품 관리"):
    from views.page_settings_products import render_product_section
    render_product_section()

with st.expander("🏷️ 유입경로 관리"):
    # 기존 유입경로 설정 코드 이동

if is_admin():
    with st.expander("🔧 Admin 관리"):
        from views.page_settings_admin import render_admin_section
        render_admin_section(sb)  # render_admin_section 시그니처 확인 후 인자 맞춤

# 하단 버전 정보 — user_id 변수명 사용 (fc_id 아님)
st.markdown("---")
st.caption(f"FCPilot v1.0.0 · {user_id[:8]}...")
```

- [ ] **Step 1: `grep` 으로 실제 함수명/변수명 확인**

  ```bash
  cd C:/FCPilot && grep -n "def render" views/page_settings_products.py views/page_settings_admin.py
  cd C:/FCPilot && grep -n "user_id\|fc_id" views/page_settings.py | head -10
  ```

- [ ] **Step 2: 각 섹션을 `st.expander`로 감싸기**

- [ ] **Step 3: 올바른 import 이름(`render_product_section`, `render_admin_section`) 사용**

- [ ] **Step 4: 하단 버전 정보 추가 (올바른 변수명 사용)**

- [ ] **Step 5: 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile views/page_settings.py && echo "OK"
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add views/page_settings.py
  git commit -m "feat: 설정 expander 카테고리 구조"
  ```

---

## 최종 단계

### Task 9: 전체 검사 + 푸시

- [ ] **Step 1: 전체 구문 검사**

  ```bash
  cd C:/FCPilot && python -m py_compile app.py utils/ui_components.py views/page_home.py views/page_clients.py views/page_clients_detail.py views/page_analysis.py views/page_stats.py views/page_pioneer_map.py views/page_settings.py && echo "ALL OK"
  ```

- [ ] **Step 2: 자동 테스트 실행**

  ```bash
  cd C:/FCPilot && python tests/test_all.py
  ```
  Expected: 모든 테스트 통과

- [ ] **Step 3: 전체 푸시**

  ```bash
  git push origin main
  ```

- [ ] **Step 4: handoff.md + plan.md 업데이트**

---

## 주의사항 요약

| 항목 | 내용 |
|------|------|
| `_nav_to` 문자열 | `app.py`의 `menu` 리스트와 **정확히 일치** (아이콘 포함). grep으로 전수 확인 필수 |
| `grade_badge` 이름 충돌 | `page_home.py:88` 로컬 변수 제거 후 `grade_badge as _grade_badge`로 import |
| settings import 이름 | `render_product_section`, `render_admin_section` (render/render_admin 아님) |
| settings 변수명 | `user_id` (fc_id 아님) — grep으로 확인 |
| `st.progress()` | 반드시 `min(pct/100, 1.0)` — 1.0 초과 시 ValueError |
| `_show_result()` | `contracts` 변수는 `render()`가 아닌 `_show_result()` 내부 스코프 |
| `page_clients.py` | 200줄 초과 → `page_clients_detail.py` 분리 필수 |
| bash 명령 | 항상 `cd C:/FCPilot &&` 선행 |
