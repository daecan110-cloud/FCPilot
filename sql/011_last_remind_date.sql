-- 리마인드 하루 1회 발송 제한을 위한 컬럼 추가
ALTER TABLE users_settings
ADD COLUMN IF NOT EXISTS last_remind_date TEXT;
