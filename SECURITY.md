# FCPilot 보안 정책 (SECURITY.md)

> 내부 사용 전용이지만, 고객 이름+전화번호+보험정보는 민감 개인정보.
> **유출 자체가 불가능한 구조를 코드 레벨에서 보장한다.**

---

## 1. 데이터 분류

| 등급 | 데이터 | 보호 수준 |
|------|--------|-----------|
| 🔴 최고 | 전화번호, 주민번호(없음), 보험 계약 상세 | 암호화 저장 + RLS + 전송 시 HTTPS |
| 🟠 높음 | 고객 이름, 주소, 직업, 상담 내용 | RLS + HTTPS |
| 🟡 보통 | 가망등급, 터치방식, 메모 | RLS |
| 🟢 낮음 | 개척 매장명, 주소 (공개 정보) | RLS (FC별 분리만) |

---

## 2. 암호화 전략

### 2-1. 전화번호 암호화 (🔴 필수)

Supabase에 전화번호를 평문 저장하지 않는다.

**방식: 앱 레벨 AES-256 암호화**

```python
# services/crypto.py
from cryptography.fernet import Fernet
import os

def get_cipher():
    """secrets.toml에서 암호화 키 로드"""
    key = st.secrets["security"]["encryption_key"]
    return Fernet(key.encode())

def encrypt_phone(phone: str) -> str:
    """전화번호 암호화"""
    if not phone:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(phone.encode()).decode()

def decrypt_phone(encrypted: str) -> str:
    """전화번호 복호화"""
    if not encrypted:
        return ""
    cipher = get_cipher()
    return cipher.decrypt(encrypted.encode()).decode()
```

**암호화 키 생성 (1회):**
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```
→ secrets.toml에 저장:
```toml
[security]
encryption_key = "생성된키..."
```

**DB 저장 흐름:**
```
사용자 입력: 010-1234-5678
    ↓ encrypt_phone()
DB 저장: gAAAAABl...  (암호화된 문자열)
    ↓ decrypt_phone()
화면 표시: 010-1234-5678
```

**검색 시:** 전화번호 검색이 필요하면 뒷자리 4자리를 별도 `phone_last4` 컬럼에 해시 저장
```python
import hashlib
def hash_phone_last4(phone: str) -> str:
    last4 = phone.replace("-", "")[-4:]
    return hashlib.sha256(last4.encode()).hexdigest()[:16]
```

### 2-2. Supabase 전송 암호화

- Supabase는 기본적으로 **HTTPS (TLS 1.2+)** 사용 ✅
- Streamlit Cloud도 HTTPS 강제 ✅
- 추가 설정 불필요하지만 **HTTP 접근 차단 확인 필수**

### 2-3. 간판 사진 접근 제어

Supabase Storage 버킷 설정:
```sql
-- private 버킷 (인증된 사용자만 접근)
INSERT INTO storage.buckets (id, name, public)
VALUES ('pioneer-photos', 'pioneer-photos', false);

-- RLS: 본인이 올린 사진만 접근
CREATE POLICY "fc_own_photos" ON storage.objects
  FOR ALL USING (
    bucket_id = 'pioneer-photos' AND
    auth.uid()::text = (storage.foldername(name))[1]
  );
```

파일 경로 규칙: `pioneer-photos/{fc_id}/{날짜}_{파일명}`

---

## 3. 접근 제어

### 3-1. Supabase RLS (이미 설계됨)
모든 `fp_` 테이블에 `fc_id = auth.uid()` 정책 적용.

### 3-2. 세션 관리
```python
# auth.py에 추가
import time

SESSION_TIMEOUT = 30 * 60  # 30분

def check_session_timeout():
    """60분 무활동 시 자동 로그아웃"""
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = time.time()
        return
    
    elapsed = time.time() - st.session_state.last_activity
    if elapsed > SESSION_TIMEOUT:
        st.session_state.clear()
        st.warning("60분 동안 활동이 없어 자동 로그아웃되었습니다.")
        st.rerun()
    else:
        st.session_state.last_activity = time.time()
```

### 3-3. 비밀번호 정책
- 최소 8자 이상
- Supabase Auth 기본 정책 활용 (bcrypt 해싱)

---

## 4. 코드 보안 규칙

### 4-1. 절대 금지
- ❌ 소스코드에 API 키/토큰 하드코딩
- ❌ 고객 데이터 포함 파일 git commit
- ❌ print()로 고객 정보 로깅
- ❌ 에러 메시지에 고객 정보 포함
- ❌ Claude API 호출 시 불필요한 고객 정보 전송

### 4-2. 필수
- ✅ secrets.toml에만 민감 정보
- ✅ 에러 로깅 시 고객 정보 마스킹 (이름 → 김**, 전화 → ***-****-5678)
- ✅ Claude API 호출 시 최소 필요 정보만 전송
- ✅ 파일 업로드 크기 제한 (10MB)
- ✅ 파일 타입 검증 (PDF/JPG/PNG만 허용)

### 4-3. 로깅 마스킹 함수
```python
# utils/helpers.py
def mask_name(name: str) -> str:
    """김영민 → 김**"""
    if not name or len(name) < 2:
        return "***"
    return name[0] + "*" * (len(name) - 1)

def mask_phone(phone: str) -> str:
    """010-1234-5678 → ***-****-5678"""
    if not phone:
        return "***"
    parts = phone.replace("-", "")
    return f"***-****-{parts[-4:]}"
```

---

## 5. Sprint별 보안 체크리스트

### 매 Sprint 완료 시 반드시 실행:

```bash
# === 보안 점검 스크립트 ===

echo "=== 1. API 키 하드코딩 탐지 ==="
grep -rn "sk-ant-\|eyJ\|bot[_-]token\|api[_-]key\s*=" --include="*.py" | grep -v secrets | grep -v "\.toml" | grep -v "st\.secrets"

echo "=== 2. 고객 데이터 파일 탐지 ==="
git ls-files | grep -iE "\.(csv|xlsx|xls)$" | grep -v templates

echo "=== 3. print()로 민감 정보 출력 탐지 ==="
grep -rn "print.*phone\|print.*이름\|print.*name\|print.*전화" --include="*.py"

echo "=== 4. bare except 탐지 ==="
grep -rn "except:" --include="*.py" | grep -v "except Exception"

echo "=== 5. 암호화 없이 전화번호 직접 저장 탐지 ==="
grep -rn "phone.*insert\|phone.*update\|\.phone\s*=" --include="*.py" | grep -v encrypt | grep -v decrypt | grep -v mask

echo "=== 6. .gitignore 필수 패턴 확인 ==="
for pattern in "secrets.toml" "*.csv" "*.xlsx" "__pycache__" ".env"; do
    grep -q "$pattern" .gitignore && echo "✅ $pattern" || echo "❌ $pattern 누락!"
done

echo "=== 7. Supabase RLS 활성화 확인 ==="
echo "→ Supabase Dashboard에서 수동 확인 필요"
echo "   모든 fp_ 테이블에 RLS enabled + policy 존재 확인"

echo "=== 8. HTTPS 확인 ==="
grep -rn "http://" --include="*.py" | grep -v "https://" | grep -v localhost | grep -v "# "

echo "=== 점검 완료 ==="
```

### 체크리스트 표

| # | 항목 | 확인 방법 | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 |
|---|------|-----------|----------|----------|----------|----------|
| 1 | API 키 하드코딩 없음 | grep 스크립트 | ☐ | ☐ | ☐ | ☐ |
| 2 | 고객 데이터 git 미포함 | git ls-files | ☐ | ☐ | ☐ | ☐ |
| 3 | 전화번호 암호화 저장 | crypto.py 사용 확인 | ☐ | ☐ | ☐ | ☐ |
| 4 | print()에 민감정보 없음 | grep 스크립트 | ☐ | ☐ | ☐ | ☐ |
| 5 | RLS 전 테이블 활성화 | Supabase Dashboard | ☐ | ☐ | ☐ | ☐ |
| 6 | 세션 타임아웃 작동 | 30분 방치 테스트 | ☐ | ☐ | ☐ | ☐ |
| 7 | Storage private 버킷 | Supabase Dashboard | - | ☐ | ☐ | ☐ |
| 8 | 파일 업로드 검증 | 비허용 파일 업로드 시도 | ☐ | ☐ | ☐ | ☐ |
| 9 | HTTPS만 사용 | grep http:// | ☐ | ☐ | ☐ | ☐ |
| 10 | 에러 메시지에 개인정보 없음 | 에러 발생 시 확인 | ☐ | ☐ | ☐ | ☐ |
| 11 | .gitignore 완성 | 필수 패턴 확인 | ☐ | ☐ | ☐ | ☐ |
| 12 | bare except 없음 | grep 스크립트 | ☐ | ☐ | ☐ | ☐ |

---

## 6. Claude API 호출 시 개인정보 최소화

### 보장분석 시
```python
# ❌ 나쁜 예 — 불필요한 개인정보 전송
prompt = f"고객 김영민(010-1234-5678)의 보장분석을 해줘: {pdf_text}"

# ✅ 좋은 예 — 최소 필요 정보만
prompt = f"다음 보험 계약 정보를 분석해줘: {pdf_text}"
# 고객명/전화번호는 Claude에 보내지 않고, 엑셀 생성 시 로컬에서 삽입
```

### 간판 OCR 시
```python
# ✅ 간판 사진만 전송, FC 정보 미포함
prompt = "이 간판 사진에서 가게 이름과 주소를 추출해줘."
```

---

## 7. 데이터 생명주기

| 단계 | 정책 |
|------|------|
| 수집 | 최소 필요 정보만. 주민번호 수집 금지. |
| 저장 | 전화번호 암호화. RLS 적용. |
| 전송 | HTTPS만. Claude API에 최소 정보만. |
| 이용 | 본인 FC만 접근. 화면 표시 시 마스킹 옵션. |
| 삭제 | 고객 삭제 시 contact_logs, analysis_records 연쇄 삭제 (CASCADE). |

---

## 8. 핵심 원칙

**유출 자체가 불가능한 구조를 만든다.**
- 전화번호는 암호화 없이 DB에 존재하지 않는다
- API 키는 secrets.toml 외에 어디에도 없다
- 본인 외 다른 FC의 데이터에 접근할 수 있는 경로가 없다
- Claude API에 고객 식별 정보가 전송되지 않는다
- Git 히스토리에 민감 데이터가 남지 않는다

**매 Sprint 보안 체크리스트 실행 필수. 통과 못 하면 배포 금지.**
