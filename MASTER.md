# MASTER.md — FCPilot

> **최종 업데이트**: 2026-03-31 (Sprint 6 완료 기준)

---

## 1. 프로젝트 요약

| 항목 | 내용 |
|------|------|
| **프로젝트명** | FCPilot |
| **목적** | 보험 FC 업무 통합 플랫폼 |
| **핵심 기능** | 보장분석 자동화, 고객 CRM, 개척영업 관리(간판OCR+지도), 약관분석, 동선추적, 팔로업/리마인드, 텔레그램 AI 어시스턴트 |
| **사용자** | 신한라이프 FC 영민 (1차) → 동료 FC (2차) |
| **현재 상태** | Sprint 6 완료 — 배포 준비 완료 |
| **배포 URL** | fcpilot-kr.streamlit.app (수동 배포 필요) |

---

## 2. 아키텍처

```
[Streamlit Cloud] ← Frontend
       ↕
[Supabase — ghglnszzjuuvrrwpvhhb] ← DB + Auth + Edge Functions
       ↕
[Claude API (Sonnet)] ← 보장분석, 약관분석, 간판OCR
[Gemini API] ← 텔레그램 AI 어시스턴트
[Naver Maps API] ← 지오코딩
[folium] ← 지도 렌더링
[Telegram Bot API] ← 양방향 소통 (알림 + 명령 수신)
```

| 구성요소 | 상세 |
|----------|------|
| Frontend | Streamlit Cloud |
| DB/Auth | Supabase Seoul — **ghglnszzjuuvrrwpvhhb** (daecan110 계정, FCPilot 전용) |
| AI (분석) | Claude API (Sonnet) — 보장분석, 약관분석, 간판OCR |
| AI (챗봇) | Gemini 2.5 Flash — 텔레그램 AI 어시스턴트 |
| 지도 | folium + Naver Maps API (지오코딩) |
| 소통 | 텔레그램 Bot (양방향 — webhook 기반) |
| Edge Functions | telegram-bot, daily-reminder |
| 개발 방식 | Opus(설계/QA) + Claude Code/Sonnet(구현) |

---

## 3. 인프라 정보

| 항목 | 값 |
|------|-----|
| GitHub | **daecan110-cloud/FCPilot** (private) |
| Supabase Project ID | ghglnszzjuuvrrwpvhhb |
| Supabase 계정 | daecan110 (FCPilot 전용 독립 인스턴스) |
| Streamlit Cloud | daecan110@gmail.com-cloud 계정 |
| 텔레그램 Chat ID | 8201988543 |
| Gemini API 계정 | daecan110 |

---

## 4. DB 테이블

| # | 테이블명 | 용도 |
|---|----------|------|
| 1 | fp_users_settings | FC 설정 (영업 모드, **role: admin/user**) |
| 2 | fp_clients | 고객 마스터 |
| 3 | fp_contact_logs | 상담 이력 |
| 4 | fp_pioneer_shops | 개척 매장 |
| 5 | fp_pioneer_visits | 개척 방문 기록 |
| 6 | fp_analysis_records | 보장분석 기록 |
| 7 | fp_yakwan_records | 약관 분석 기록 |
| 8 | command_queue | 텔레그램 명령 큐 |
| 9 | bot_sessions | 텔레그램 봇 세션 (인스턴스 간 상태 공유) |

> **접두사 규칙**: `fp_` — FCPilot 테이블 식별 (독립 인스턴스이나 관례 유지)

---

## 5. 앱 구조

### 5-1. 탭 구조 (Sprint 3 기준, ⚠️ Sprint 6 코드 확인 필요)

| 탭 | 파일 | 핵심 기능 |
|----|------|-----------|
| 보장분석 | views/page_analysis.py | PDF 업로드 → 보장분석표 엑셀 생성, 약관분석 → K열 반영 |
| 고객관리 | views/page_clients.py | 고객 목록/등록/수정, 상담 기록 타임라인 |
| 개척지도 | views/page_pioneer_map.py | 간판OCR 등록, folium 지도, 팔로업 상태 |
| 동선기록 | views/page_pioneer_route.py | AntPath 경로선, 날짜별 방문 기록 |
| 설정 | views/page_settings.py | 영업 모드, Admin 전용(역할 관리 + DB 통계) |

> Sprint 6에서 `pages/` → `views/` 이름 변경 (Streamlit 사이드바 자동 노출 차단)

### 5-2. 영업 모드

| 모드 | 설명 |
|------|------|
| pioneer (개척) | 영민 기본 — 개척지도/동선 우선 |
| db (DB 영업) | 고객관리/상담 우선 |
| mixed (혼합) | 전체 동일 비중 |

설정에서 언제든 전환 가능

### 5-3. 역할 시스템 (Sprint 6)

| 역할 | 권한 |
|------|------|
| admin | 설정 탭 내 역할 관리 + DB 통계 접근 |
| user | 일반 기능만 |

---

## 6. 텔레그램 봇

### 6-1. 현재 구현 (Sprint 5~6)

- **방식**: Supabase Edge Function (telegram-bot) + webhook
- **AI 엔진**: Gemini 2.5 Flash (429 대응: 재시도 + 로컬 폴백)
- **기능**: 고객 등록/조회/수정/삭제, 자연어 대화, 동명이인 처리, DB 세션 관리
- **세션**: bot_sessions 테이블 (Edge Function 인스턴스 간 상태 공유)

### 6-2. 봇 분리 계획 (향후)

| 봇 | 용도 | 대상 |
|----|------|------|
| **고객관리 봇** | CRM 조회/등록, 일정 리마인드, 자연어 고객 관리 | 영민 (FC 업무) |
| **개발알림 봇** | Sprint 완료 알림, 에러 보고, 상태 체크 | 영민 (개발자) |

> 현재는 하나의 봇에 통합. 분리 시점은 실사용 테스트 후 결정

---

## 7. 주요 엔진

| 엔진 | 파일 | 역할 |
|------|------|------|
| 보장분석 v4 | analysis_engine.py | PDF → pdfplumber → 32개 보험사 키워드 → 엑셀 |
| 약관분석 | yakwan_engine.py | 약관 PDF → Claude API → 구조화 JSON + K열 요약 |
| 간판 OCR | ocr_engine.py | Claude Vision → 상호명 + 업종 추출 |
| 지오코딩 | geocoding.py | Naver Maps API → 좌표 변환 |
| 팔로업 | followup.py | 상태머신 (방문→관심→제안→계약 등) |
| 리마인드 | reminder.py | 대상 조회 로직 (발송 트리거 미구현) |
| 엑셀 생성 | excel_generator.py | master_template.xlsx 기반 보장분석표 |
| 지도 | map_utils.py | folium AntPath + 번호 마커 |

---

## 8. Sprint 이력

| Sprint | 내용 | 상태 |
|--------|------|------|
| 1 (MVP) | 인증 + 보장분석 엔진 v4 + 텔레그램 알림 + 약관 AI 대화 | ✅ 완료 |
| 2 | CRM (고객 목록/등록/수정) + 개척지도 (간판OCR + folium) + CSV 마이그레이션 | ✅ 완료 |
| 3 | 약관 강화 (K열 반영) + 동선추적 (AntPath) + 팔로업 + 리마인드 로직 | ✅ 완료 |
| 4 | Supabase 독립 분리 + 텔레그램 양방향 (webhook + Gemini) + Edge Functions | ✅ 완료 |
| 5 | 텔레그램 봇 v4 (자연어 CRM) + QA + 보안 체크 + 배포 준비 | ✅ 완료 |
| 6 | UI 정리 (views/ 이동) + Admin/User 역할 분리 + 보안 최종 점검 | ✅ 완료 |

---

## 9. 다음 작업 (Sprint 7~)

### 우선순위 (확정)

| # | 작업 | 비고 |
|---|------|------|
| 1 | ~~텔레그램 자연어 개선 마무리~~ | **Claude Code 진행 중** |
| 2 | CSV 마이그레이션 | 기존 구글시트 데이터 → Supabase |
| 3 | 실사용 테스트 | 실제 영업 현장에서 전체 플로우 검증 |
| 4 | UI/UX 개선 | 실사용 피드백 기반 |

### 미구현/잔여 작업

| 작업 | 출처 |
|------|------|
| 리마인드 발송 트리거 구현 | Sprint 3 잔여 |
| Daily Reminder cron 설정 (pg_cron + pg_net) | Sprint 5 — 영민 수동 |
| Streamlit Cloud 배포 | Sprint 5 — 영민 수동 |
| Admin role SQL 실행 | Sprint 6 — 영민 수동 |
| 보장분석표 하단 셀 병합 검증 | Sprint 1 잔여 |
| 홈 탭 (오늘의 할 일) | Sprint 3 handoff 계획 |
| 통계 대시보드 | Sprint 3 handoff 계획 |
| 텔레그램 봇 분리 (고객관리 vs 개발알림) | 향후 |
| 200줄 초과 파일 7개 리팩토링 | Sprint 6 이슈 |

---

## 10. 핵심 의사결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-03-30 | Streamlit + Supabase | AlphaBot 인프라 재활용, 학습비용 제로 |
| 2026-03-30 | Claude Vision OCR | 별도 OCR 불필요, 한글 간판 인식 우수 |
| 2026-03-30 | folium 지도 | 무료, Streamlit 호환, 개척 동선 표시 가능 |
| 2026-03-30 | 영업 모드 시스템 | FC마다 스타일 다름, 탭 순서로 차별화 |
| 2026-03-31 | Supabase 독립 인스턴스 | AlphaBot과 완전 분리 (보안 + 관리 편의) |
| 2026-03-31 | Gemini for 텔레그램 | Claude API 비용 절감, 자연어 대화에 적합 |
| 2026-03-31 | Edge Function + webhook | 폴링 대비 실시간성, 서버리스 |
| 2026-03-31 | views/ 폴더명 변경 | Streamlit 사이드바 자동 노출 차단 |
| 2026-03-31 | Admin/User 역할 | 동료 FC 확장 대비, 설정 접근 제어 |

---

## 11. 보장분석표 규칙 (불변)

- 저장 직전 `_final_format_pass()` 필수 실행
- `master_template.xlsx` 원본 절대 수정 금지
- 계약 7개 이하 → 1파일 / 8개 이상 → 7개씩 분리
- 약관 분석 결과 → **K열(특이사항)**에 자동 반영

---

## 12. 보안 규칙

- GitHub repo: **private 필수** (고객 개인정보)
- `fp_` 접두사: 테이블 네이밍 규칙 유지
- 데이터 파일 git 커밋 금지
- API 키 하드코딩 금지 → secrets.toml / 환경변수
- bare except 금지
- 보안 체크리스트: Sprint 6 ALL CLEAR 달성

---

## 13. 알려진 이슈

| 이슈 | 상태 |
|------|------|
| Gemini 무료 tier 분당 2회 제한 | 429 재시도 + 로컬 폴백 대응 |
| 200줄 초과 파일 7개 | 향후 리팩토링 |
| DB 직접 연결 IPv6 전용 | Pooler 미연결, connection string 확인 필요 |
| Streamlit Cloud 무료 플랜 앱 개수 제한 | 확인 필요 |

---

## 14. 문서 체계

| 문서 | 역할 | 관리 |
|------|------|------|
| **MASTER.md** | 전체 설계/아키텍처/의사결정 (이 문서) | Opus |
| **handoff.md** | 세션 인수인계 (Sprint 상태 + 다음 할 일) | Claude Code |
| **CLAUDE.md** | Claude Code 작업 규칙 | Claude Code |
| **plan.md** | 현재 Sprint 상세 계획 | Claude Code |

> **Opus 역할**: 설계/방향/QA 리뷰 — MASTER.md 관리
> **Claude Code 역할**: 구현/버그수정 — handoff.md, plan.md, CLAUDE.md 관리
> **새 채팅 시작 시**: MASTER.md + handoff.md 2개만 주면 맥락 100% 복원
