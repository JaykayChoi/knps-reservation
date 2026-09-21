BEGIN;

ALTER TABLE public.user_settings DROP CONSTRAINT category_filter_exclusivity;
ALTER TABLE public.user_settings ADD CONSTRAINT category_filter_exclusivity CHECK (
    (category = 'knps' AND cardinality(COALESCE(selected_parkinglots, '{}')) = 0 AND ktx_options = '{}')
    OR (category = 'moduparking' AND cardinality(COALESCE(selected_parks, '{}')) = 0
        AND cardinality(COALESCE(selected_types, '{}')) = 0 AND ktx_options = '{}')
    OR (category = 'ktx' AND cardinality(COALESCE(selected_parks, '{}')) = 0
        AND cardinality(COALESCE(selected_types, '{}')) = 0
        AND cardinality(COALESCE(selected_parkinglots, '{}')) = 0
        AND jsonb_typeof(ktx_options) = 'object'
        AND ktx_options ?& ARRAY['departure', 'arrival', 'date', 'start_time', 'end_time']
        AND (
            (ktx_options->>'seat_class' IN ('general', 'special', 'either'))
            OR (
                jsonb_typeof(ktx_options->'seat_classes') = 'array'
                AND jsonb_array_length(ktx_options->'seat_classes') > 0
                AND (ktx_options->'seat_classes') <@ '["general", "special", "standing"]'::jsonb
            )
        ))
);

COMMIT;
