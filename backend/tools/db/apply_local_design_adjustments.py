from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path
from typing import Any, Dict

import pymysql


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def connect(args: argparse.Namespace):
    password = args.password
    if password is None:
        password = getpass.getpass(f"Password for local MySQL user {args.user}: ")
    return pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=password,
        database=args.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def exists(cur, sql: str, params: tuple[Any, ...]) -> bool:
    cur.execute(sql, params)
    return cur.fetchone() is not None


def table_exists(cur, table: str) -> bool:
    return exists(
        cur,
        "SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s",
        (table,),
    )


def column_exists(cur, table: str, column: str) -> bool:
    return exists(
        cur,
        """
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s
        """,
        (table, column),
    )


def index_exists(cur, table: str, index_name: str) -> bool:
    return exists(
        cur,
        """
        SELECT 1 FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND INDEX_NAME=%s
        """,
        (table, index_name),
    )


def constraint_exists(cur, table: str, constraint_name: str) -> bool:
    return exists(
        cur,
        """
        SELECT 1 FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND CONSTRAINT_NAME=%s
        """,
        (table, constraint_name),
    )


def add_column(cur, table: str, column: str, definition: str) -> None:
    if not column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")


def add_index(cur, table: str, index_name: str, columns: str) -> None:
    if not index_exists(cur, table, index_name):
        cur.execute(f"CREATE INDEX `{index_name}` ON `{table}` ({columns})")


def add_fk(cur, table: str, constraint_name: str, ddl: str) -> None:
    if not constraint_exists(cur, table, constraint_name):
        cur.execute(f"ALTER TABLE `{table}` ADD CONSTRAINT `{constraint_name}` {ddl}")


def fk_exists(cur, table: str, constraint_name: str) -> bool:
    return constraint_exists(cur, table, constraint_name)


def backup_table_if_missing(cur, backup_table: str, select_sql: str) -> None:
    if not table_exists(cur, backup_table):
        cur.execute(f"CREATE TABLE `{backup_table}` AS {select_sql}")


def ensure_homework(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS homework_assignments (
            id VARCHAR(100) PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            assignment_type VARCHAR(50) NOT NULL,
            class_name VARCHAR(200),
            due_at DATETIME,
            allow_late TINYINT(1) NOT NULL DEFAULT 0,
            total_score DECIMAL(8,2) NOT NULL DEFAULT 100.00,
            rubric TEXT,
            questions_json JSON NOT NULL,
            created_by VARCHAR(100) NOT NULL,
            created_at DATETIME NOT NULL,
            status VARCHAR(50),
            updated_at DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    add_column(cur, "homework_assignments", "course_id", "VARCHAR(100) NOT NULL DEFAULT 'course_big_data'")
    add_column(cur, "homework_assignments", "node_id", "VARCHAR(255) NULL")
    add_column(cur, "homework_assignments", "node_name", "VARCHAR(500) NULL")
    add_column(cur, "homework_assignments", "node_path_json", "JSON NOT NULL")
    add_column(cur, "homework_assignments", "chapter_context", "TEXT NULL")
    add_column(cur, "homework_assignments", "objective_result_mode", "VARCHAR(50) NOT NULL DEFAULT 'immediate'")
    cur.execute("ALTER TABLE homework_assignments MODIFY COLUMN node_id VARCHAR(200) NULL")
    add_index(cur, "homework_assignments", "idx_homework_assignments_course_node", "`course_id`, `node_id`")
    add_index(cur, "homework_assignments", "idx_homework_assignments_created_by", "`created_by`")
    add_fk(
        cur,
        "homework_assignments",
        "fk_homework_assignments_course",
        "FOREIGN KEY (`course_id`) REFERENCES `courses`(`course_id`) ON DELETE RESTRICT",
    )
    add_fk(
        cur,
        "homework_assignments",
        "fk_homework_assignments_course_node",
        "FOREIGN KEY (`course_id`, `node_id`) REFERENCES `course_nodes`(`course_id`, `node_id`) ON DELETE RESTRICT",
    )

    cur.execute(
        """
        UPDATE homework_assignments
        SET node_path_json = JSON_ARRAY()
        WHERE node_path_json IS NULL
        """
    )

    if table_exists(cur, "homework_submissions"):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS homework_submissions_orphan_backup AS
            SELECT s.*
            FROM homework_submissions s
            LEFT JOIN homework_assignments a ON s.assignment_id = a.id
            WHERE a.id IS NULL
            """
        )
        cur.execute(
            """
            DELETE s
            FROM homework_submissions s
            LEFT JOIN homework_assignments a ON s.assignment_id = a.id
            WHERE a.id IS NULL
            """
        )
        add_index(cur, "homework_submissions", "idx_homework_submissions_assignment", "`assignment_id`")
        add_fk(
            cur,
            "homework_submissions",
            "fk_homework_submissions_assignment",
            "FOREIGN KEY (`assignment_id`) REFERENCES `homework_assignments`(`id`) ON DELETE CASCADE",
        )
        if column_exists(cur, "homework_submissions", "course_id"):
            cur.execute("ALTER TABLE homework_submissions MODIFY COLUMN course_id VARCHAR(100) NULL")
            cur.execute("ALTER TABLE homework_submissions MODIFY COLUMN node_id VARCHAR(200) NULL")
            add_index(cur, "homework_submissions", "idx_homework_submissions_course_node", "`course_id`, `node_id`")
            add_fk(
                cur,
                "homework_submissions",
                "fk_homework_submissions_course",
                "FOREIGN KEY (`course_id`) REFERENCES `courses`(`course_id`) ON DELETE SET NULL",
            )
            add_fk(
                cur,
                "homework_submissions",
                "fk_homework_submissions_course_node",
                "FOREIGN KEY (`course_id`, `node_id`) REFERENCES `course_nodes`(`course_id`, `node_id`) ON DELETE SET NULL",
            )
        if column_exists(cur, "homework_submissions", "student_user_id"):
            add_fk(
                cur,
                "homework_submissions",
                "fk_homework_submissions_student",
                "FOREIGN KEY (`student_user_id`) REFERENCES `users`(`user_id`) ON DELETE SET NULL",
            )
        if column_exists(cur, "homework_submissions", "grader_user_id"):
            add_fk(
                cur,
                "homework_submissions",
                "fk_homework_submissions_grader",
                "FOREIGN KEY (`grader_user_id`) REFERENCES `users`(`user_id`) ON DELETE SET NULL",
            )

    if table_exists(cur, "homework_grading_events"):
        cur.execute("ALTER TABLE homework_grading_events MODIFY COLUMN assignment_id VARCHAR(100) NOT NULL")
        cur.execute("ALTER TABLE homework_grading_events MODIFY COLUMN submission_id VARCHAR(100) NULL")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS homework_grading_events_orphan_backup AS
            SELECT e.*
            FROM homework_grading_events e
            LEFT JOIN homework_assignments a ON e.assignment_id = a.id
            WHERE a.id IS NULL
            """
        )
        add_index(cur, "homework_grading_events", "idx_homework_grading_events_assignment", "`assignment_id`")
        add_index(cur, "homework_grading_events", "idx_homework_grading_events_submission", "`submission_id`")
        add_fk(
            cur,
            "homework_grading_events",
            "fk_homework_grading_events_assignment",
            "FOREIGN KEY (`assignment_id`) REFERENCES `homework_assignments`(`id`) ON DELETE CASCADE",
        )
        add_fk(
            cur,
            "homework_grading_events",
            "fk_homework_grading_events_submission",
            "FOREIGN KEY (`submission_id`) REFERENCES `homework_submissions`(`id`) ON DELETE SET NULL",
        )
        cur.execute(
            """
            DELETE e
            FROM homework_grading_events e
            LEFT JOIN homework_assignments a ON e.assignment_id = a.id
            WHERE a.id IS NULL
            """
        )


def ensure_career_ability_mapping(cur) -> None:
    cur.execute(
        """
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
            CONSTRAINT fk_career_positions_course
                FOREIGN KEY (course_id)
                REFERENCES courses(course_id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
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
            CONSTRAINT fk_cam_course_node
                FOREIGN KEY (course_id, node_id)
                REFERENCES course_nodes(course_id, node_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_cam_ability
                FOREIGN KEY (ability_id)
                REFERENCES career_abilities(ability_id)
                ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def ensure_teaching_tables(cur) -> None:
    cur.execute(
        """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute(
        """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def ensure_event_time_columns(cur) -> None:
    for table in (
        "homework_grading_events",
        "teaching_interaction_events",
        "teacher_intervention_events",
        "teaching_research_events",
    ):
        if not table_exists(cur, table):
            continue
        add_column(cur, table, "occurred_at", "DATETIME NULL")
        cur.execute(
            f"""
            UPDATE `{table}`
            SET occurred_at = STR_TO_DATE(REPLACE(SUBSTRING(created_at, 1, 19), 'T', ' '), '%Y-%m-%d %H:%i:%s')
            WHERE occurred_at IS NULL AND created_at IS NOT NULL AND created_at <> ''
            """
        )


def ensure_course_node_relations(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS course_node_relations (
            course_id VARCHAR(100) NOT NULL,
            node_id VARCHAR(200) NOT NULL,
            related_node_id VARCHAR(200) NOT NULL,
            relation_type VARCHAR(64) NOT NULL,
            payload_json JSON NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (course_id, node_id, related_node_id, relation_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )
    cur.execute("ALTER TABLE course_node_relations MODIFY COLUMN course_id VARCHAR(100) NOT NULL")
    cur.execute("ALTER TABLE course_node_relations MODIFY COLUMN node_id VARCHAR(200) NOT NULL")
    cur.execute("ALTER TABLE course_node_relations MODIFY COLUMN related_node_id VARCHAR(200) NOT NULL")
    add_index(cur, "course_node_relations", "idx_cnr_related", "`course_id`, `related_node_id`")
    add_fk(
        cur,
        "course_node_relations",
        "fk_cnr_source_node",
        "FOREIGN KEY (`course_id`, `node_id`) REFERENCES `course_nodes`(`course_id`, `node_id`) ON DELETE CASCADE",
    )
    add_fk(
        cur,
        "course_node_relations",
        "fk_cnr_related_node",
        "FOREIGN KEY (`course_id`, `related_node_id`) REFERENCES `course_nodes`(`course_id`, `node_id`) ON DELETE CASCADE",
    )


def repair_course_references(cur) -> None:
    if table_exists(cur, "diagnosis_reports"):
        backup_table_if_missing(
            cur,
            "diagnosis_reports_course_mismatch_backup",
            """
            SELECT d.*
            FROM diagnosis_reports d
            LEFT JOIN courses c ON d.course_id = c.course_id
            WHERE c.course_id IS NULL
            """,
        )
        cur.execute(
            """
            UPDATE diagnosis_reports d
            LEFT JOIN courses c ON d.course_id = c.course_id
            SET d.course_id = 'course_big_data'
            WHERE c.course_id IS NULL
              AND EXISTS (SELECT 1 FROM courses ok WHERE ok.course_id = 'course_big_data')
            """
        )
        cur.execute("ALTER TABLE diagnosis_reports MODIFY COLUMN course_id VARCHAR(100) NOT NULL")
        add_fk(
            cur,
            "diagnosis_reports",
            "fk_diagnosis_reports_user",
            "FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE",
        )
        add_fk(
            cur,
            "diagnosis_reports",
            "fk_diagnosis_reports_course",
            "FOREIGN KEY (`course_id`) REFERENCES `courses`(`course_id`) ON DELETE CASCADE",
        )

    if table_exists(cur, "quiz_attempts"):
        backup_table_if_missing(
            cur,
            "quiz_attempts_node_mismatch_backup",
            """
            SELECT q.*
            FROM quiz_attempts q
            LEFT JOIN course_nodes n ON q.course_id = n.course_id AND q.node_id = n.node_id
            WHERE q.course_id IS NOT NULL
              AND q.node_id IS NOT NULL
              AND n.node_detail_id IS NULL
            """,
        )
        cur.execute(
            """
            UPDATE quiz_attempts q
            JOIN course_nodes n
              ON n.course_id = q.course_id
             AND n.node_name = q.node_id
            LEFT JOIN course_nodes exact
              ON exact.course_id = q.course_id
             AND exact.node_id = q.node_id
            SET q.node_id = n.node_id
            WHERE exact.node_detail_id IS NULL
              AND n.node_detail_id = (
                SELECT n2.node_detail_id
                FROM course_nodes n2
                WHERE n2.course_id = q.course_id
                  AND n2.node_name = q.node_id
                ORDER BY
                  NOT EXISTS (
                    SELECT 1
                    FROM course_nodes child
                    WHERE child.course_id = n2.course_id
                      AND child.parent_node_id = n2.node_id
                  ) DESC,
                  n2.depth DESC,
                  LENGTH(n2.node_id) DESC,
                  n2.node_detail_id DESC
                LIMIT 1
              )
            """
        )
        cur.execute(
            """
            UPDATE quiz_attempts q
            LEFT JOIN course_nodes n ON q.course_id = n.course_id AND q.node_id = n.node_id
            SET q.node_id = NULL
            WHERE q.course_id IS NOT NULL
              AND q.node_id IS NOT NULL
              AND n.node_detail_id IS NULL
            """
        )
        add_index(cur, "quiz_attempts", "idx_quiz_attempts_course_node", "`course_id`, `node_id`")
        add_fk(
            cur,
            "quiz_attempts",
            "fk_quiz_attempts_user",
            "FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE SET NULL",
        )
        add_fk(
            cur,
            "quiz_attempts",
            "fk_quiz_attempts_course",
            "FOREIGN KEY (`course_id`) REFERENCES `courses`(`course_id`) ON DELETE SET NULL",
        )
        add_fk(
            cur,
            "quiz_attempts",
            "fk_quiz_attempts_course_node",
            "FOREIGN KEY (`course_id`, `node_id`) REFERENCES `course_nodes`(`course_id`, `node_id`) ON DELETE SET NULL",
        )

    if table_exists(cur, "resources"):
        add_index(cur, "resources", "idx_resources_course_node", "`course_id`, `node_id`")
        add_fk(
            cur,
            "resources",
            "fk_resources_course_node",
            "FOREIGN KEY (`course_id`, `node_id`) REFERENCES `course_nodes`(`course_id`, `node_id`) ON DELETE CASCADE",
        )


def ensure_user_relationships(cur) -> None:
    if table_exists(cur, "teacher_student_links"):
        cur.execute(
            """
            UPDATE teacher_student_links l
            LEFT JOIN users teacher
              ON teacher.username = l.teacher_username AND teacher.user_type = 'teacher'
            LEFT JOIN users student
              ON student.username = l.student_username AND student.user_type = 'student'
            SET l.teacher_user_id = COALESCE(l.teacher_user_id, teacher.user_id),
                l.student_user_id = COALESCE(l.student_user_id, student.user_id)
            """
        )
        add_fk(
            cur,
            "teacher_student_links",
            "fk_teacher_student_links_teacher",
            "FOREIGN KEY (`teacher_user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE",
        )
        add_fk(
            cur,
            "teacher_student_links",
            "fk_teacher_student_links_student",
            "FOREIGN KEY (`student_user_id`) REFERENCES `users`(`user_id`) ON DELETE CASCADE",
        )

    if table_exists(cur, "user_activity_log"):
        add_column(cur, "user_activity_log", "user_id", "INT NULL AFTER username")
        cur.execute(
            """
            UPDATE user_activity_log a
            JOIN users u ON u.username = a.username
            SET a.user_id = u.user_id
            WHERE a.user_id IS NULL
            """
        )
        add_index(cur, "user_activity_log", "idx_user_activity_user_id", "`user_id`")
        add_fk(
            cur,
            "user_activity_log",
            "fk_user_activity_log_user",
            "FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE SET NULL",
        )

    if table_exists(cur, "llm_logs"):
        add_fk(
            cur,
            "llm_logs",
            "fk_llm_logs_user",
            "FOREIGN KEY (`user_id`) REFERENCES `users`(`user_id`) ON DELETE SET NULL",
        )


def ensure_twin_profile_node_course(cur) -> None:
    if not table_exists(cur, "twin_profile_nodes"):
        return
    add_column(cur, "twin_profile_nodes", "course_id", "VARCHAR(100) NOT NULL DEFAULT 'course_big_data' AFTER user_id")
    cur.execute(
        """
        UPDATE twin_profile_nodes
        SET course_id = 'course_big_data'
        WHERE course_id IS NULL OR course_id = ''
        """
    )
    backup_table_if_missing(
        cur,
        "twin_profile_nodes_node_mismatch_backup",
        """
        SELECT t.*
        FROM twin_profile_nodes t
        LEFT JOIN course_nodes n ON t.course_id = n.course_id AND t.node_id = n.node_id
        WHERE n.node_detail_id IS NULL
        """,
    )
    if index_exists(cur, "twin_profile_nodes", "uk_username_node"):
        cur.execute("ALTER TABLE twin_profile_nodes DROP INDEX uk_username_node")
    cur.execute(
        """
        UPDATE twin_profile_nodes t
        JOIN course_nodes n
          ON n.course_id = t.course_id
         AND n.node_name = t.node_id
        LEFT JOIN course_nodes exact
          ON exact.course_id = t.course_id
         AND exact.node_id = t.node_id
        SET t.node_id = n.node_id
        WHERE exact.node_detail_id IS NULL
          AND n.node_detail_id = (
            SELECT n2.node_detail_id
            FROM course_nodes n2
            WHERE n2.course_id = t.course_id
              AND n2.node_name = t.node_id
            ORDER BY
              NOT EXISTS (
                SELECT 1
                FROM course_nodes child
                WHERE child.course_id = n2.course_id
                  AND child.parent_node_id = n2.node_id
              ) DESC,
              n2.depth DESC,
              LENGTH(n2.node_id) DESC,
              n2.node_detail_id DESC
            LIMIT 1
          )
        """
    )
    cur.execute(
        """
        DELETE t
        FROM twin_profile_nodes t
        LEFT JOIN course_nodes n ON t.course_id = n.course_id AND t.node_id = n.node_id
        WHERE n.node_detail_id IS NULL
        """
    )
    cur.execute(
        """
        DELETE older
        FROM twin_profile_nodes older
        JOIN twin_profile_nodes newer
          ON newer.username = older.username
         AND newer.course_id = older.course_id
         AND newer.node_id = older.node_id
         AND newer.node_detail_id > older.node_detail_id
        """
    )
    add_index(cur, "twin_profile_nodes", "idx_tpn_course_node", "`course_id`, `node_id`")
    if not index_exists(cur, "twin_profile_nodes", "uk_tpn_user_course_node"):
        cur.execute(
            """
            CREATE UNIQUE INDEX uk_tpn_user_course_node
            ON twin_profile_nodes (`username`, `course_id`, `node_id`)
            """
        )
    add_fk(
        cur,
        "twin_profile_nodes",
        "fk_tpn_course_node",
        "FOREIGN KEY (`course_id`, `node_id`) REFERENCES `course_nodes`(`course_id`, `node_id`) ON DELETE CASCADE",
    )


def ensure_user_interaction_table(cur) -> None:
    needs_rebuild = False
    if table_exists(cur, "user_interaction"):
        needs_rebuild = not column_exists(cur, "user_interaction", "interaction_id")
    if needs_rebuild:
        backup_table_if_missing(cur, "user_interaction_legacy_backup", "SELECT * FROM user_interaction")
        cur.execute("DROP TABLE user_interaction")
    cur.execute(
        """
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
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
    )


def main() -> None:
    env_local = load_env(PROJECT_ROOT / ".env.local.mysql")
    parser = argparse.ArgumentParser(description="Apply local-only MySQL design adjustments.")
    parser.add_argument("--host", default=os.getenv("LOCAL_DB_HOST") or env_local.get("DB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("LOCAL_DB_PORT") or env_local.get("DB_PORT", "3306")))
    parser.add_argument("--user", default=os.getenv("LOCAL_DB_USER") or env_local.get("DB_USER", "root"))
    parser.add_argument("--password", default=os.getenv("LOCAL_DB_PASSWORD") or env_local.get("DB_PASSWORD"))
    parser.add_argument("--database", default=os.getenv("LOCAL_DB_NAME") or env_local.get("DB_NAME", "ai_education_design"))
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to adjust a non-local database.")

    conn = connect(args)
    try:
        with conn.cursor() as cur:
            ensure_homework(cur)
            ensure_career_ability_mapping(cur)
            ensure_teaching_tables(cur)
            ensure_event_time_columns(cur)
            ensure_course_node_relations(cur)
            repair_course_references(cur)
            ensure_user_relationships(cur)
            ensure_twin_profile_node_course(cur)
            ensure_user_interaction_table(cur)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Applied local design adjustments to {args.host}:{args.port}/{args.database}")


if __name__ == "__main__":
    main()
