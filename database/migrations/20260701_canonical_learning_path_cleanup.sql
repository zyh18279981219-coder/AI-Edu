-- Canonical learning path cleanup for AI-Education.
-- Run on MySQL 8.0+ after backing up the target database.
-- Goal: personalized paths live only in learning_path_versions/items/status.

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;

DELIMITER $$

DROP PROCEDURE IF EXISTS drop_fk_if_exists $$
CREATE PROCEDURE drop_fk_if_exists(IN p_table VARCHAR(128), IN p_fk VARCHAR(128))
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.TABLE_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND CONSTRAINT_NAME = p_fk
          AND CONSTRAINT_TYPE = 'FOREIGN KEY'
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', p_table, '` DROP FOREIGN KEY `', p_fk, '`');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END $$

DROP PROCEDURE IF EXISTS drop_index_if_exists $$
CREATE PROCEDURE drop_index_if_exists(IN p_table VARCHAR(128), IN p_index VARCHAR(128))
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND INDEX_NAME = p_index
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', p_table, '` DROP INDEX `', p_index, '`');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END $$

DROP PROCEDURE IF EXISTS drop_column_if_exists $$
CREATE PROCEDURE drop_column_if_exists(IN p_table VARCHAR(128), IN p_column VARCHAR(128))
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = p_table
          AND COLUMN_NAME = p_column
    ) THEN
        SET @sql = CONCAT('ALTER TABLE `', p_table, '` DROP COLUMN `', p_column, '`');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END $$

DELIMITER ;

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
    CONSTRAINT fk_lpv_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_lpv_course FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
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
    CONSTRAINT fk_lpi_path FOREIGN KEY (path_id) REFERENCES learning_path_versions(path_id) ON DELETE CASCADE,
    CONSTRAINT fk_lpi_course_node FOREIGN KEY (course_id, node_id) REFERENCES course_nodes(course_id, node_id) ON DELETE CASCADE,
    CONSTRAINT fk_lpi_resource FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET @has_legacy_status := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'learning_path_node_status'
      AND COLUMN_NAME = 'plan_id'
);
SET @has_canonical_status := (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'learning_path_node_status'
      AND COLUMN_NAME = 'path_id'
);
SET @status_sql := IF(
    @has_legacy_status > 0 AND @has_canonical_status = 0,
    'RENAME TABLE learning_path_node_status TO learning_path_node_status_legacy_plan',
    'SELECT 1'
);
PREPARE stmt FROM @status_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CALL drop_fk_if_exists('learning_path_node_status_legacy_plan', 'fk_lpns_plan');
CALL drop_fk_if_exists('learning_path_node_status_legacy_plan', 'fk_lpns_plan_node');
CALL drop_fk_if_exists('learning_path_node_status_legacy_plan', 'fk_lpns_user');

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
    CONSTRAINT fk_lpns_path FOREIGN KEY (path_id) REFERENCES learning_path_versions(path_id) ON DELETE CASCADE,
    CONSTRAINT fk_lpns_item FOREIGN KEY (item_id) REFERENCES learning_path_items(item_id) ON DELETE SET NULL,
    CONSTRAINT fk_lpns_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP TEMPORARY TABLE IF EXISTS tmp_legacy_paths;
CREATE TEMPORARY TABLE tmp_legacy_paths AS
SELECT
    base.old_plan_id,
    base.username,
    base.user_id,
    base.course_id,
    base.diagnosis_report_id,
    base.title,
    base.summary,
    base.status,
    base.generated_reason,
    base.payload_json,
    base.created_at,
    base.updated_at,
    COALESCE(existing.max_version, 0)
      + ROW_NUMBER() OVER (PARTITION BY base.username, base.course_id ORDER BY base.updated_at, base.old_plan_id) AS assigned_version_no
FROM (
    SELECT
        lp.plan_id AS old_plan_id,
        lp.username,
        lp.user_id,
        COALESCE(
            NULLIF(JSON_UNQUOTE(JSON_EXTRACT(lpn.content, '$.course_id')), ''),
            NULLIF(lp.course_id, ''),
            'course_big_data'
        ) AS course_id,
        COALESCE(
            NULLIF(JSON_UNQUOTE(JSON_EXTRACT(lpn.content, '$.basis_report_id')), ''),
            NULLIF(JSON_UNQUOTE(JSON_EXTRACT(lpn.content, '$.diagnosis.report_id')), '')
        ) AS diagnosis_report_id,
        COALESCE(lp.title, lp.filename, '个性化学习路径') AS title,
        NULLIF(JSON_UNQUOTE(JSON_EXTRACT(lpn.content, '$.summary')), '') AS summary,
        COALESCE(NULLIF(lp.status, ''), 'archived') AS status,
        COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(lpn.content, '$.trigger_type')), ''), 'legacy_migration') AS generated_reason,
        lpn.content AS payload_json,
        COALESCE(lp.created_at, NOW()) AS created_at,
        COALESCE(lp.updated_at, lp.created_at, NOW()) AS updated_at
    FROM learning_plans lp
    JOIN learning_plan_nodes lpn
      ON lpn.plan_id = lp.plan_id
     AND lpn.node_key = 'payload'
    WHERE lp.category = 'path'
      AND NOT EXISTS (
          SELECT 1
          FROM learning_path_versions existing_path
          WHERE existing_path.username = lp.username
            AND CAST(existing_path.source_payload_json AS CHAR) = CAST(lpn.content AS CHAR)
      )
) base
LEFT JOIN (
    SELECT username, course_id, MAX(version_no) AS max_version
    FROM learning_path_versions
    GROUP BY username, course_id
) existing
  ON existing.username = base.username
 AND existing.course_id = base.course_id;

INSERT INTO learning_path_versions
    (username, user_id, course_id, diagnosis_report_id, version_no,
     title, summary, status, generated_reason, source_payload_json,
     created_at, updated_at)
SELECT
    username, user_id, course_id, diagnosis_report_id, assigned_version_no,
    title, summary, status, generated_reason, payload_json,
    created_at, updated_at
FROM tmp_legacy_paths;

DROP TEMPORARY TABLE IF EXISTS tmp_legacy_path_map;
CREATE TEMPORARY TABLE tmp_legacy_path_map AS
SELECT t.old_plan_id, t.payload_json, v.path_id, v.username, v.user_id, v.course_id
FROM tmp_legacy_paths t
JOIN learning_path_versions v
  ON v.username = t.username
 AND v.course_id = t.course_id
 AND v.version_no = t.assigned_version_no;

INSERT IGNORE INTO learning_path_items
    (path_id, course_id, node_id, sequence_order, item_type,
     recommendation_reason, target_mastery, status, payload_json, created_at, updated_at)
SELECT
    m.path_id,
    COALESCE(NULLIF(j.course_id, ''), m.course_id),
    CASE WHEN cn.node_id IS NULL THEN NULL ELSE j.node_id END,
    j.ord,
    COALESCE(NULLIF(j.item_type, ''), 'knowledge_point'),
    COALESCE(NULLIF(j.reason, ''), '历史路径迁移'),
    j.target_mastery,
    'pending',
    j.item_json,
    NOW(),
    NOW()
FROM tmp_legacy_path_map m
JOIN JSON_TABLE(
    m.payload_json,
    '$.formal_path_nodes[*]' COLUMNS (
        ord FOR ORDINALITY,
        node_id VARCHAR(200) PATH '$.node_id' NULL ON EMPTY,
        course_id VARCHAR(100) PATH '$.course_id' NULL ON EMPTY,
        item_type VARCHAR(50) PATH '$.item_type' NULL ON EMPTY,
        reason TEXT PATH '$.recommendation_reason' NULL ON EMPTY,
        target_mastery DECIMAL(6,2) PATH '$.target_mastery' NULL ON EMPTY,
        item_json JSON PATH '$'
    )
) j
LEFT JOIN course_nodes cn
  ON cn.course_id = COALESCE(NULLIF(j.course_id, ''), m.course_id)
 AND cn.node_id = j.node_id;

INSERT IGNORE INTO learning_path_node_status
    (path_id, item_id, username, user_id, course_id, node_id,
     item_type, source_type, status, mastery_before, payload_json, created_at, updated_at)
SELECT
    i.path_id,
    i.item_id,
    m.username,
    m.user_id,
    i.course_id,
    i.node_id,
    COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(i.payload_json, '$.item_type')), ''), 'course_knowledge_point'),
    COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(i.payload_json, '$.source_type')), ''), 'published_course_graph'),
    'pending',
    CAST(JSON_UNQUOTE(JSON_EXTRACT(i.payload_json, '$.mastery_score')) AS DECIMAL(6,2)),
    i.payload_json,
    NOW(),
    NOW()
FROM learning_path_items i
JOIN tmp_legacy_path_map m ON m.path_id = i.path_id
WHERE i.node_id IS NOT NULL;

SET @has_legacy_status_table := (
    SELECT COUNT(*)
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'learning_path_node_status_legacy_plan'
);
SET @legacy_status_sql := IF(
    @has_legacy_status_table > 0,
    'INSERT INTO learning_path_node_status
        (path_id, item_id, username, user_id, course_id, node_id,
         item_type, source_type, status, mastery_before, mastery_after,
         started_at, completed_at, payload_json, created_at, updated_at)
     SELECT
        m.path_id, i.item_id, s.username, s.user_id, s.course_id, s.node_id,
        s.item_type, s.source_type, s.status, s.mastery_before, s.mastery_after,
        s.started_at, s.completed_at, s.payload_json, s.created_at, s.updated_at
     FROM learning_path_node_status_legacy_plan s
     JOIN tmp_legacy_path_map m ON m.old_plan_id = s.plan_id
     LEFT JOIN learning_path_items i
       ON i.path_id = m.path_id
      AND i.node_id = s.node_id
     WHERE s.node_id IS NOT NULL
     ON DUPLICATE KEY UPDATE
        item_id = COALESCE(VALUES(item_id), learning_path_node_status.item_id),
        status = VALUES(status),
        mastery_before = COALESCE(VALUES(mastery_before), learning_path_node_status.mastery_before),
        mastery_after = COALESCE(VALUES(mastery_after), learning_path_node_status.mastery_after),
        started_at = COALESCE(VALUES(started_at), learning_path_node_status.started_at),
        completed_at = COALESCE(VALUES(completed_at), learning_path_node_status.completed_at),
        payload_json = VALUES(payload_json),
        updated_at = VALUES(updated_at)',
    'SELECT 1'
);
PREPARE stmt FROM @legacy_status_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

DELETE lpn
FROM learning_plan_nodes lpn
JOIN learning_plans lp ON lp.plan_id = lpn.plan_id
WHERE lp.category = 'path';

DELETE FROM learning_plans WHERE category = 'path';

CALL drop_fk_if_exists('learning_path_versions', 'learning_path_versions_ibfk_1');
CALL drop_fk_if_exists('learning_path_versions', 'fk_lpv_plan');
CALL drop_index_if_exists('learning_path_versions', 'idx_lpv_plan');
CALL drop_column_if_exists('learning_path_versions', 'plan_id');

CALL drop_fk_if_exists('teacher_student_links', 'fk_teacher_student_links_teacher');
CALL drop_fk_if_exists('teacher_student_links', 'fk_teacher_student_links_student');
CALL drop_fk_if_exists('user_activity_log', 'fk_user_activity_log_user');

CALL drop_index_if_exists('users', 'idx_login_id');
CALL drop_index_if_exists('homework_grading_events', 'idx_homework_grading_events_assignment');

DROP TABLE IF EXISTS diagnosis_reports_course_mismatch_backup;
DROP TABLE IF EXISTS homework_grading_events_orphan_backup;
DROP TABLE IF EXISTS homework_submissions_orphan_backup;
DROP TABLE IF EXISTS quiz_attempts_node_mismatch_backup;
DROP TABLE IF EXISTS twin_profile_nodes_node_mismatch_backup;
DROP TABLE IF EXISTS learning_path_node_status_legacy_plan;

ALTER TABLE learning_plans
    MODIFY COLUMN category ENUM('global', 'user') DEFAULT 'user',
    MODIFY COLUMN plan_type VARCHAR(50) NOT NULL DEFAULT 'schedule';

DROP PROCEDURE IF EXISTS drop_fk_if_exists;
DROP PROCEDURE IF EXISTS drop_index_if_exists;
DROP PROCEDURE IF EXISTS drop_column_if_exists;
