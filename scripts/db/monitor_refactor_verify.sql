SELECT COUNT(*) AS monitors FROM public.monitor_settings;
SELECT category, COUNT(*) AS rows FROM public.monitor_settings GROUP BY category ORDER BY category;
SELECT COUNT(*) AS invalid_options FROM public.monitor_settings
WHERE NOT public.monitor_options_are_valid(category, options);
SELECT COUNT(*) AS history_rows FROM public.notification_history;
SELECT COUNT(*) AS catalog_rows FROM public.monitor_catalog;
