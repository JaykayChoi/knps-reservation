SELECT category, COUNT(*) AS rows
FROM public.user_settings
GROUP BY category ORDER BY category;

SELECT COUNT(*) AS invalid_ktx_rows
FROM public.user_settings
WHERE category='ktx' AND (
    jsonb_typeof(ktx_options) <> 'object'
    OR NOT (ktx_options ?& ARRAY['departure','arrival','date','start_time','end_time'])
    OR (NOT (ktx_options ? 'seat_classes')
        AND ktx_options->>'seat_class' NOT IN ('general','special','either'))
);
