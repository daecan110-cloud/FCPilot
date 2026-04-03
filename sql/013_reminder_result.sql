-- fp_reminders 결과 추적 컬럼 추가
-- result: 완료 시 결과 유형
-- result_memo: FC 후기 / 실패 사유

ALTER TABLE fp_reminders
  ADD COLUMN IF NOT EXISTS result TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS result_memo TEXT DEFAULT '';
