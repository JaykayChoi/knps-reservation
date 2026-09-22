DO $$
BEGIN
    IF to_regclass('public.user_settings') IS NULL THEN
        RAISE EXCEPTION 'user_settings not restored';
    END IF;
    IF to_regclass('public.monitor_settings') IS NOT NULL THEN
        RAISE EXCEPTION 'monitor_settings remains';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.user_settings WHERE id=1
        AND selected_parks=ARRAY['덕유산'] AND selected_types=ARRAY['카라반']
        AND selected_days=ARRAY['Fri']) THEN RAISE EXCEPTION 'KNPS rollback failed'; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.user_settings WHERE id=2
        AND selected_parkinglots=ARRAY['109902']) THEN RAISE EXCEPTION 'parking rollback failed'; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.user_settings WHERE id=3
        AND ktx_options->>'seat_class'='either') THEN RAISE EXCEPTION 'KTX rollback failed'; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.notification_history WHERE setting_id=3
        AND park_name='KTX:서울→부산' AND facility_type='001:090000:general')
        THEN RAISE EXCEPTION 'history rollback failed'; END IF;
END $$;
SELECT 'rollback assertions passed' AS result;
