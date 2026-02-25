-- Migration: Granular columns for notification_history
-- Generated: 2026-02-25

-- 1. Add granular columns to notification_history
ALTER TABLE notification_history ADD COLUMN IF NOT EXISTS target_date TEXT;
ALTER TABLE notification_history ADD COLUMN IF NOT EXISTS park_name TEXT;
ALTER TABLE notification_history ADD COLUMN IF NOT EXISTS facility_type TEXT;
ALTER TABLE notification_history ADD COLUMN IF NOT EXISTS is_waiting BOOLEAN DEFAULT FALSE;

-- 2. Populate new columns from identifier if possible (Format: 20260301_Park_Facility)
-- This is optional but good for existing data
UPDATE notification_history 
SET 
    target_date = SPLIT_PART(identifier, '_', 1),
    park_name = SPLIT_PART(identifier, '_', 2),
    facility_type = SPLIT_PART(identifier, '_', 3)
WHERE target_date IS NULL AND identifier LIKE '%_%_%';

-- 3. Update indices for the new comparison logic
CREATE INDEX IF NOT EXISTS idx_notification_history_granular_lookup 
ON notification_history(setting_id, target_date, park_name, facility_type, is_waiting);

-- 4. Drop identifier column as it is redundant for granular logic
ALTER TABLE notification_history DROP COLUMN IF EXISTS identifier;
