-- Add multi-course access tables used by the learning center and teacher course scope.
-- Safe to run repeatedly on existing MySQL databases.

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

CALL add_column_if_missing('teacher_student_links', 'course_id', 'VARCHAR(100) NULL');
CALL add_column_if_missing('teacher_student_links', 'class_name', 'VARCHAR(255) NULL');
CALL add_index_if_missing('teacher_student_links', 'idx_tsl_course', '`course_id`, `class_name`');

INSERT INTO course_enrollments
    (course_id, student_username, student_user_id, status, enrolled_at, payload_json, created_at, updated_at)
SELECT c.course_id, u.username, u.user_id, 'active', COALESCE(c.published_at, NOW()),
       JSON_OBJECT('seed', '20260702_course_access_tables'), NOW(), NOW()
FROM courses c
JOIN users u ON u.user_type = 'student'
WHERE c.lifecycle_status = 'published'
ON DUPLICATE KEY UPDATE
    student_user_id = VALUES(student_user_id),
    status = IF(status = 'dropped', status, VALUES(status)),
    updated_at = VALUES(updated_at);

INSERT INTO teacher_course_assignments
    (course_id, teacher_username, teacher_user_id, class_name, role, status, payload_json, created_at, updated_at)
SELECT c.course_id, u.username, u.user_id, '', u.user_type, 'active',
       JSON_OBJECT('seed', '20260702_course_access_tables'), NOW(), NOW()
FROM courses c
JOIN users u ON u.user_type IN ('teacher', 'admin')
ON DUPLICATE KEY UPDATE
    teacher_user_id = VALUES(teacher_user_id),
    role = VALUES(role),
    status = VALUES(status),
    updated_at = VALUES(updated_at);

DROP PROCEDURE IF EXISTS add_column_if_missing;
DROP PROCEDURE IF EXISTS add_index_if_missing;
