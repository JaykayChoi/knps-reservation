BEGIN;

DROP TRIGGER IF EXISTS monitor_settings_touch_updated_at ON public.monitor_settings;
DROP FUNCTION IF EXISTS public.touch_monitor_updated_at();
DROP FUNCTION IF EXISTS public.create_monitor(JSONB);
DROP FUNCTION IF EXISTS public.reset_notification_history_for_kst_day();

ALTER TABLE public.monitor_settings
    ADD COLUMN weeks_ahead INTEGER DEFAULT 8,
    ADD COLUMN selected_days TEXT[] DEFAULT ARRAY['Fri','Sat','Sun'],
    ADD COLUMN start_date TEXT,
    ADD COLUMN end_date TEXT,
    ADD COLUMN selected_types TEXT[] DEFAULT '{}',
    ADD COLUMN selected_parks TEXT[] DEFAULT '{}',
    ADD COLUMN selected_parkinglots TEXT[] DEFAULT '{}',
    ADD COLUMN include_waiting BOOLEAN DEFAULT TRUE,
    ADD COLUMN date_mode TEXT DEFAULT 'weekday',
    ADD COLUMN ktx_options JSONB NOT NULL DEFAULT '{}';

UPDATE public.monitor_settings SET
    date_mode = CASE WHEN category='knps' THEN options->>'date_mode' ELSE 'weekday' END,
    weeks_ahead = CASE WHEN category='knps' THEN (options->>'weeks_ahead')::integer ELSE 0 END,
    selected_days = CASE WHEN category='knps' THEN ARRAY(
        SELECT jsonb_array_elements_text(options->'days')) ELSE '{}' END,
    start_date = CASE WHEN category='knps' THEN NULLIF(options->>'start_date','') END,
    end_date = CASE WHEN category='knps' THEN NULLIF(options->>'end_date','') END,
    selected_types = CASE WHEN category='knps' THEN ARRAY(
        SELECT jsonb_array_elements_text(options->'facility_types')) ELSE '{}' END,
    selected_parks = CASE WHEN category='knps' THEN ARRAY(
        SELECT jsonb_array_elements_text(options->'parks')) ELSE '{}' END,
    selected_parkinglots = CASE WHEN category='moduparking' THEN ARRAY(
        SELECT jsonb_array_elements_text(options->'lot_ids')) ELSE '{}' END,
    include_waiting = CASE WHEN category='knps' THEN (options->>'include_waiting')::boolean ELSE FALSE END,
    ktx_options = CASE WHEN category='ktx' THEN
        CASE options->'seat_classes'
            WHEN '["general"]'::jsonb THEN (options - 'seat_classes') || '{"seat_class":"general"}'
            WHEN '["special"]'::jsonb THEN (options - 'seat_classes') || '{"seat_class":"special"}'
            WHEN '["general","special"]'::jsonb THEN (options - 'seat_classes') || '{"seat_class":"either"}'
            ELSE options
        END
        ELSE '{}'::jsonb END;

ALTER TABLE public.monitor_settings DROP CONSTRAINT monitor_options_valid;
ALTER TABLE public.monitor_settings DROP CONSTRAINT monitor_cooldown_valid;
ALTER TABLE public.monitor_settings DROP CONSTRAINT monitor_quiet_hours_valid;
ALTER TABLE public.monitor_settings ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE public.monitor_settings_id_seq;
DROP FUNCTION public.monitor_options_are_valid(public.setting_category, JSONB);

ALTER TABLE public.monitor_settings
    DROP COLUMN options,
    DROP COLUMN quiet_hours_enabled,
    DROP COLUMN quiet_hours_start,
    DROP COLUMN quiet_hours_end;

ALTER TABLE public.notification_history RENAME COLUMN monitor_id TO setting_id;
ALTER TABLE public.notification_history RENAME COLUMN target_key TO park_name;
ALTER TABLE public.notification_history RENAME COLUMN item_key TO facility_type;
DROP INDEX IF EXISTS public.notification_history_monitor_lookup;
CREATE INDEX idx_notification_history_granular_lookup
    ON public.notification_history(setting_id, target_date, park_name, facility_type, is_waiting);

ALTER TABLE public.system_status DROP COLUMN last_history_reset_date;
DROP TABLE public.monitor_catalog;
ALTER TABLE public.monitor_settings RENAME TO user_settings;

ALTER TABLE public.user_settings ADD CONSTRAINT category_filter_exclusivity CHECK (
    (category = 'knps' AND cardinality(COALESCE(selected_parkinglots, '{}')) = 0 AND ktx_options = '{}')
    OR (category = 'moduparking' AND cardinality(COALESCE(selected_parks, '{}')) = 0
        AND cardinality(COALESCE(selected_types, '{}')) = 0 AND ktx_options = '{}')
    OR (category = 'ktx' AND cardinality(COALESCE(selected_parks, '{}')) = 0
        AND cardinality(COALESCE(selected_types, '{}')) = 0
        AND cardinality(COALESCE(selected_parkinglots, '{}')) = 0
        AND jsonb_typeof(ktx_options) = 'object')
);

COMMIT;
