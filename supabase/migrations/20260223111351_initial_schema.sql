-- 사용자 설정 테이블
CREATE TABLE IF NOT EXISTS user_settings (
    id BIGINT PRIMARY KEY,
    weeks_ahead INTEGER DEFAULT 8,
    selected_days TEXT[] DEFAULT '{"Fri", "Sat", "Sun"}',
    selected_types TEXT[] DEFAULT '{"특화야영장", "카라반", "자동차야영장"}',
    selected_parks TEXT[] DEFAULT '{}',
    cooldown_days INTEGER DEFAULT 3,
    telegram_bot_token TEXT DEFAULT '',
    telegram_chat_id TEXT DEFAULT ''
);

-- 알림 이력 테이블
CREATE TABLE IF NOT EXISTS notification_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    identifier TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- 기본 설정 데이터 삽입
INSERT INTO user_settings (id) 
VALUES (1)
ON CONFLICT (id) DO NOTHING;
