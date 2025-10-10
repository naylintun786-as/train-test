-- For shared host with a single database
-- Creates prefixed tables only (no CREATE DATABASE)

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS time_stamp_shifts;
DROP TABLE IF EXISTS time_stamp_users;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE IF NOT EXISTS time_stamp_users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_name VARCHAR(150) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_time_stamp_users_name (user_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS time_stamp_shifts (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  work_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  notes VARCHAR(500) NULL,
  total_hours DECIMAL(6,2) AS (ROUND(TIME_TO_SEC(TIMEDIFF(end_time, start_time)) / 3600, 2)) STORED,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_time_stamp_shifts_user FOREIGN KEY (user_id) REFERENCES time_stamp_users(id) ON DELETE CASCADE ON UPDATE CASCADE,
  INDEX idx_time_stamp_shifts_user_date (user_id, work_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed users
INSERT INTO time_stamp_users (user_name) VALUES
  ('alice'), ('bob'), ('charlie');

-- Seed shifts
INSERT INTO time_stamp_shifts (user_id, work_date, start_time, end_time, notes) VALUES
  (1, CURDATE(), '09:00:00', '17:00:00', 'Initial seed shift');
