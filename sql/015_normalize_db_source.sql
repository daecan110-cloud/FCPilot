-- 015: 유입경로 정규화 — "개인(지인)" → "지인" 통일
UPDATE clients
SET db_source = '지인'
WHERE db_source IN ('개인(지인)', '지인(개인)');
