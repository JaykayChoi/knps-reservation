-- Migration: Watch 모두의주차장 parking lots (monthly pass availability)
-- Generated: 2026-08-05

-- Stores the modu.kr parkinglotSeq values a setting monitors, e.g. {'109902','106112'}.
ALTER TABLE user_settings
ADD COLUMN IF NOT EXISTS selected_parkinglots TEXT[] DEFAULT '{}';

UPDATE user_settings
SET selected_parkinglots = '{}'
WHERE selected_parkinglots IS NULL;
