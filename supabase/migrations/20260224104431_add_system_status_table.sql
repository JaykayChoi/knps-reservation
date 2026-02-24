-- Add system_status table for tracking system metadata including last check time
CREATE TABLE IF NOT EXISTS system_status (
    id BIGINT PRIMARY KEY DEFAULT 1,
    last_check_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT single_row CHECK (id = 1)
);
-- Insert initial row if table is empty
INSERT INTO system_status (id, last_check_at)
VALUES (1, NOW())
ON CONFLICT (id) DO NOTHING;
CREATE INDEX IF NOT EXISTS idx_system_status_id ON system_status(id);