CREATE TYPE public.setting_category AS ENUM ('knps', 'moduparking', 'ktx');

CREATE TABLE public.user_settings (
    id BIGINT PRIMARY KEY,
    name TEXT DEFAULT 'New Settings',
    category public.setting_category NOT NULL DEFAULT 'knps',
    is_active BOOLEAN DEFAULT TRUE,
    date_mode TEXT DEFAULT 'weekday',
    weeks_ahead INTEGER DEFAULT 8,
    selected_days TEXT[] DEFAULT ARRAY['Fri','Sat','Sun'],
    start_date TEXT,
    end_date TEXT,
    selected_types TEXT[] DEFAULT '{}',
    selected_parks TEXT[] DEFAULT '{}',
    selected_parkinglots TEXT[] DEFAULT '{}',
    include_waiting BOOLEAN DEFAULT TRUE,
    cooldown_days INTEGER DEFAULT 3,
    telegram_bot_token TEXT DEFAULT '',
    telegram_chat_id TEXT DEFAULT '',
    ktx_options JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.notification_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    setting_id BIGINT REFERENCES public.user_settings(id) ON DELETE CASCADE,
    target_date TEXT,
    park_name TEXT,
    facility_type TEXT,
    is_waiting BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE public.system_status (
    id BIGINT PRIMARY KEY DEFAULT 1,
    last_check_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO public.system_status(id, last_check_at)
VALUES (1, '2026-09-21T12:00:00Z');

INSERT INTO public.user_settings
    (id, name, category, is_active, date_mode, weeks_ahead, selected_days,
     start_date, end_date, selected_types, selected_parks, selected_parkinglots,
     include_waiting, cooldown_days, telegram_bot_token, telegram_chat_id,
     ktx_options, created_at, updated_at)
VALUES
    (1, 'Camp', 'knps', true, 'weekday', 4, ARRAY['Fri'], '2026-10-01',
     '2026-10-02', ARRAY['카라반'], ARRAY['덕유산'], '{}', false, 3,
     'secret-one', 'chat-one', '{}', '2026-01-01T00:00:00Z', '2026-02-01T00:00:00Z'),
    (2, 'Parking', 'moduparking', false, 'weekday', 0, '{}', NULL, NULL,
     '{}', '{}', ARRAY['109902'], false, 0, 'secret-two', 'chat-two', '{}',
     '2026-01-02T00:00:00Z', '2026-02-02T00:00:00Z'),
    (3, 'Train legacy', 'ktx', true, 'weekday', 0, '{}', NULL, NULL,
     '{}', '{}', '{}', false, 30, 'secret-three', 'chat-three',
     '{"departure":"서울","arrival":"부산","date":"2099-10-01","start_time":"08:00","end_time":"18:00","seat_class":"either"}',
     '2026-01-03T00:00:00Z', '2026-02-03T00:00:00Z'),
    (4, 'Train standing', 'ktx', true, 'weekday', 0, '{}', NULL, NULL,
     '{}', '{}', '{}', false, 1, '', '',
     '{"departure":"광명","departure_code":"0501","arrival":"부산","arrival_code":"0020","date":"2099-10-02","start_time":"09:00","end_time":"10:00","seat_classes":["general","standing"]}',
     '2026-01-04T00:00:00Z', '2026-02-04T00:00:00Z');

INSERT INTO public.notification_history
    (setting_id, target_date, park_name, facility_type, is_waiting, sent_at)
VALUES
    (1, '20991001', '덕유산', '카라반', false, '2026-09-21T01:00:00Z'),
    (2, 'MONTHLY', '투루파킹 KT&G타워 주차장', '월정기권', false, '2026-09-21T02:00:00Z'),
    (3, '20991001', 'KTX:서울→부산', '001:090000:general', false, '2026-09-21T03:00:00Z');
