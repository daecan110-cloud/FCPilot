-- pioneer-photos 버킷 생성 (간판 사진 저장)
INSERT INTO storage.buckets (id, name, public)
VALUES ('pioneer-photos', 'pioneer-photos', true)
ON CONFLICT (id) DO NOTHING;

-- 업로드: 인증된 사용자만 본인 폴더에 업로드
CREATE POLICY "fc_upload_own_photos" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (
        bucket_id = 'pioneer-photos'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- 조회: public 버킷이므로 별도 정책 불필요 (get_public_url 사용)

-- 삭제: 본인 폴더만
CREATE POLICY "fc_delete_own_photos" ON storage.objects
    FOR DELETE TO authenticated
    USING (
        bucket_id = 'pioneer-photos'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );
