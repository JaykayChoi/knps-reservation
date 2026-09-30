DO $$
DECLARE
    created public.monitor_settings;
BEGIN
    IF EXISTS (SELECT 1 FROM public.monitor_settings WHERE last_checked_at IS NOT NULL) THEN
        RAISE EXCEPTION 'Existing completion times must remain unknown';
    END IF;
    UPDATE public.monitor_settings SET last_checked_at = '2026-09-29T15:01:02Z' WHERE id = 3;
    UPDATE public.monitor_settings SET name = 'Renamed train' WHERE id = 3;
    IF NOT EXISTS (SELECT 1 FROM public.monitor_settings
                   WHERE id = 3 AND last_checked_at = '2026-09-30T00:01:02+09:00') THEN
        RAISE EXCEPTION 'Completion time was not preserved or timezone is wrong';
    END IF;
    SELECT * INTO created FROM public.create_monitor(
        '{"name":"New parking","category":"moduparking","options":{"lot_ids":[]}}');
    IF created.id IS NULL OR created.last_checked_at IS NOT NULL THEN
        RAISE EXCEPTION 'New monitor must start without a completed check';
    END IF;
    IF (SELECT COUNT(*) FROM public.notification_history) <> 3 THEN
        RAISE EXCEPTION 'Completion migration changed notification history';
    END IF;
END $$;

SELECT 'completion time assertions passed' AS result;
