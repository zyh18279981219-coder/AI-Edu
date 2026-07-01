-- AI-Education MySQL bootstrap script.
-- Run as a MySQL administrator before importing database/schema.sql.
--
-- Default development credentials:
--   database: ai_education_design
--   user:     ai_education_design
--   password: ai_education_design
--
-- Change these values before production deployment.

CREATE DATABASE IF NOT EXISTS ai_education_design
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'ai_education_design'@'%'
  IDENTIFIED BY 'ai_education_design';

GRANT ALL PRIVILEGES ON ai_education_design.* TO 'ai_education_design'@'%';

FLUSH PRIVILEGES;
