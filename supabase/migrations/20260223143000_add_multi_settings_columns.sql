-- Add multi-settings support columns to user_settings table
ALTER TABLE user_settings 
ADD COLUMN IF NOT EXISTS name TEXT DEFAULT 'New Settings',
ADD COLUMN IF NOT EXISTS date_mode TEXT DEFAULT 'weekday',
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
-- Add start_date and end_date columns if they don't exist
ALTER TABLE user_settings 
ADD COLUMN IF NOT EXISTS start_date TEXT,
ADD COLUMN IF NOT EXISTS end_date TEXT;
-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_settings_is_active ON user_settings(is_active);
CREATE INDEX IF NOT EXISTS idx_user_settings_created_at ON user_settings(created_at);
-- Set default values for existing rows
UPDATE user_settings 
SET 
    name = COALESCE(name, 'Default Settings'),
    date_mode = COALESCE(date_mode, 'weekday'),
    is_active = COALESCE(is_active, TRUE),
    created_at = COALESCE(created_at, NOW()),
    updated_at = NOW()
WHERE name IS NULL OR date_mode IS NULL OR is_active IS NULL OR created_at IS NULL;