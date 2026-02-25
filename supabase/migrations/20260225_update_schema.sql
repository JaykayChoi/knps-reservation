-- Migration: Add setting_id to notification_history and include_waiting to user_settings
-- Generated: 2026-02-25

-- 1. Add include_waiting to user_settings (already applied in previous step, but included here for documentation)
DO $$ 
BEGIN 
    IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='user_settings' AND COLUMN_NAME='include_waiting') THEN
        ALTER TABLE user_settings ADD COLUMN include_waiting BOOLEAN DEFAULT TRUE;
    END IF;
END $$;

-- 2. Add setting_id to notification_history
-- Link history to specific settings for per-setting cooldown management
ALTER TABLE notification_history ADD COLUMN IF NOT EXISTS setting_id INT REFERENCES user_settings(id) ON DELETE CASCADE;

-- 3. Index for performance
CREATE INDEX IF NOT EXISTS idx_notification_history_setting_id ON notification_history(setting_id);
CREATE INDEX IF NOT EXISTS idx_notification_history_identifier_setting ON notification_history(identifier, setting_id);
