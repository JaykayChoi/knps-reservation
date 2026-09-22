BEGIN;

ALTER TABLE public.user_settings RENAME TO monitor_settings;

ALTER TABLE public.monitor_settings
    ADD COLUMN options JSONB,
    ADD COLUMN quiet_hours_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN quiet_hours_start TIME(0) NOT NULL DEFAULT '23:00',
    ADD COLUMN quiet_hours_end TIME(0) NOT NULL DEFAULT '07:00';

UPDATE public.monitor_settings
SET options = CASE category
    WHEN 'knps' THEN jsonb_build_object(
        'date_mode', COALESCE(date_mode, 'weekday'),
        'weeks_ahead', COALESCE(weeks_ahead, 8),
        'days', CASE
            WHEN COALESCE(date_mode, 'weekday') = 'weekday'
                 AND cardinality(COALESCE(selected_days, '{}')) = 0
                THEN '["Fri","Sat","Sun"]'::jsonb
            ELSE COALESCE((
                SELECT jsonb_agg(CASE day
                    WHEN '0' THEN 'Mon' WHEN '1' THEN 'Tue' WHEN '2' THEN 'Wed'
                    WHEN '3' THEN 'Thu' WHEN '4' THEN 'Fri' WHEN '5' THEN 'Sat'
                    WHEN '6' THEN 'Sun' ELSE day END ORDER BY ordinal)
                FROM unnest(COALESCE(selected_days, '{}')) WITH ORDINALITY AS d(day, ordinal)
            ), '[]'::jsonb)
        END,
        'start_date', NULLIF(start_date, ''),
        'end_date', NULLIF(end_date, ''),
        'parks', to_jsonb(COALESCE(selected_parks, '{}')),
        'facility_types', to_jsonb(COALESCE(selected_types, '{}')),
        'include_waiting', COALESCE(include_waiting, TRUE)
    )
    WHEN 'moduparking' THEN jsonb_build_object(
        'lot_ids', to_jsonb(COALESCE(selected_parkinglots, '{}'))
    )
    WHEN 'ktx' THEN (COALESCE(ktx_options, '{}') - 'seat_class') || jsonb_build_object(
        'seat_classes', CASE
            WHEN jsonb_typeof(ktx_options->'seat_classes') = 'array'
                THEN ktx_options->'seat_classes'
            WHEN ktx_options->>'seat_class' = 'general' THEN '["general"]'::jsonb
            WHEN ktx_options->>'seat_class' = 'special' THEN '["special"]'::jsonb
            WHEN ktx_options->>'seat_class' = 'either' THEN '["general","special"]'::jsonb
            ELSE '[]'::jsonb
        END
    )
END;

CREATE OR REPLACE FUNCTION public.monitor_options_are_valid(
    p_category public.setting_category,
    p_options JSONB
) RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
STRICT
SET search_path = ''
AS $$
DECLARE
    value JSONB;
    seat TEXT;
    day TEXT;
BEGIN
    IF jsonb_typeof(p_options) <> 'object' THEN RETURN FALSE; END IF;

    IF p_category = 'knps' THEN
        IF NOT (p_options ?& ARRAY['date_mode','weeks_ahead','days','start_date','end_date',
                                  'parks','facility_types','include_waiting'])
           OR p_options - ARRAY['date_mode','weeks_ahead','days','start_date','end_date',
                                'parks','facility_types','include_waiting'] <> '{}'::jsonb
           OR p_options->>'date_mode' NOT IN ('weekday','absolute')
           OR jsonb_typeof(p_options->'weeks_ahead') <> 'number'
           OR jsonb_typeof(p_options->'days') <> 'array'
           OR jsonb_typeof(p_options->'parks') <> 'array'
           OR jsonb_typeof(p_options->'facility_types') <> 'array'
           OR jsonb_typeof(p_options->'include_waiting') <> 'boolean'
        THEN RETURN FALSE; END IF;
        IF (p_options->>'weeks_ahead')::numeric < 0
           OR (p_options->>'weeks_ahead')::numeric > 52
           OR trunc((p_options->>'weeks_ahead')::numeric) <> (p_options->>'weeks_ahead')::numeric
        THEN RETURN FALSE; END IF;
        FOR day IN SELECT jsonb_array_elements_text(p_options->'days') LOOP
            IF day NOT IN ('Mon','Tue','Wed','Thu','Fri','Sat','Sun') THEN RETURN FALSE; END IF;
        END LOOP;
        FOR value IN SELECT jsonb_array_elements(p_options->'parks') LOOP
            IF jsonb_typeof(value) IS DISTINCT FROM 'string' OR value #>> '{}' = '' THEN RETURN FALSE; END IF;
        END LOOP;
        FOR value IN SELECT jsonb_array_elements(p_options->'facility_types') LOOP
            IF jsonb_typeof(value) IS DISTINCT FROM 'string' OR value #>> '{}' = '' THEN RETURN FALSE; END IF;
        END LOOP;
        IF (p_options->>'date_mode') = 'absolute'
           AND (jsonb_typeof(p_options->'start_date') <> 'string'
                OR jsonb_typeof(p_options->'end_date') <> 'string')
        THEN RETURN FALSE; END IF;
        IF jsonb_typeof(p_options->'start_date') NOT IN ('string','null')
           OR jsonb_typeof(p_options->'end_date') NOT IN ('string','null')
           OR ((p_options->'start_date' = 'null'::jsonb) <> (p_options->'end_date' = 'null'::jsonb))
        THEN RETURN FALSE; END IF;
        IF p_options->'start_date' <> 'null'::jsonb AND (
            p_options->>'start_date' !~ '^\d{4}-\d{2}-\d{2}$'
            OR (p_options->>'start_date')::date > (p_options->>'end_date')::date
        ) THEN RETURN FALSE; END IF;
        RETURN TRUE;
    END IF;

    IF p_category = 'moduparking' THEN
        IF NOT (p_options ? 'lot_ids') OR p_options - 'lot_ids' <> '{}'::jsonb
           OR jsonb_typeof(p_options->'lot_ids') <> 'array'
        THEN RETURN FALSE; END IF;
        FOR value IN SELECT jsonb_array_elements(p_options->'lot_ids') LOOP
            IF jsonb_typeof(value) IS DISTINCT FROM 'string' OR value #>> '{}' = '' THEN RETURN FALSE; END IF;
        END LOOP;
        RETURN TRUE;
    END IF;

    IF p_category = 'ktx' THEN
        IF NOT (p_options ?& ARRAY['departure','arrival','date','start_time','end_time','seat_classes'])
           OR p_options - ARRAY['departure','arrival','departure_code','arrival_code','date',
                                'start_time','end_time','seat_classes'] <> '{}'::jsonb
           OR jsonb_typeof(p_options->'departure') <> 'string'
           OR jsonb_typeof(p_options->'arrival') <> 'string'
           OR jsonb_typeof(p_options->'date') <> 'string'
           OR jsonb_typeof(p_options->'start_time') <> 'string'
           OR jsonb_typeof(p_options->'end_time') <> 'string'
           OR jsonb_typeof(p_options->'seat_classes') <> 'array'
           OR jsonb_array_length(p_options->'seat_classes') = 0
           OR (p_options ? 'departure_code') <> (p_options ? 'arrival_code')
           OR p_options->>'departure' = p_options->>'arrival'
           OR p_options->>'departure' = '' OR p_options->>'arrival' = ''
           OR p_options->>'date' !~ '^\d{4}-\d{2}-\d{2}$'
           OR p_options->>'start_time' !~ '^\d{2}:\d{2}$'
           OR p_options->>'end_time' !~ '^\d{2}:\d{2}$'
           OR (p_options->>'start_time')::time > (p_options->>'end_time')::time
        THEN RETURN FALSE; END IF;
        IF p_options ? 'departure_code' AND (
            jsonb_typeof(p_options->'departure_code') <> 'string'
            OR jsonb_typeof(p_options->'arrival_code') <> 'string'
            OR NOT (p_options->>'departure_code' ~ '^\d{4}$')
            OR NOT (p_options->>'arrival_code' ~ '^\d{4}$')
        ) THEN RETURN FALSE; END IF;
        FOR seat IN SELECT jsonb_array_elements_text(p_options->'seat_classes') LOOP
            IF seat NOT IN ('general','special','standing') THEN RETURN FALSE; END IF;
        END LOOP;
        IF (SELECT COUNT(*) FROM jsonb_array_elements_text(p_options->'seat_classes'))
           <> (SELECT COUNT(DISTINCT item) FROM jsonb_array_elements_text(p_options->'seat_classes') AS item)
        THEN RETURN FALSE; END IF;
        RETURN TRUE;
    END IF;
    RETURN FALSE;
EXCEPTION WHEN OTHERS THEN
    RETURN FALSE;
END;
$$;

ALTER TABLE public.monitor_settings
    ALTER COLUMN options SET NOT NULL,
    DROP CONSTRAINT IF EXISTS category_filter_exclusivity,
    ADD CONSTRAINT monitor_options_valid CHECK (
        public.monitor_options_are_valid(category, options)
    ),
    ADD CONSTRAINT monitor_cooldown_valid CHECK (cooldown_days BETWEEN 0 AND 30),
    ADD CONSTRAINT monitor_quiet_hours_valid CHECK (
        NOT quiet_hours_enabled OR quiet_hours_start <> quiet_hours_end
    );

ALTER TABLE public.monitor_settings
    DROP COLUMN weeks_ahead,
    DROP COLUMN selected_days,
    DROP COLUMN start_date,
    DROP COLUMN end_date,
    DROP COLUMN selected_types,
    DROP COLUMN selected_parks,
    DROP COLUMN selected_parkinglots,
    DROP COLUMN include_waiting,
    DROP COLUMN date_mode,
    DROP COLUMN ktx_options;

CREATE SEQUENCE public.monitor_settings_id_seq OWNED BY public.monitor_settings.id;
ALTER TABLE public.monitor_settings ALTER COLUMN id
    SET DEFAULT nextval('public.monitor_settings_id_seq');
SELECT setval('public.monitor_settings_id_seq', COALESCE(MAX(id), 1), COUNT(*) > 0)
FROM public.monitor_settings;

ALTER TABLE public.notification_history RENAME COLUMN setting_id TO monitor_id;
ALTER TABLE public.notification_history RENAME COLUMN park_name TO target_key;
ALTER TABLE public.notification_history RENAME COLUMN facility_type TO item_key;
DROP INDEX IF EXISTS public.idx_notification_history_setting_id;
DROP INDEX IF EXISTS public.idx_notification_history_granular_lookup;
CREATE INDEX notification_history_monitor_lookup
    ON public.notification_history
       (monitor_id, target_date, target_key, item_key, is_waiting, sent_at DESC);

ALTER TABLE public.system_status
    ADD COLUMN last_history_reset_date DATE;

CREATE TABLE public.monitor_catalog (
    category public.setting_category NOT NULL,
    kind TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    label TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (category, kind, entry_key),
    CONSTRAINT monitor_catalog_metadata_object CHECK (jsonb_typeof(metadata) = 'object')
);

INSERT INTO public.monitor_catalog(category, kind, entry_key, label, metadata) VALUES
('knps','facility_type','특화야영장','특화야영장','{}'),
('knps','facility_type','카라반','카라반','{}'),
('knps','facility_type','자동차야영장','자동차야영장','{}'),
('moduparking','parking_lot','109902','투루파킹 KT&G타워 주차장','{"geohash":"wydm77"}'),
('moduparking','parking_lot','106112','카카오 T 대치사거리 주차장','{"geohash":"wydm77"}');

INSERT INTO public.monitor_catalog(category, kind, entry_key, label, metadata)
SELECT 'knps', 'park', park, park, '{}'
FROM unnest(ARRAY[
    '가야산','계룡산','내장산','내장산백암','다도해해상','덕유산','무등산동부',
    '변산반도','북한산','설악산','소백산','소백산북부','오대산','월악산','월출산',
    '주왕산','지리산경남','지리산전북','치악산','태백산','태안해안','팔공산동부',
    '팔공산서부','한려해상','한려해상동부'
]) AS park;

CREATE OR REPLACE FUNCTION public.touch_monitor_updated_at()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;
CREATE TRIGGER monitor_settings_touch_updated_at
BEFORE UPDATE ON public.monitor_settings
FOR EACH ROW EXECUTE FUNCTION public.touch_monitor_updated_at();

CREATE OR REPLACE FUNCTION public.create_monitor(p_monitor JSONB)
RETURNS SETOF public.monitor_settings
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    LOCK TABLE public.monitor_settings IN SHARE ROW EXCLUSIVE MODE;
    IF (SELECT COUNT(*) FROM public.monitor_settings) >= 10 THEN
        RAISE EXCEPTION 'Maximum of 10 monitors reached';
    END IF;
    RETURN QUERY INSERT INTO public.monitor_settings(
        name, category, options, is_active, cooldown_days,
        quiet_hours_enabled, quiet_hours_start, quiet_hours_end,
        telegram_bot_token, telegram_chat_id
    ) VALUES (
        COALESCE(p_monitor->>'name', 'New Monitor'),
        COALESCE(p_monitor->>'category', 'knps')::public.setting_category,
        COALESCE(p_monitor->'options', '{}'::jsonb),
        COALESCE((p_monitor->>'is_active')::boolean, TRUE),
        COALESCE((p_monitor->>'cooldown_days')::integer, 3),
        COALESCE((p_monitor->>'quiet_hours_enabled')::boolean, FALSE),
        COALESCE((p_monitor->>'quiet_hours_start')::time, '23:00'::time),
        COALESCE((p_monitor->>'quiet_hours_end')::time, '07:00'::time),
        COALESCE(p_monitor->>'telegram_bot_token', ''),
        COALESCE(p_monitor->>'telegram_chat_id', '')
    ) RETURNING *;
END;
$$;

DROP FUNCTION IF EXISTS public.truncate_notification_history();
CREATE OR REPLACE FUNCTION public.reset_notification_history_for_kst_day()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    kst_now TIMESTAMP := now() AT TIME ZONE 'Asia/Seoul';
BEGIN
    IF EXTRACT(HOUR FROM kst_now) <> 0 OR EXTRACT(MINUTE FROM kst_now) <> 0 THEN
        RAISE EXCEPTION 'History can only be reset during the first minute of the KST day';
    END IF;
    PERFORM 1 FROM public.system_status WHERE id=1 FOR UPDATE;
    IF (SELECT last_history_reset_date FROM public.system_status WHERE id=1) = kst_now::date THEN
        RETURN FALSE;
    END IF;
    TRUNCATE TABLE public.notification_history;
    UPDATE public.system_status SET last_history_reset_date = kst_now::date WHERE id=1;
    RETURN TRUE;
END;
$$;

REVOKE ALL ON FUNCTION public.create_monitor(JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.reset_notification_history_for_kst_day() FROM PUBLIC;
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
        GRANT EXECUTE ON FUNCTION public.create_monitor(JSONB) TO anon;
        GRANT EXECUTE ON FUNCTION public.reset_notification_history_for_kst_day() TO anon;
        GRANT SELECT ON public.monitor_catalog TO anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
        GRANT EXECUTE ON FUNCTION public.create_monitor(JSONB) TO authenticated;
        GRANT EXECUTE ON FUNCTION public.reset_notification_history_for_kst_day() TO authenticated;
        GRANT SELECT ON public.monitor_catalog TO authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='service_role') THEN
        GRANT EXECUTE ON FUNCTION public.create_monitor(JSONB) TO service_role;
        GRANT EXECUTE ON FUNCTION public.reset_notification_history_for_kst_day() TO service_role;
        GRANT SELECT ON public.monitor_catalog TO service_role;
    END IF;
END $$;

COMMIT;
