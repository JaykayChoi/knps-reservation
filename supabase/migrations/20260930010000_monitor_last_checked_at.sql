-- Completion time is shared by the web checks and the local KTX worker.
-- Existing and duplicated monitors start without a completed check.
ALTER TABLE public.monitor_settings
    ADD COLUMN last_checked_at TIMESTAMPTZ;

COMMENT ON COLUMN public.monitor_settings.last_checked_at IS
    'UTC completion time of the last successful check, including notification processing. Skipped or failed checks leave it unchanged.';
