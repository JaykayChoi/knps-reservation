DO $$
DECLARE
    next_id BIGINT;
BEGIN
    IF to_regclass('public.monitor_settings') IS NULL THEN
        RAISE EXCEPTION 'monitor_settings missing';
    END IF;
    IF to_regclass('public.user_settings') IS NOT NULL THEN
        RAISE EXCEPTION 'legacy user_settings remains';
    END IF;
    IF (SELECT COUNT(*) FROM public.monitor_settings) <> 4 THEN
        RAISE EXCEPTION 'monitor count changed';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.monitor_settings WHERE id=1 AND category='knps'
        AND options->'parks' = '["덕유산"]'::jsonb
        AND options->'facility_types' = '["카라반"]'::jsonb
        AND options->>'include_waiting' = 'false'
        AND quiet_hours_enabled = false
        AND created_at = '2026-01-01T00:00:00Z'
    ) THEN RAISE EXCEPTION 'KNPS semantics changed'; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.monitor_settings WHERE id=2 AND category='moduparking'
        AND options->'lot_ids' = '["109902"]'::jsonb AND NOT is_active
        AND cooldown_days=0
    ) THEN RAISE EXCEPTION 'parking semantics changed'; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.monitor_settings WHERE id=3 AND category='ktx'
        AND options->'seat_classes' = '["general","special"]'::jsonb
        AND NOT (options ? 'seat_class')
    ) THEN RAISE EXCEPTION 'legacy KTX class not migrated'; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM public.monitor_settings WHERE id=4
        AND options->'seat_classes' = '["general","standing"]'::jsonb
        AND options->>'departure_code'='0501'
    ) THEN RAISE EXCEPTION 'new KTX classes changed'; END IF;
    IF (SELECT COUNT(*) FROM public.notification_history) <> 3 OR NOT EXISTS (
        SELECT 1 FROM public.notification_history
        WHERE monitor_id=3 AND target_key='KTX:서울→부산'
        AND item_key='001:090000:general'
    ) THEN RAISE EXCEPTION 'notification history changed'; END IF;
    IF NOT EXISTS (SELECT 1 FROM public.monitor_catalog WHERE category='moduparking'
        AND entry_key='109902') THEN RAISE EXCEPTION 'catalog missing'; END IF;

    INSERT INTO public.monitor_settings(name, category, options)
    VALUES ('Identity', 'moduparking', '{"lot_ids":[]}'::jsonb)
    RETURNING id INTO next_id;
    IF next_id <> 5 THEN RAISE EXCEPTION 'identity sequence is wrong: %', next_id; END IF;

    BEGIN
        INSERT INTO public.monitor_settings(name, category, options)
        VALUES ('Invalid', 'ktx', '{"seat_classes":[]}'::jsonb);
        RAISE EXCEPTION 'invalid options accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
END $$;

SELECT 'refactor assertions passed' AS result;
