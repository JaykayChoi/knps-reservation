DO $$
DECLARE parking_id bigint;
BEGIN
    SELECT id INTO STRICT parking_id FROM user_settings WHERE category='moduparking';
    IF (SELECT COUNT(*) FROM user_settings) <> 3 THEN RAISE EXCEPTION 'Settings lost'; END IF;
    IF NOT EXISTS (SELECT 1 FROM user_settings WHERE id=1 AND category='knps'
        AND selected_parks=ARRAY['Park'] AND selected_parkinglots='{}')
        THEN RAISE EXCEPTION 'KNPS fields not preserved'; END IF;
    IF NOT EXISTS (SELECT 1 FROM user_settings WHERE id=parking_id
        AND selected_parkinglots=ARRAY['12'] AND NOT is_active AND cooldown_days=5)
        THEN RAISE EXCEPTION 'Parking settings not preserved'; END IF;
    IF NOT EXISTS (SELECT 1 FROM notification_history WHERE setting_id=parking_id AND target_date='MONTHLY')
        THEN RAISE EXCEPTION 'Monthly history not moved'; END IF;
    IF NOT EXISTS (SELECT 1 FROM notification_history WHERE setting_id=1 AND target_date='20991001')
        THEN RAISE EXCEPTION 'KNPS history moved incorrectly'; END IF;
    BEGIN
        UPDATE user_settings SET selected_parkinglots=ARRAY['12'] WHERE id=1;
        RAISE EXCEPTION 'Mixed filters accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    INSERT INTO user_settings(id, category, selected_parks, selected_types, ktx_options)
    VALUES (4, 'ktx', '{}', '{}', '{"departure":"서울","arrival":"부산","date":"2099-10-01","start_time":"08:00","end_time":"18:00","seat_class":"either"}');
    IF (SELECT ktx_status->>'status' FROM system_status WHERE id=1) <> 'idle'
        THEN RAISE EXCEPTION 'Missing initial KTX status'; END IF;
END $$;
SELECT 'Category migration assertions passed' AS result;
