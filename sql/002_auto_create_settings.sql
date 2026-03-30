-- 회원가입 시 fp_users_settings 자동 생성 트리거
-- Supabase SQL Editor에서 실행

CREATE OR REPLACE FUNCTION fp_handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO fp_users_settings (id, display_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER fp_on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION fp_handle_new_user();
