-- Shared database cutover: run once as an administrator in dev20260912.

-- Creates missing tables only; does not replace business data.

SET NAMES utf8mb4;

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


CREATE TABLE IF NOT EXISTS fivee_adk_internal_metadata (
	`key` VARCHAR(128) NOT NULL, 
	value VARCHAR(256) NOT NULL, 
	PRIMARY KEY (`key`)
)

;


CREATE TABLE IF NOT EXISTS fivee_app_states (
	app_name VARCHAR(128) NOT NULL, 
	state LONGTEXT NOT NULL, 
	update_time DATETIME(6) NOT NULL, 
	PRIMARY KEY (app_name)
)

;


CREATE TABLE IF NOT EXISTS fivee_sessions (
	app_name VARCHAR(128) NOT NULL, 
	user_id VARCHAR(128) NOT NULL, 
	id VARCHAR(128) NOT NULL, 
	state LONGTEXT NOT NULL, 
	create_time DATETIME(6) NOT NULL, 
	update_time DATETIME(6) NOT NULL, 
	PRIMARY KEY (app_name, user_id, id)
)

;


CREATE TABLE IF NOT EXISTS fivee_user_states (
	app_name VARCHAR(128) NOT NULL, 
	user_id VARCHAR(128) NOT NULL, 
	state LONGTEXT NOT NULL, 
	update_time DATETIME(6) NOT NULL, 
	PRIMARY KEY (app_name, user_id)
)

;


CREATE TABLE IF NOT EXISTS fivee_events (
	id VARCHAR(128) NOT NULL, 
	app_name VARCHAR(128) NOT NULL, 
	user_id VARCHAR(128) NOT NULL, 
	session_id VARCHAR(128) NOT NULL, 
	invocation_id VARCHAR(256) NOT NULL, 
	timestamp DATETIME(6) NOT NULL, 
	event_data LONGTEXT, 
	PRIMARY KEY (id, app_name, user_id, session_id), 
	FOREIGN KEY(app_name, user_id, session_id) REFERENCES fivee_sessions (app_name, user_id, id) ON DELETE CASCADE,
INDEX idx_events_app_user_session_ts (app_name, user_id, session_id)
)

;
