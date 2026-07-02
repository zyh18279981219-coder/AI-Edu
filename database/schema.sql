-- AI-Education local MySQL schema
-- Source of truth for the zyh branch local development database.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- =========================================================
-- 1. Users, identity, session and runtime state
-- =========================================================

CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    login_id VARCHAR(50) UNIQUE NOT NULL,
    user_type ENUM('student', 'teacher', 'admin') NOT NULL,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255),
    display_name VARCHAR(200),
    teacher_id INT,
    email VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_type_username (user_type, username),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_username (username),
    CONSTRAINT fk_users_teacher
        FOREIGN KEY (teacher_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id INT PRIMARY KEY,
    avatar_url VARCHAR(500),
    phone VARCHAR(20),
    address VARCHAR(500),
    bio TEXT,
    preferences JSON,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_profiles_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teacher_student_links (
    teacher_username VARCHAR(100) NOT NULL,
    student_username VARCHAR(100) NOT NULL,
    teacher_user_id INT,
    student_user_id INT,
    course_id VARCHAR(100) NULL,
    class_name VARCHAR(255) NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (teacher_username, student_username),
    INDEX idx_tsl_teacher_user_id (teacher_user_id),
    INDEX idx_tsl_student_user_id (student_user_id),
    INDEX idx_tsl_course (course_id, class_name),
    CONSTRAINT fk_tsl_teacher
        FOREIGN KEY (teacher_user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_tsl_student
        FOREIGN KEY (student_user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id INT,
    username VARCHAR(100) NOT NULL,
    user_type ENUM('student', 'teacher', 'admin') NOT NULL,
    created_at DATETIME,
    last_accessed DATETIME,
    current_pdf_path TEXT,
    current_node VARCHAR(500),
    payload_json JSON NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_sessions_user_id (user_id),
    INDEX idx_sessions_username (username),
    INDEX idx_sessions_updated_at (updated_at),
    CONSTRAINT fk_sessions_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_states (
    username VARCHAR(150) PRIMARY KEY,
    user_id INT NULL,
    payload_json JSON NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_user_states_user_id (user_id),
    CONSTRAINT fk_user_states_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS llm_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME,
    username VARCHAR(100),
    user_id INT,
    module VARCHAR(100),
    model VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'success',
    duration_ms INT NULL,
    prompt_tokens INT NULL,
    completion_tokens INT NULL,
    total_tokens INT NULL,
    cost_estimate DECIMAL(12,6) NULL,
    request_id VARCHAR(128) NULL,
    error_message TEXT NULL,
    payload_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_llm_logs_username (username),
    INDEX idx_llm_logs_user_id (user_id),
    INDEX idx_llm_logs_module (module),
    INDEX idx_llm_logs_created_at (created_at),
    CONSTRAINT fk_llm_logs_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_activity_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NULL,
    activity_date DATE NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    activity_details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_activity_username_date (username, activity_date),
    INDEX idx_user_activity_user_id (user_id),
    INDEX idx_user_activity_date (activity_date),
    UNIQUE KEY uk_user_activity_day_type (username, activity_date, activity_type),
    CONSTRAINT fk_user_activity_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 2. Course digital twin and resources
-- =========================================================

CREATE TABLE IF NOT EXISTS courses (
    course_id VARCHAR(100) PRIMARY KEY,
    course_name VARCHAR(500) NOT NULL,
    source_path VARCHAR(1000),
    description TEXT,
    difficulty_level ENUM('beginner', 'intermediate', 'advanced'),
    estimated_hours DECIMAL(6,2),
    lifecycle_status VARCHAR(50) NOT NULL DEFAULT 'published',
    published_at DATETIME NULL,
    published_by VARCHAR(100) NULL,
    payload_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_courses_course_name (course_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS course_enrollments (
    enrollment_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    student_username VARCHAR(100) NOT NULL,
    student_user_id INT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    enrolled_at DATETIME NULL,
    payload_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_course_enrollments_course_student (course_id, student_username),
    INDEX idx_course_enrollments_student (student_username, status),
    INDEX idx_course_enrollments_user_id (student_user_id),
    CONSTRAINT fk_course_enrollments_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_course_enrollments_student
        FOREIGN KEY (student_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teacher_course_assignments (
    assignment_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    teacher_username VARCHAR(100) NOT NULL,
    teacher_user_id INT NULL,
    class_name VARCHAR(255) NOT NULL DEFAULT '',
    role VARCHAR(50) NOT NULL DEFAULT 'teacher',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    payload_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tca_course_teacher_class (course_id, teacher_username, class_name),
    INDEX idx_tca_teacher (teacher_username, status),
    INDEX idx_tca_user_id (teacher_user_id),
    CONSTRAINT fk_tca_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_tca_teacher
        FOREIGN KEY (teacher_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS course_metadata (
    metadata_id INT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    additional_data JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_course_metadata_course (course_id),
    CONSTRAINT fk_course_metadata_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS course_nodes (
    node_detail_id INT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    node_name VARCHAR(500) NOT NULL,
    normalized_name VARCHAR(500) NULL,
    node_type VARCHAR(50) NULL,
    node_path_json JSON NOT NULL,
    depth INT NOT NULL DEFAULT 0,
    parent_node_id VARCHAR(200),
    sort_order INT NOT NULL DEFAULT 0,
    publish_status VARCHAR(50) NOT NULL DEFAULT 'published',
    payload_json JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_course_nodes_course_node (course_id, node_id),
    INDEX idx_course_nodes_course_depth (course_id, depth),
    INDEX idx_course_nodes_parent (course_id, parent_node_id),
    INDEX idx_course_nodes_name (node_name),
    CONSTRAINT fk_course_nodes_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS resources (
    resource_id INT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    resource_path VARCHAR(1000) NOT NULL,
    resource_path_hash CHAR(64) GENERATED ALWAYS AS (SHA2(resource_path, 256)) STORED,
    resource_type VARCHAR(200),
    title VARCHAR(500),
    payload_json JSON NOT NULL,
    resource_source VARCHAR(50) NOT NULL DEFAULT 'local',
    quality_status VARCHAR(50) NOT NULL DEFAULT 'unchecked',
    review_status VARCHAR(50) NOT NULL DEFAULT 'enabled',
    is_enabled TINYINT(1) NOT NULL DEFAULT 1,
    is_deleted TINYINT(1) NOT NULL DEFAULT 0,
    deleted_at DATETIME NULL,
    deleted_by VARCHAR(100) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_resources_course_node_path (course_id, node_id, resource_path_hash),
    INDEX idx_resources_course_node (course_id, node_id),
    INDEX idx_resources_deleted (is_deleted),
    CONSTRAINT fk_resources_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE IF NOT EXISTS resource_learning_events (
    event_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NULL,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    resource_id INT NULL,
    resource_path VARCHAR(1000),
    event_type VARCHAR(50) NOT NULL,
    duration_seconds INT DEFAULT 0,
    progress_percent DECIMAL(6,2),
    is_completed TINYINT(1) NOT NULL DEFAULT 0,
    occurred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_rle_user_course_node (username, course_id, node_id),
    INDEX idx_rle_resource (resource_id),
    INDEX idx_rle_occurred_at (occurred_at),
    CONSTRAINT fk_rle_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_rle_course_node
        FOREIGN KEY (course_id, node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rle_resource
        FOREIGN KEY (resource_id)
        REFERENCES resources(resource_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS course_node_relations (
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    related_node_id VARCHAR(200) NOT NULL,
    relation_type VARCHAR(64) NOT NULL,
    payload_json JSON NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (course_id, node_id, related_node_id, relation_type),
    INDEX idx_cnr_related (course_id, related_node_id),
    CONSTRAINT fk_cnr_source_node
        FOREIGN KEY (course_id, node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cnr_related_node
        FOREIGN KEY (course_id, related_node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE
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

-- =========================================================
-- 3. Learning plans and personalized path
-- =========================================================

CREATE TABLE IF NOT EXISTS learning_plans (
    plan_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NULL,
    course_id VARCHAR(100) NULL,
    filename VARCHAR(255) NOT NULL,
    plan_path VARCHAR(500),
    category ENUM('global', 'user') DEFAULT 'user',
    plan_type VARCHAR(50) NOT NULL DEFAULT 'schedule',
    title VARCHAR(500),
    description TEXT,
    status ENUM('draft', 'active', 'completed', 'archived') DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_learning_plans_user_course_filename (username, course_id, filename),
    INDEX idx_learning_plans_user_id (user_id),
    INDEX idx_learning_plans_course_type (course_id, plan_type, status),
    INDEX idx_learning_plans_category (category),
    INDEX idx_learning_plans_status (status),
    CONSTRAINT fk_learning_plans_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS learning_plan_nodes (
    node_id INT PRIMARY KEY AUTO_INCREMENT,
    plan_id INT NOT NULL,
    node_key VARCHAR(100) NOT NULL,
    node_name VARCHAR(500),
    node_type VARCHAR(50),
    sequence_order INT DEFAULT 0,
    parent_node_id INT,
    content JSON,
    metadata JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_learning_plan_nodes_plan_key (plan_id, node_key),
    INDEX idx_learning_plan_nodes_plan_id (plan_id),
    INDEX idx_learning_plan_nodes_parent (parent_node_id),
    CONSTRAINT fk_learning_plan_nodes_plan
        FOREIGN KEY (plan_id)
        REFERENCES learning_plans(plan_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_learning_plan_nodes_parent
        FOREIGN KEY (parent_node_id)
        REFERENCES learning_plan_nodes(node_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS learning_path_versions (
    path_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NULL,
    course_id VARCHAR(100) NOT NULL,
    diagnosis_report_id VARCHAR(100) NULL,
    version_no INT NOT NULL DEFAULT 1,
    title VARCHAR(500),
    summary TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    generated_reason TEXT,
    source_payload_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_lpv_user_course_version (username, course_id, version_no),
    INDEX idx_lpv_user_course_status (username, course_id, status),
    INDEX idx_lpv_user_id (user_id),
    CONSTRAINT fk_lpv_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_lpv_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS learning_path_items (
    item_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    path_id BIGINT NOT NULL,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NULL,
    resource_id INT NULL,
    sequence_order INT NOT NULL DEFAULT 0,
    item_type VARCHAR(50) NOT NULL DEFAULT 'knowledge_point',
    recommendation_reason TEXT,
    target_mastery DECIMAL(6,2) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    payload_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_lpi_path_order (path_id, sequence_order),
    INDEX idx_lpi_course_node (course_id, node_id),
    INDEX idx_lpi_resource (resource_id),
    CONSTRAINT fk_lpi_path
        FOREIGN KEY (path_id)
        REFERENCES learning_path_versions(path_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_lpi_course_node
        FOREIGN KEY (course_id, node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_lpi_resource
        FOREIGN KEY (resource_id)
        REFERENCES resources(resource_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS learning_path_node_status (
    status_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    path_id BIGINT NOT NULL,
    item_id BIGINT NULL,
    username VARCHAR(100) NOT NULL,
    user_id INT NULL,
    course_id VARCHAR(100),
    node_id VARCHAR(200),
    item_type VARCHAR(50) NOT NULL DEFAULT 'course_knowledge_point',
    source_type VARCHAR(50) NOT NULL DEFAULT 'published_course_graph',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    mastery_before DECIMAL(6,2),
    mastery_after DECIMAL(6,2),
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_lpns_path_item (path_id, item_type, source_type, node_id),
    INDEX idx_lpns_username_status (username, status),
    INDEX idx_lpns_course_node (course_id, node_id),
    INDEX idx_lpns_item (item_id),
    CONSTRAINT fk_lpns_path
        FOREIGN KEY (path_id)
        REFERENCES learning_path_versions(path_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_lpns_item
        FOREIGN KEY (item_id)
        REFERENCES learning_path_items(item_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_lpns_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 4. Student digital twin, quiz evidence and diagnosis
-- =========================================================

CREATE TABLE IF NOT EXISTS twin_profiles (
    profile_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NOT NULL,
    course_id VARCHAR(100) NOT NULL DEFAULT 'course_big_data',
    last_updated DATETIME,
    overall_mastery DECIMAL(5,2) DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_twin_profiles_user_course (username, course_id),
    INDEX idx_twin_profiles_user_id (user_id),
    INDEX idx_twin_profiles_course (course_id),
    CONSTRAINT fk_twin_profiles_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS twin_profile_nodes (
    node_detail_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NOT NULL,
    course_id VARCHAR(100) NOT NULL DEFAULT 'course_big_data',
    node_id VARCHAR(200) NOT NULL,
    node_path_json JSON NOT NULL,
    quiz_score DECIMAL(6,2),
    progress DECIMAL(6,2) DEFAULT 0.00,
    study_duration_minutes DECIMAL(10,2) DEFAULT 0.00,
    llm_interaction_count INT DEFAULT 0,
    mastery_score DECIMAL(6,2) DEFAULT 0.00,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_tpn_user_course_node (username, course_id, node_id),
    INDEX idx_tpn_user_id (user_id),
    INDEX idx_tpn_course_node (course_id, node_id),
    CONSTRAINT fk_tpn_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS twin_history (
    history_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL,
    user_id INT NULL,
    course_id VARCHAR(100) NOT NULL DEFAULT 'course_big_data',
    snapshot_date DATE NOT NULL,
    overall_mastery DECIMAL(5,2) DEFAULT 0.00,
    payload_json JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_twin_history_user_course_date (username, course_id, snapshot_date),
    INDEX idx_twin_history_user_id (user_id),
    INDEX idx_twin_history_course (course_id),
    CONSTRAINT fk_twin_history_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
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

CREATE TABLE IF NOT EXISTS quiz_attempts (
    attempt_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    username VARCHAR(100),
    course_id VARCHAR(100),
    node_id VARCHAR(200),
    score DECIMAL(6,2),
    total DECIMAL(6,2),
    passed TINYINT(1) DEFAULT 0,
    payload_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_quiz_attempts_user_id (user_id),
    INDEX idx_quiz_attempts_username (username),
    INDEX idx_quiz_attempts_course_node (course_id, node_id),
    INDEX idx_quiz_attempts_created_at (created_at),
    CONSTRAINT fk_quiz_attempts_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS diagnosis_reports (
    report_id VARCHAR(100) PRIMARY KEY,
    user_id INT NULL,
    username VARCHAR(100),
    course_id VARCHAR(100),
    report_date DATE NOT NULL,
    persona_summary TEXT,
    evidence_level VARCHAR(50),
    confidence DECIMAL(5,2),
    payload_json JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_diagnosis_user_course (user_id, course_id),
    INDEX idx_diagnosis_username (username),
    INDEX idx_diagnosis_report_date (report_date),
    CONSTRAINT fk_diagnosis_reports_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
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

CREATE TABLE IF NOT EXISTS diagnosis_corrections (
    correction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    report_id VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200),
    teacher_username VARCHAR(100) NOT NULL,
    teacher_user_id INT NULL,
    original_reason_type VARCHAR(100),
    corrected_reason_type VARCHAR(100),
    original_evidence_level VARCHAR(50),
    corrected_evidence_level VARCHAR(50),
    correction_note TEXT,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dc_report (report_id),
    INDEX idx_dc_teacher_time (teacher_username, created_at),
    INDEX idx_dc_student_course (username, course_id),
    CONSTRAINT fk_dc_report
        FOREIGN KEY (report_id)
        REFERENCES diagnosis_reports(report_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_dc_teacher
        FOREIGN KEY (teacher_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 5. Homework and assessment evidence
-- =========================================================

CREATE TABLE IF NOT EXISTS homework_assignments (
    id VARCHAR(100) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    assignment_type VARCHAR(50) NOT NULL,
    class_name VARCHAR(200),
    course_id VARCHAR(100) NOT NULL DEFAULT 'course_big_data',
    node_id VARCHAR(255),
    node_name VARCHAR(500),
    node_path_json JSON NOT NULL,
    chapter_context TEXT,
    objective_result_mode VARCHAR(50) NOT NULL DEFAULT 'immediate',
    due_at DATETIME,
    allow_late TINYINT(1) NOT NULL DEFAULT 0,
    total_score DECIMAL(8,2) NOT NULL DEFAULT 100.00,
    rubric TEXT,
    questions_json JSON NOT NULL,
    created_by VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL,
    status VARCHAR(50),
    updated_at DATETIME,
    INDEX idx_homework_assignments_created_by (created_by),
    INDEX idx_homework_assignments_created_at (created_at),
    INDEX idx_homework_assignments_course_node (course_id, node_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS homework_submissions (
    id VARCHAR(100) PRIMARY KEY,
    assignment_id VARCHAR(100) NOT NULL,
    student_username VARCHAR(100) NOT NULL,
    answers_json JSON NOT NULL,
    submitted_at DATETIME NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'submitted',
    ai_score DECIMAL(8,2),
    ai_feedback TEXT,
    ai_rationale TEXT,
    teacher_score DECIMAL(8,2),
    teacher_comment TEXT,
    graded_at DATETIME,
    grader_username VARCHAR(100),
    updated_at DATETIME,
    INDEX idx_homework_submissions_assignment (assignment_id),
    INDEX idx_homework_submissions_student (student_username),
    CONSTRAINT fk_homework_submissions_assignment
        FOREIGN KEY (assignment_id)
        REFERENCES homework_assignments(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS homework_assignment_knowledge_points (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    assignment_id VARCHAR(100) NOT NULL,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    coverage_source VARCHAR(50) NOT NULL DEFAULT 'teacher_confirmed',
    recommended_by_system TINYINT(1) NOT NULL DEFAULT 0,
    confirmed_by_teacher TINYINT(1) NOT NULL DEFAULT 0,
    coverage_weight DECIMAL(6,4) NULL,
    confidence DECIMAL(5,2),
    reason TEXT,
    teacher_username VARCHAR(100),
    confirmed_at DATETIME NULL,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_hakp_assignment_node (assignment_id, course_id, node_id),
    INDEX idx_hakp_course_node (course_id, node_id),
    INDEX idx_hakp_assignment (assignment_id),
    CONSTRAINT fk_hakp_assignment
        FOREIGN KEY (assignment_id)
        REFERENCES homework_assignments(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_hakp_course_node
        FOREIGN KEY (course_id, node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE
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

CREATE TABLE IF NOT EXISTS homework_grading_events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    assignment_id VARCHAR(255) NOT NULL,
    submission_id VARCHAR(255),
    teacher_username VARCHAR(100) NOT NULL,
    student_username VARCHAR(100),
    event_type VARCHAR(100) NOT NULL,
    grading_minutes DOUBLE,
    is_ai_recommended TINYINT DEFAULT 0,
    is_ai_executed TINYINT DEFAULT 0,
    payload_json LONGTEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    occurred_at DATETIME NULL,
    INDEX idx_hge_teacher_time (teacher_username, created_at),
    INDEX idx_hge_assignment (assignment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 6. Teaching interaction, research and teacher twin evidence
-- =========================================================

CREATE TABLE IF NOT EXISTS teaching_announcements (
    id VARCHAR(64) PRIMARY KEY,
    teacher_username VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    class_name VARCHAR(255),
    course_id VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'published',
    published_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_ta_teacher_time (teacher_username, published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teaching_discussion_topics (
    id VARCHAR(64) PRIMARY KEY,
    teacher_username VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    class_name VARCHAR(255),
    course_id VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    student_question_count INT NOT NULL DEFAULT 0,
    teacher_reply_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_tdt_teacher_time (teacher_username, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teaching_discussion_posts (
    id VARCHAR(64) PRIMARY KEY,
    topic_id VARCHAR(64) NOT NULL,
    author_username VARCHAR(100) NOT NULL,
    author_role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    replied_to_post_id VARCHAR(64),
    response_minutes DOUBLE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    INDEX idx_tdp_topic_time (topic_id, created_at),
    CONSTRAINT fk_tdp_topic
        FOREIGN KEY (topic_id)
        REFERENCES teaching_discussion_topics(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teaching_research_records (
    id VARCHAR(64) PRIMARY KEY,
    teacher_username VARCHAR(100) NOT NULL,
    activity_type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    resource_link VARCHAR(1000),
    class_name VARCHAR(255),
    course_id VARCHAR(100),
    happened_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    INDEX idx_trr_teacher_time (teacher_username, happened_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teaching_interaction_events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    teacher_username VARCHAR(100) NOT NULL,
    course_id VARCHAR(100),
    class_name VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    target_id VARCHAR(255),
    student_username VARCHAR(100),
    response_minutes DOUBLE,
    payload_json LONGTEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    occurred_at DATETIME NULL,
    INDEX idx_tie_teacher_time (teacher_username, created_at),
    INDEX idx_tie_type_time (event_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teaching_research_events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    teacher_username VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    payload_json LONGTEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    occurred_at DATETIME NULL,
    INDEX idx_tre_teacher_time (teacher_username, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS teacher_intervention_events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    package_id VARCHAR(255),
    teacher_username VARCHAR(100) NOT NULL,
    student_username VARCHAR(100),
    event_type VARCHAR(100) NOT NULL,
    weak_node_count INT DEFAULT 0,
    completion_rate DOUBLE DEFAULT 0,
    payload_json LONGTEXT NOT NULL,
    created_at VARCHAR(40) NOT NULL,
    occurred_at DATETIME NULL,
    INDEX idx_tievt_teacher_time (teacher_username, created_at)
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

CREATE TABLE IF NOT EXISTS intervention_packages (
    package_id VARCHAR(100) PRIMARY KEY,
    teacher_username VARCHAR(100) NOT NULL,
    teacher_user_id INT NULL,
    student_username VARCHAR(100) NOT NULL,
    student_user_id INT NULL,
    course_id VARCHAR(100),
    diagnosis_report_id VARCHAR(100),
    package_title VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    risk_level VARCHAR(50),
    review_note TEXT,
    pushed_at DATETIME NULL,
    completed_at DATETIME NULL,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ip_teacher_status (teacher_username, status),
    INDEX idx_ip_student_status (student_username, status),
    INDEX idx_ip_course (course_id),
    CONSTRAINT fk_ip_teacher
        FOREIGN KEY (teacher_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_ip_student
        FOREIGN KEY (student_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_ip_diagnosis
        FOREIGN KEY (diagnosis_report_id)
        REFERENCES diagnosis_reports(report_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS intervention_package_items (
    item_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    package_id VARCHAR(100) NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    course_id VARCHAR(100),
    node_id VARCHAR(200),
    resource_id INT NULL,
    homework_assignment_id VARCHAR(100),
    quiz_payload_json JSON,
    reminder_text TEXT,
    sequence_order INT NOT NULL DEFAULT 0,
    required TINYINT(1) NOT NULL DEFAULT 1,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ipi_package_order (package_id, sequence_order),
    INDEX idx_ipi_course_node (course_id, node_id),
    CONSTRAINT fk_ipi_package
        FOREIGN KEY (package_id)
        REFERENCES intervention_packages(package_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_ipi_resource
        FOREIGN KEY (resource_id)
        REFERENCES resources(resource_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_ipi_homework
        FOREIGN KEY (homework_assignment_id)
        REFERENCES homework_assignments(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS intervention_package_student_records (
    record_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    package_id VARCHAR(100) NOT NULL,
    item_id BIGINT NULL,
    student_username VARCHAR(100) NOT NULL,
    student_user_id INT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    score DECIMAL(8,2),
    feedback TEXT,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    payload_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_ipsr_student_status (student_username, status),
    INDEX idx_ipsr_package (package_id),
    CONSTRAINT fk_ipsr_package
        FOREIGN KEY (package_id)
        REFERENCES intervention_packages(package_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_ipsr_item
        FOREIGN KEY (item_id)
        REFERENCES intervention_package_items(item_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_ipsr_student
        FOREIGN KEY (student_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 7. Industry intelligence and ability mapping
-- =========================================================

CREATE TABLE IF NOT EXISTS career_positions (
    position_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    position_name VARCHAR(200) NOT NULL,
    normalized_name VARCHAR(200) NOT NULL,
    source_keyword VARCHAR(200),
    position_type VARCHAR(50) DEFAULT 'related',
    target_rank INT DEFAULT 0,
    created_by INT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_career_positions_course_name (course_id, normalized_name),
    INDEX idx_career_positions_course (course_id),
    INDEX idx_career_positions_created_by (created_by),
    CONSTRAINT fk_career_positions_course
        FOREIGN KEY (course_id)
        REFERENCES courses(course_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_career_positions_created_by
        FOREIGN KEY (created_by)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS career_abilities (
    ability_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    position_id BIGINT NOT NULL,
    ability_name VARCHAR(300) NOT NULL,
    ability_category VARCHAR(100),
    demand_level DECIMAL(5,2),
    support_level VARCHAR(20),
    evidence_json JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_career_abilities_position_name (position_id, ability_name),
    CONSTRAINT fk_career_abilities_position
        FOREIGN KEY (position_id)
        REFERENCES career_positions(position_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS course_ability_mappings (
    mapping_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    course_id VARCHAR(100) NOT NULL,
    node_id VARCHAR(200) NOT NULL,
    ability_id BIGINT NOT NULL,
    support_weight DECIMAL(6,4) NOT NULL DEFAULT 0.0000,
    support_level VARCHAR(20),
    match_reason TEXT,
    evidence_json JSON,
    review_status VARCHAR(50) NOT NULL DEFAULT 'draft',
    reviewed_by INT,
    reviewed_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_course_ability_mapping (course_id, node_id, ability_id),
    INDEX idx_cam_ability (ability_id),
    CONSTRAINT fk_cam_course_node
        FOREIGN KEY (course_id, node_id)
        REFERENCES course_nodes(course_id, node_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cam_ability
        FOREIGN KEY (ability_id)
        REFERENCES career_abilities(ability_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_cam_reviewed_by
        FOREIGN KEY (reviewed_by)
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

-- =========================================================
-- 8. 5E interaction records
-- =========================================================

CREATE TABLE IF NOT EXISTS events (
    id VARCHAR(128) PRIMARY KEY,
    app_name VARCHAR(128) NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    session_id VARCHAR(128) NOT NULL,
    invocation_id VARCHAR(256) NOT NULL,
    timestamp DATETIME NOT NULL,
    event_data TEXT,
    INDEX idx_events_app_name (app_name),
    INDEX idx_events_user_id (user_id),
    INDEX idx_events_session (session_id),
    INDEX idx_events_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_interaction (
    interaction_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_identifier VARCHAR(100) NOT NULL,
    student_user_id INT NULL,
    student_username VARCHAR(100) NULL,
    course_id VARCHAR(100) NULL,
    session_id VARCHAR(255) NULL,
    stage VARCHAR(64) NOT NULL,
    question_type VARCHAR(100) NULL,
    question_count INT NOT NULL DEFAULT 0,
    error TEXT NULL,
    payload_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ui_user_time (user_identifier, created_at),
    INDEX idx_ui_student_user_id (student_user_id),
    INDEX idx_ui_course_stage (course_id, stage),
    CONSTRAINT fk_user_interaction_student
        FOREIGN KEY (student_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fivee_effectiveness_records (
    record_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_identifier VARCHAR(100) NOT NULL,
    student_user_id INT NULL,
    student_username VARCHAR(100),
    course_id VARCHAR(100),
    node_id VARCHAR(200),
    session_id VARCHAR(255),
    stage VARCHAR(64) NOT NULL,
    interaction_count INT NOT NULL DEFAULT 0,
    valid_interaction_count INT NOT NULL DEFAULT 0,
    completion_rate DECIMAL(6,2),
    quiz_score_before DECIMAL(6,2),
    quiz_score_after DECIMAL(6,2),
    path_continue_rate DECIMAL(6,2),
    effectiveness_score DECIMAL(6,2),
    payload_json JSON,
    calculated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fer_student_course (student_username, course_id),
    INDEX idx_fer_stage_time (stage, calculated_at),
    CONSTRAINT fk_fer_student
        FOREIGN KEY (student_user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
