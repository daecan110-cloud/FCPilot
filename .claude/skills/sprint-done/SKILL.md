---
name: sprint-done
description: Sprint 완료 처리 — 테스트 실행, 체크리스트 생성, 텔레그램 발송, handoff 업데이트, commit+push
---

Sprint 완료 자동화. 아래 순서대로 반드시 실행한다:

## 1. 테스트 실행
```bash
python tests/test_all.py
```
실패하면 여기서 멈추고 실패 내용을 보고한다.

## 2. 변경 파일 기반 테스트 체크리스트 생성
```bash
git diff --name-only $(git log --oneline | head -20 | tail -1 | cut -d' ' -f1)..HEAD
```
변경된 파일을 분석해서 영민이 수동으로 확인해야 할 항목을 생성한다:
```
📋 영민 테스트 체크리스트

이번에 추가/수정한 기능:
- [ ] {기능} — {확인 방법: 어떤 탭 → 어떤 동작 → 예상 결과}

테스트: fcpilot-kr.streamlit.app
```
각 항목에 **구체적 확인 방법**을 반드시 포함한다.

## 3. 텔레그램 발송
```python
from utils.telegram import send_message
send_message(체크리스트_내용)
```

## 4. handoff.md 업데이트
- 완료 항목, 미완료 항목, 알려진 이슈 갱신
- "영민 테스트 대기 중" 표시

## 5. plan.md 업데이트
- 완료된 항목 체크

## 6. commit + push
```bash
git add -A && git commit -m "sprint: {요약}" && git push origin main
```
