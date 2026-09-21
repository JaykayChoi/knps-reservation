-- Only for a fresh disposable database. Apply legacy migrations first.
UPDATE user_settings SET name='Mixed', selected_parks=ARRAY['Park'],
    selected_parkinglots=ARRAY['12'], cooldown_days=5, is_active=FALSE WHERE id=1;
INSERT INTO user_settings(id, name, selected_parkinglots) VALUES (2, 'KNPS only', '{}');
INSERT INTO notification_history(setting_id, target_date, park_name, facility_type, is_waiting)
VALUES (1, 'MONTHLY', 'Lot', 'Monthly', FALSE), (1, '20991001', 'Park', 'Camp', FALSE);
