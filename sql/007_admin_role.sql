-- Sprint 6: users_settings에 role 컬럼 추가 (admin/user)

ALTER TABLE users_settings
  ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'
  CHECK (role IN ('admin', 'user'));

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_users_settings_role ON users_settings(role);

-- 현재 등록된 첫 번째 사용자를 admin으로 지정 (수동 실행 시 이메일 기준으로 변경 가능)
-- UPDATE users_settings SET role = 'admin' WHERE id = '<your_user_id>';
