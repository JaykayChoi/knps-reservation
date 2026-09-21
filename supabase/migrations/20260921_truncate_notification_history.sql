-- Allow the backend's configured Supabase key to clear cooldown history.
CREATE OR REPLACE FUNCTION public.truncate_notification_history()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF EXTRACT(HOUR FROM now() AT TIME ZONE 'Asia/Seoul') <> 0
       OR EXTRACT(MINUTE FROM now() AT TIME ZONE 'Asia/Seoul') <> 0 THEN
        RAISE EXCEPTION 'History can only be truncated during the first minute of the KST day';
    END IF;
    TRUNCATE TABLE public.notification_history;
END;
$$;

REVOKE ALL ON FUNCTION public.truncate_notification_history() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.truncate_notification_history() TO anon, authenticated, service_role;
