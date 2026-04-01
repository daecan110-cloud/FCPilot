-- 등급 체크 제약 조건 업데이트: VIP, S 등급 추가
ALTER TABLE clients DROP CONSTRAINT IF EXISTS clients_prospect_grade_check;
ALTER TABLE clients ADD CONSTRAINT clients_prospect_grade_check
    CHECK (prospect_grade IN ('VIP', 'S', 'A', 'B', 'C', 'D'));
