-- Run this in your MySQL database to add the scheduler_settings table.
-- Your existing tables (admins, clients, invoices, calls) are untouched.

USE ai_debt_reminder;

CREATE TABLE IF NOT EXISTS scheduler_settings (
    id                   INT PRIMARY KEY DEFAULT 1,
    call_time            VARCHAR(5)  NOT NULL DEFAULT '09:00',
    active_days          JSON        NOT NULL,
    is_active            TINYINT(1)  NOT NULL DEFAULT 1,
    max_retries          INT         NOT NULL DEFAULT 3,
    retry_interval_hours INT         NOT NULL DEFAULT 24,
    updated_at           TIMESTAMP   NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Insert default row (only if it doesn't already exist)
INSERT IGNORE INTO scheduler_settings
    (id, call_time, active_days, is_active, max_retries, retry_interval_hours)
VALUES
    (1, '09:00', '["Mon","Tue","Wed","Thu","Fri"]', 1, 3, 24);
