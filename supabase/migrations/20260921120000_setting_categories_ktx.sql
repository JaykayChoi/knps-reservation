BEGIN;

CREATE TYPE public.setting_category AS ENUM ('knps', 'moduparking', 'ktx');
ALTER TABLE public.user_settings
    ADD COLUMN category public.setting_category NOT NULL DEFAULT 'knps',
    ADD COLUMN ktx_options JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Lock allocation of IDs while splitting existing mixed monitors. Retain the
-- original row for KNPS, and move only monthly-pass history to the parking row.
LOCK TABLE public.user_settings IN ACCESS EXCLUSIVE MODE;
DO $$
DECLARE
    original public.user_settings%ROWTYPE;
    new_id BIGINT;
BEGIN
    SELECT COALESCE(MAX(id), 0) INTO new_id FROM public.user_settings;
    FOR original IN SELECT * FROM public.user_settings
        WHERE cardinality(selected_parkinglots) > 0 ORDER BY id
    LOOP
        new_id := new_id + 1;
        INSERT INTO public.user_settings
            (id, name, category, is_active, cooldown_days, telegram_bot_token,
             telegram_chat_id, selected_parkinglots, selected_parks, selected_types,
             selected_days, weeks_ahead, include_waiting, created_at, updated_at)
        VALUES
            (new_id, original.name || ' (Parking)', 'moduparking', original.is_active,
             original.cooldown_days, original.telegram_bot_token, original.telegram_chat_id,
             original.selected_parkinglots, '{}', '{}', '{}', 0, FALSE,
             original.created_at, NOW());
        UPDATE public.notification_history SET setting_id = new_id
            WHERE setting_id = original.id AND target_date = 'MONTHLY';
        UPDATE public.user_settings SET selected_parkinglots = '{}'
            WHERE id = original.id;
    END LOOP;
END $$;

ALTER TABLE public.user_settings ADD CONSTRAINT category_filter_exclusivity CHECK (
    (category = 'knps' AND cardinality(COALESCE(selected_parkinglots, '{}')) = 0 AND ktx_options = '{}')
    OR (category = 'moduparking' AND cardinality(COALESCE(selected_parks, '{}')) = 0
        AND cardinality(COALESCE(selected_types, '{}')) = 0 AND ktx_options = '{}')
    OR (category = 'ktx' AND cardinality(COALESCE(selected_parks, '{}')) = 0
        AND cardinality(COALESCE(selected_types, '{}')) = 0
        AND cardinality(COALESCE(selected_parkinglots, '{}')) = 0
        AND jsonb_typeof(ktx_options) = 'object'
        AND ktx_options ?& ARRAY['departure', 'arrival', 'date', 'start_time', 'end_time', 'seat_class'])
);
CREATE INDEX user_settings_category_active ON public.user_settings(category, is_active);
ALTER TABLE public.system_status ADD COLUMN ktx_status JSONB NOT NULL DEFAULT '{"status":"idle"}';
COMMIT;
