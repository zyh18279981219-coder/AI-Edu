-- Module data support tables and fields for the 12-module design review.
-- Safe to run repeatedly on MySQL 8.0+.

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

DELIMITER $$

DROP PROCEDURE IF EXISTS add_column_if_missing $$
CREATE PROCEDURE add_column_if_missing(
    IN p_table_name VARCHAR(128),
    IN p_column_name VARCHAR(128),
    IN p_column_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = p_table_name
          AND column_name = p_column_name
    ) THEN
        SET @ddl = CONCAT('ALTER TABLE `', p_table_name, '` ADD COLUMN `', p_column_name, '` ', p_column_definition);
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END $$

DROP PROCEDURE IF EXISTS add_index_if_missing $$
CREATE PROCEDURE add_index_if_missing(
    IN p_table_name VARCHAR(128),
    IN p_index_name VARCHAR(128),
    IN p_index_columns TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = p_table_name
          AND index_name = p_index_name
    ) THEN
        SET @ddl = CONCAT('CREATE INDEX `', p_index_name, '` ON `', p_table_name, '` (', p_index_columns, ')');
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END $$

DELIMITER ;

CALL add_column_if_missing('llm_logs', 'status', 'VARCHAR(50) NOT NULL DEFAULT ''success'' AFTER model');
CALL add_column_if_missing('llm_logs', 'duration_ms', 'INT NULL AFTER status');
CALL add_column_if_missing('llm_logs', 'prompt_tokens', 'INT NULL AFTER duration_ms');
CALL add_column_if_missing('llm_logs', 'completion_tokens', 'INT NULL AFTER prompt_tokens');
CALL add_column_if_missing('llm_logs', 'total_tokens', 'INT NULL AFTER completion_tokens');
CALL add_column_if_missing('llm_logs', 'cost_estimate', 'DECIMAL(12,6) NULL AFTER total_tokens');
CALL add_column_if_missing('llm_logs', 'request_id', 'VARCHAR(128) NULL AFTER cost_estimate');
CALL add_column_if_missing('llm_logs', 'error_message', 'TEXT NULL AFTER request_id');

CALL add_column_if_missing('course_nodes', 'normalized_name', 'VARCHAR(500) NULL AFTER node_name');
CALL add_column_if_missing('course_nodes', 'node_type', 'VARCHAR(50) NULL AFTER normalized_name');
CALL add_column_if_missing('course_nodes', 'sort_order', 'INT NOT NULL DEFAULT 0 AFTER parent_node_id');
CALL add_column_if_missing('course_nodes', 'publish_status', 'VARCHAR(50) NOT NULL DEFAULT ''published'' AFTER sort_order');

CALL add_column_if_missing('homework_assignment_knowledge_points', 'coverage_weight', 'DECIMAL(6,4) NULL AFTER confirmed_by_teacher');

CREATE TABLE IF NOT EXISTS resource_candidates (
    candidate_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    query_text VARCHAR(500),
    title VARCHAR(500),
    url VARCHAR(1000) NOT NULL,
    embed_url VARCHAR(1000),
    relevance_score DECIMAL(6,4),
    reliability_score DECIMAL(6,4),
    embeddable TINYINT(1) NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'candidate',
    reject_reason TEXT,
    bound_resource_id INT NULL,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_resource_candidates_course_url (course_id, url(255)),
    INDEX idx_resource_candidates_node (course_id, node_id, status),
    INDEX idx_resource_candidates_provider (provider),
    CONSTRAINT fk_rc_course_node
        FOREIGN KEY (course_id, node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rc_bound_resource
        FOREIGN KEY (bound_resource_id)
        REFERENCES resources(resource_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS course_publish_snapshots (
    snapshot_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    version_no INT NOT NULL,
    structure_snapshot_json JSON NOT NULL,
    resource_snapshot_json JSON,
    ability_snapshot_json JSON,
    published_by VARCHAR(100),
    published_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_course_publish_snapshot_version (course_id, version_no),
    INDEX idx_course_publish_snapshot_course_time (course_id, published_at),
    CONSTRAINT fk_cps_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quiz_definitions (
    definition_id VARCHAR(100) PRIMARY KEY,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    title VARCHAR(500) NOT NULL,
    question_type VARCHAR(50) NOT NULL DEFAULT '客观题/选择题',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    version_no INT NOT NULL DEFAULT 1,
    created_by VARCHAR(100),
    published_at DATETIME NULL,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_qd_course_node_status (course_id, node_id, status),
    CONSTRAINT fk_qd_course_node
        FOREIGN KEY (course_id, node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quiz_questions (
    question_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    definition_id VARCHAR(100) NOT NULL,
    sequence_order INT NOT NULL DEFAULT 0,
    question_type VARCHAR(50) NOT NULL,
    stem TEXT NOT NULL,
    options_json JSON,
    answer_json JSON,
    analysis TEXT,
    score DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_qq_definition_order (definition_id, sequence_order),
    CONSTRAINT fk_qq_definition
        FOREIGN KEY (definition_id)
        REFERENCES quiz_definitions(definition_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quiz_definition_versions (
    version_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    definition_id VARCHAR(100) NOT NULL,
    version_no INT NOT NULL,
    snapshot_json JSON NOT NULL,
    created_by VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_qdv_definition_version (definition_id, version_no),
    CONSTRAINT fk_qdv_definition
        FOREIGN KEY (definition_id)
        REFERENCES quiz_definitions(definition_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS diagnosis_rules (
    rule_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_code VARCHAR(100) NOT NULL,
    rule_name VARCHAR(200) NOT NULL,
    scope VARCHAR(50) NOT NULL DEFAULT 'global',
    course_id VARCHAR(100) NULL,
    threshold_json JSON NOT NULL,
    effective_status VARCHAR(50) NOT NULL DEFAULT 'enabled',
    updated_by VARCHAR(100),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_diagnosis_rules_scope_code (scope, course_id, rule_code),
    INDEX idx_diagnosis_rules_status (effective_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS code_test_cases (
    case_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    assignment_id VARCHAR(100) NOT NULL,
    question_key VARCHAR(100) NOT NULL,
    sequence_order INT NOT NULL DEFAULT 0,
    stdin TEXT,
    expected_output TEXT,
    score DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    is_hidden TINYINT(1) NOT NULL DEFAULT 0,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ctc_assignment_question (assignment_id, question_key),
    CONSTRAINT fk_ctc_assignment
        FOREIGN KEY (assignment_id)
        REFERENCES homework_assignments(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS code_submission_runs (
    run_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    submission_id VARCHAR(100) NOT NULL,
    assignment_id VARCHAR(100) NOT NULL,
    question_key VARCHAR(100) NOT NULL,
    language VARCHAR(50),
    run_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    score DECIMAL(8,2),
    duration_ms INT NULL,
    memory_kb INT NULL,
    error_message TEXT,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_csr_submission (submission_id),
    INDEX idx_csr_assignment_question (assignment_id, question_key),
    CONSTRAINT fk_csr_submission
        FOREIGN KEY (submission_id)
        REFERENCES homework_submissions(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_csr_assignment
        FOREIGN KEY (assignment_id)
        REFERENCES homework_assignments(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS code_run_results (
    result_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id BIGINT NOT NULL,
    case_id BIGINT NULL,
    passed TINYINT(1) NOT NULL DEFAULT 0,
    actual_output TEXT,
    error_message TEXT,
    duration_ms INT NULL,
    memory_kb INT NULL,
    score DECIMAL(8,2),
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_crr_run (run_id),
    CONSTRAINT fk_crr_run
        FOREIGN KEY (run_id)
        REFERENCES code_submission_runs(run_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_crr_case
        FOREIGN KEY (case_id)
        REFERENCES code_test_cases(case_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teacher_external_metrics (
    metric_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    teacher_username VARCHAR(100) NOT NULL,
    teacher_user_id INT NULL,
    dimension_code VARCHAR(100) NOT NULL,
    metric_code VARCHAR(100) NOT NULL,
    metric_value DECIMAL(12,4),
    evidence_json JSON,
    source_type VARCHAR(50) NOT NULL DEFAULT 'manual',
    collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_tem_teacher_dimension (teacher_username, dimension_code),
    INDEX idx_tem_teacher_user_id (teacher_user_id),
    CONSTRAINT fk_tem_teacher
        FOREIGN KEY (teacher_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teacher_metric_snapshots (
    snapshot_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    teacher_username VARCHAR(100) NOT NULL,
    teacher_user_id INT NULL,
    snapshot_date DATE NOT NULL,
    dimension_scores_json JSON NOT NULL,
    evidence_summary_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tms_teacher_date (teacher_username, snapshot_date),
    INDEX idx_tms_teacher_user_id (teacher_user_id),
    CONSTRAINT fk_tms_teacher
        FOREIGN KEY (teacher_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS industry_tasks (
    task_id VARCHAR(100) PRIMARY KEY,
    teacher_username VARCHAR(100) NOT NULL,
    teacher_user_id INT NULL,
    course_id VARCHAR(100) NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress DECIMAL(6,2) NOT NULL DEFAULT 0.00,
    error_message TEXT,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_industry_tasks_teacher_status (teacher_username, status),
    INDEX idx_industry_tasks_course (course_id),
    CONSTRAINT fk_it_teacher
        FOREIGN KEY (teacher_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_it_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS industry_job_samples (
    sample_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(100) NOT NULL,
    job_title VARCHAR(500),
    company_name VARCHAR(500),
    job_url VARCHAR(1000),
    location VARCHAR(200),
    source_site VARCHAR(100),
    demand_text MEDIUMTEXT,
    evidence_json JSON,
    collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ijs_task (task_id),
    CONSTRAINT fk_ijs_task
        FOREIGN KEY (task_id)
        REFERENCES industry_tasks(task_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS industry_analysis_results (
    result_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id VARCHAR(100) NOT NULL,
    course_id VARCHAR(100) NOT NULL,
    ability_candidates_json JSON NOT NULL,
    summary TEXT,
    generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_iar_task (task_id),
    INDEX idx_iar_course (course_id),
    CONSTRAINT fk_iar_task
        FOREIGN KEY (task_id)
        REFERENCES industry_tasks(task_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_iar_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ability_achievement_snapshots (
    snapshot_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NULL,
    course_id VARCHAR(100) NOT NULL,
    ability_id BIGINT NOT NULL,
    achievement_score DECIMAL(6,2),
    support_level VARCHAR(20),
    evidence_json JSON,
    calculated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_aas_user_course_ability_time (username, course_id, ability_id, calculated_at),
    INDEX idx_aas_user_course (username, course_id),
    CONSTRAINT fk_aas_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_aas_ability
        FOREIGN KEY (ability_id)
        REFERENCES career_abilities(ability_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
