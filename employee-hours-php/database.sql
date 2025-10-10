-- Employee Working Hours Registration System
-- Database schema and seed data
--
-- Compatible with MySQL 8.x and MariaDB 10.4+

-- Create database
CREATE DATABASE IF NOT EXISTS employee_hours CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE employee_hours;

-- Drop existing tables (for idempotent import during development)
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS Payments;
DROP TABLE IF EXISTS Work_Shifts;
DROP TABLE IF EXISTS Users;
DROP TABLE IF EXISTS Departments;
SET FOREIGN_KEY_CHECKS = 1;

-- Departments (optional)
CREATE TABLE Departments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  UNIQUE KEY uniq_department_name (name)
) ENGINE=InnoDB;

-- Users (employees)
CREATE TABLE Users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(150) NOT NULL,
  email VARCHAR(150) NOT NULL,
  department_id INT NULL,
  hourly_rate DECIMAL(10,2) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_users_department FOREIGN KEY (department_id) REFERENCES Departments(id) ON UPDATE CASCADE ON DELETE SET NULL,
  UNIQUE KEY uniq_users_email (email)
) ENGINE=InnoDB;

-- Work_Shifts (timesheet entries)
-- total_hours is a STORED generated column to compute hours automatically
CREATE TABLE Work_Shifts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  work_date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  notes VARCHAR(500) NULL,
  -- Calculates decimal hours rounded to 2 decimals
  total_hours DECIMAL(6,2) AS (ROUND(TIME_TO_SEC(TIMEDIFF(end_time, start_time)) / 3600, 2)) STORED,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_shifts_user FOREIGN KEY (user_id) REFERENCES Users(id) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_shifts_user_date (user_id, work_date)
) ENGINE=InnoDB;

-- Optional Payments table (not used by UI but provided)
CREATE TABLE Payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  notes VARCHAR(500) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_payments_user FOREIGN KEY (user_id) REFERENCES Users(id) ON UPDATE CASCADE ON DELETE CASCADE,
  INDEX idx_payments_user_period (user_id, period_start, period_end)
) ENGINE=InnoDB;

-- Seed data for Departments
INSERT INTO Departments (name) VALUES
  ('Engineering'),
  ('Operations'),
  ('Sales'),
  ('HR');

-- Seed data for Users
INSERT INTO Users (full_name, email, department_id, hourly_rate) VALUES
  ('Alice Johnson', 'alice@example.com', 1, 35.00),
  ('Bob Smith', 'bob@example.com', 2, 28.50),
  ('Charlie Davis', 'charlie@example.com', 1, 42.00),
  ('Diana Prince', 'diana@example.com', 3, 30.00);

-- Seed data for Work_Shifts
INSERT INTO Work_Shifts (user_id, work_date, start_time, end_time, notes) VALUES
  (1, '2025-10-01', '09:00:00', '17:30:00', 'Regular shift'),
  (1, '2025-10-02', '10:00:00', '18:00:00', 'Late start'),
  (2, '2025-10-01', '08:30:00', '16:30:00', 'Warehouse'),
  (3, '2025-10-01', '09:00:00', '12:00:00', 'Half-day'),
  (4, '2025-10-03', '09:00:00', '17:00:00', 'Client meetings');

-- Example payment entries (optional)
INSERT INTO Payments (user_id, period_start, period_end, amount, notes) VALUES
  (1, '2025-09-16', '2025-09-30', 1400.00, 'Bi-weekly'),
  (2, '2025-09-16', '2025-09-30', 1140.00, 'Bi-weekly');
