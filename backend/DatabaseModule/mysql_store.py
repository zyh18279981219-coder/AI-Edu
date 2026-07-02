"""
MySQL数据库存储实现

实现DatabaseStore接口，提供MySQL数据库的具体访问逻辑。
支持连接池、事务管理、参数化查询等MySQL特性。
"""

from __future__ import annotations

import json
import re
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None

try:
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL, Engine
    from sqlalchemy.exc import DBAPIError, OperationalError as SQLAlchemyOperationalError
except ImportError:
    create_engine = None
    URL = None
    Engine = None
    DBAPIError = None
    SQLAlchemyOperationalError = None

from .database_store import DatabaseStore
from QuizModule.definition_utils import (
    QUIZ_DEFINITION_STATE_PREFIX,
    published_definition_index_from_state_rows,
)

logger = logging.getLogger(__name__)


class MySQLStore(DatabaseStore):
    """MySQL数据库存储实现
    
    实现DatabaseStore接口的所有方法，提供MySQL数据库的具体访问逻辑。
    支持连接池、事务管理、SSL连接等MySQL特性。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "ai_education",
        charset: str = "utf8mb4",
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        pool_timeout: int = 30,
        pool_warmup: bool = True,
        **kwargs
    ):
        """初始化MySQL存储
        
        Args:
            host: MySQL服务器地址
            port: MySQL端口
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
            **kwargs: 其他连接参数
        """
        if pymysql is None:
            raise ImportError("pymysql is required for MySQL support. Install with: pip install pymysql")
        if create_engine is None or URL is None:
            raise ImportError("SQLAlchemy is required for MySQL connection pooling. Install with: pip install sqlalchemy pymysql")
        
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': charset,
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': False,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30,
            **kwargs
        }
        self.pool_config = {
            'pool_size': int(pool_size),
            'max_overflow': int(max_overflow),
            'pool_recycle': int(pool_recycle),
            'pool_pre_ping': bool(pool_pre_ping),
            'pool_timeout': int(pool_timeout),
            'pool_warmup': bool(pool_warmup),
        }
        self._engine = self._create_engine()
        self._lock = threading.RLock()
        self._initialize()
        if self.pool_config["pool_warmup"] and self.pool_config["pool_size"] > 0:
            self._warm_pool()

    def _create_engine(self) -> "Engine":
        """创建全局复用的SQLAlchemy连接池。"""
        url = URL.create(
            "mysql+pymysql",
            username=self.config["user"],
            password=self.config["password"],
            host=self.config["host"],
            port=self.config["port"],
            database=self.config["database"],
            query={"charset": self.config["charset"]},
        )
        connect_args = {
            "autocommit": False,
            "connect_timeout": self.config["connect_timeout"],
            "read_timeout": self.config["read_timeout"],
            "write_timeout": self.config["write_timeout"],
        }
        for key, value in self.config.items():
            if key not in {
                "host",
                "port",
                "user",
                "password",
                "database",
                "charset",
                "cursorclass",
                "autocommit",
                "connect_timeout",
                "read_timeout",
                "write_timeout",
            } and value is not None:
                connect_args[key] = value

        logger.info(
            "Creating MySQL connection pool host=%s port=%s database=%s pool_size=%s max_overflow=%s",
            self.config["host"],
            self.config["port"],
            self.config["database"],
            self.pool_config["pool_size"],
            self.pool_config["max_overflow"],
        )
        return create_engine(
            url,
            connect_args=connect_args,
            pool_size=self.pool_config["pool_size"],
            max_overflow=self.pool_config["max_overflow"],
            pool_recycle=self.pool_config["pool_recycle"],
            pool_pre_ping=self.pool_config["pool_pre_ping"],
            pool_timeout=self.pool_config["pool_timeout"],
            future=True,
        )

    @contextmanager
    def connection(self):
        """从SQLAlchemy连接池获取MySQL连接（带重试机制）。"""
        max_retries = 3
        retry_delay = 1

        conn = None
        for attempt in range(max_retries):
            try:
                conn = self._engine.raw_connection()
                self._use_dict_cursor(conn)
                break
            except self._retryable_errors():
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                raise

        if conn is None:
            raise RuntimeError("failed to acquire MySQL connection")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _retryable_errors(self) -> tuple[type[BaseException], ...]:
        errors: list[type[BaseException]] = [pymysql.err.OperationalError, TimeoutError]
        if DBAPIError is not None:
            errors.append(DBAPIError)
        if SQLAlchemyOperationalError is not None:
            errors.append(SQLAlchemyOperationalError)
        return tuple(errors)

    def _use_dict_cursor(self, conn: Any) -> None:
        """让交给业务代码的连接默认返回dict行，同时不影响SQLAlchemy内部探测。"""
        dbapi_conn = getattr(conn, "driver_connection", None) or getattr(conn, "connection", None) or conn
        if hasattr(dbapi_conn, "cursorclass"):
            dbapi_conn.cursorclass = pymysql.cursors.DictCursor

    def _warm_pool(self) -> None:
        """启动时预热连接池，提前建立pool_size个连接。"""
        connections = []
        try:
            for _ in range(self.pool_config["pool_size"]):
                connections.append(self._engine.raw_connection())
        finally:
            for conn in connections:
                conn.close()

    def close(self) -> None:
        """关闭连接池中的所有连接。"""
        self._engine.dispose()

    def _initialize(self):
        """初始化数据库表结构"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                # 读取并执行完整的MySQL schema
                schema_path = Path(__file__).parent / "mysql_schema_clean.sql"
                
                if schema_path.exists():
                    with schema_path.open('r', encoding='utf-8') as f:
                        schema_sql = f.read()
                    
                    # Strip line comments before splitting so a section header does not hide
                    # the CREATE TABLE statement that follows it in the same chunk.
                    executable_sql = "\n".join(
                        line for line in schema_sql.splitlines()
                        if not line.strip().startswith("--")
                    )
                    statements = [stmt.strip() for stmt in executable_sql.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        if statement and not statement.startswith('--'):
                            try:
                                cursor.execute(statement)
                            except Exception as e:
                                # 忽略已存在的表/视图错误，但记录其他错误
                                if 'already exists' not in str(e).lower():
                                    logger.warning("Schema initialization warning: %s", e)
                else:
                    # 如果schema文件不存在，创建基本表结构
                    self._create_basic_tables(cursor)
                self._apply_schema_fixes(cursor)

    def _apply_schema_fixes(self, cursor):
        """对历史遗留表结构做幂等修复。"""
        self._ensure_user_activity_log_table(cursor)
        self._ensure_course_lifecycle_columns(cursor)
        self._ensure_career_mapping_columns(cursor)
        self._ensure_multi_course_learning_columns(cursor)
        twin_profile_columns = self._table_columns(cursor, "twin_profiles")
        if "overall_mastery" in twin_profile_columns:
            cursor.execute("SHOW COLUMNS FROM twin_profiles LIKE 'overall_mastery'")
            row = cursor.fetchone()
            if row:
                column_type = str(row["Type"] if isinstance(row, dict) else row[1]).lower()
                if column_type != "decimal(5,2)":
                    logger.warning(
                        "Schema fix: alter twin_profiles.overall_mastery from %s to DECIMAL(5,2)",
                        column_type,
                    )
                    cursor.execute(
                        "ALTER TABLE twin_profiles MODIFY COLUMN overall_mastery DECIMAL(5,2) DEFAULT 0.00"
                    )

    def _ensure_user_activity_log_table(self, cursor):
        """确保学习连续天数和通知模块需要的活动日志表存在。"""
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_activity_log (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(100) NOT NULL,
                user_id INT NULL,
                activity_date DATE NOT NULL,
                activity_type VARCHAR(50) NOT NULL,
                activity_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_username_date (username, activity_date),
                INDEX idx_user_activity_user_id (user_id),
                INDEX idx_activity_date (activity_date),
                UNIQUE KEY unique_user_date_type (username, activity_date, activity_type),
                CONSTRAINT fk_user_activity_log_user
                    FOREIGN KEY (user_id)
                    REFERENCES users(user_id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        if "user_id" not in self._table_columns(cursor, "user_activity_log"):
            cursor.execute("ALTER TABLE user_activity_log ADD COLUMN user_id INT NULL AFTER username")
            cursor.execute("CREATE INDEX idx_user_activity_user_id ON user_activity_log (user_id)")

    def _ensure_course_lifecycle_columns(self, cursor):
        """确保课程建设、资源审核和发布流程需要的状态字段存在。"""
        course_columns = self._table_columns(cursor, "courses")
        if course_columns:
            if "lifecycle_status" not in course_columns:
                cursor.execute("ALTER TABLE courses ADD COLUMN lifecycle_status VARCHAR(50) NOT NULL DEFAULT 'published' AFTER estimated_hours")
            if "published_at" not in course_columns:
                cursor.execute("ALTER TABLE courses ADD COLUMN published_at DATETIME NULL AFTER lifecycle_status")
            if "published_by" not in course_columns:
                cursor.execute("ALTER TABLE courses ADD COLUMN published_by VARCHAR(100) NULL AFTER published_at")
            if "payload_json" not in course_columns:
                cursor.execute("ALTER TABLE courses ADD COLUMN payload_json JSON NULL AFTER published_by")

        resource_columns = self._table_columns(cursor, "resources")
        if resource_columns:
            if "resource_source" not in resource_columns:
                cursor.execute("ALTER TABLE resources ADD COLUMN resource_source VARCHAR(50) NOT NULL DEFAULT 'local' AFTER payload_json")
            if "quality_status" not in resource_columns:
                cursor.execute("ALTER TABLE resources ADD COLUMN quality_status VARCHAR(50) NOT NULL DEFAULT 'unchecked' AFTER resource_source")
            if "review_status" not in resource_columns:
                cursor.execute("ALTER TABLE resources ADD COLUMN review_status VARCHAR(50) NOT NULL DEFAULT 'enabled' AFTER quality_status")
            if "is_enabled" not in resource_columns:
                cursor.execute("ALTER TABLE resources ADD COLUMN is_enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER review_status")

    def _ensure_career_mapping_columns(self, cursor):
        """确保课程目标岗位和能力映射表支持课程级配置。"""
        position_columns = self._table_columns(cursor, "career_positions")
        if position_columns:
            if "course_id" not in position_columns:
                cursor.execute("ALTER TABLE career_positions ADD COLUMN course_id VARCHAR(100) NULL AFTER position_id")
                cursor.execute("CREATE INDEX idx_career_positions_course ON career_positions (course_id)")
            if "target_rank" not in position_columns:
                cursor.execute("ALTER TABLE career_positions ADD COLUMN target_rank INT DEFAULT 0 AFTER position_type")
            try:
                cursor.execute("SHOW INDEX FROM career_positions WHERE Key_name = 'uk_career_positions_normalized'")
                if cursor.fetchall():
                    cursor.execute("ALTER TABLE career_positions DROP INDEX uk_career_positions_normalized")
            except Exception as exc:
                logger.debug("Skip dropping legacy career position index: %s", exc)
            try:
                cursor.execute("SHOW INDEX FROM career_positions WHERE Key_name = 'uk_career_positions_course_name'")
                if not cursor.fetchall():
                    cursor.execute("CREATE UNIQUE INDEX uk_career_positions_course_name ON career_positions (course_id, normalized_name)")
            except Exception as exc:
                logger.debug("Skip creating career position course index: %s", exc)

    def _ensure_multi_course_learning_columns(self, cursor):
        """确保多课程学习计划模型需要的字段存在。"""
        learning_plan_columns = self._table_columns(cursor, "learning_plans")
        if learning_plan_columns:
            if "course_id" not in learning_plan_columns:
                cursor.execute("ALTER TABLE learning_plans ADD COLUMN course_id VARCHAR(100) NULL AFTER user_id")
                cursor.execute("UPDATE learning_plans SET course_id = 'course_big_data' WHERE course_id IS NULL")
            if "plan_type" not in learning_plan_columns:
                cursor.execute("ALTER TABLE learning_plans ADD COLUMN plan_type VARCHAR(50) NOT NULL DEFAULT 'schedule' AFTER category")
                cursor.execute(
                    """
                    UPDATE learning_plans
                    SET plan_type = CASE
                        WHEN category = 'path' THEN 'path_legacy'
                        WHEN category = 'global' THEN 'global'
                        ELSE 'schedule'
                    END
                    """
                )
        twin_profile_columns = self._table_columns(cursor, "twin_profiles")
        if twin_profile_columns and "course_id" not in twin_profile_columns:
            cursor.execute("ALTER TABLE twin_profiles ADD COLUMN course_id VARCHAR(100) NOT NULL DEFAULT 'course_big_data' AFTER user_id")
        twin_history_columns = self._table_columns(cursor, "twin_history")
        if twin_history_columns and "course_id" not in twin_history_columns:
            cursor.execute("ALTER TABLE twin_history ADD COLUMN course_id VARCHAR(100) NOT NULL DEFAULT 'course_big_data' AFTER user_id")

    def _create_basic_tables(self, cursor):
        """创建基本表结构（fallback方案）"""
        # 用户表
        cursor.execute("""
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
                FOREIGN KEY (teacher_id) REFERENCES users(user_id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 用户扩展信息表
        cursor.execute("""
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
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 教师学生关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teacher_student_links (
                teacher_username VARCHAR(100) NOT NULL,
                student_username VARCHAR(100) NOT NULL,
                teacher_user_id INT,
                student_user_id INT,
                course_id VARCHAR(100) NULL,
                class_name VARCHAR(255) NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (teacher_username, student_username),
                INDEX idx_teacher_user_id (teacher_user_id),
                INDEX idx_student_user_id (student_user_id),
                INDEX idx_tsl_course (course_id, class_name),
                FOREIGN KEY (teacher_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (student_user_id) REFERENCES users(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 数字孪生画像主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS twin_profiles (
                profile_id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(100) NOT NULL UNIQUE,
                user_id INT NOT NULL,
                last_updated DATETIME,
                overall_mastery DECIMAL(5,2) DEFAULT 0.00,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                INDEX idx_username (username),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 会话表
        cursor.execute("""
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
                INDEX idx_user_id (user_id),
                INDEX idx_username (username),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 学习计划主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_plans (
                plan_id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(100) NOT NULL,
                user_id INT NOT NULL,
                course_id VARCHAR(100),
                filename VARCHAR(255) NOT NULL,
                plan_path VARCHAR(500),
                category ENUM('global', 'user') DEFAULT 'user',
                plan_type VARCHAR(50) NOT NULL DEFAULT 'schedule',
                title VARCHAR(500),
                description TEXT,
                status ENUM('draft', 'active', 'completed', 'archived') DEFAULT 'draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_username_course_filename (username, course_id, filename),
                INDEX idx_user_id (user_id),
                INDEX idx_course_type (course_id, plan_type, status),
                INDEX idx_category (category),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 学习计划节点表
        cursor.execute("""
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
                UNIQUE KEY uk_plan_node (plan_id, node_key),
                INDEX idx_plan_id (plan_id),
                INDEX idx_parent_node (parent_node_id),
                FOREIGN KEY (plan_id) REFERENCES learning_plans(plan_id) ON DELETE CASCADE,
                FOREIGN KEY (parent_node_id) REFERENCES learning_plan_nodes(node_id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # 课程主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id VARCHAR(100) PRIMARY KEY,
                course_name VARCHAR(500) NOT NULL,
                source_path VARCHAR(1000),
                description TEXT,
                difficulty_level ENUM('beginner', 'intermediate', 'advanced'),
                estimated_hours DECIMAL(6,2),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_course_name (course_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS course_nodes (
                node_detail_id INT PRIMARY KEY AUTO_INCREMENT,
                course_id VARCHAR(100) NOT NULL,
                node_id VARCHAR(200) NOT NULL,
                node_name VARCHAR(500) NOT NULL,
                node_path_json JSON NOT NULL,
                depth INT NOT NULL DEFAULT 0,
                parent_node_id VARCHAR(200),
                payload_json JSON,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_course_nodes_course_node (course_id, node_id),
                INDEX idx_course_nodes_course_depth (course_id, depth),
                INDEX idx_course_nodes_parent (course_id, parent_node_id),
                INDEX idx_course_nodes_name (node_name),
                FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 资源表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                resource_id INT PRIMARY KEY AUTO_INCREMENT,
                course_id VARCHAR(100) NOT NULL,
                node_id VARCHAR(200) NOT NULL,
                resource_path VARCHAR(1000) NOT NULL,
                resource_type VARCHAR(50),
                title VARCHAR(500),
                payload_json JSON NOT NULL,
                is_deleted TINYINT(1) DEFAULT 0,
                deleted_at DATETIME NULL,
                deleted_by VARCHAR(100) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_course_node_resource (course_id, node_id, resource_path),
                INDEX idx_course_id (course_id),
                INDEX idx_is_deleted (is_deleted),
                FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
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
                FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
                FOREIGN KEY (student_user_id) REFERENCES users(user_id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
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
                FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_user_id) REFERENCES users(user_id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
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
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
                FOREIGN KEY (course_id) REFERENCES courses(course_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
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
                FOREIGN KEY (path_id) REFERENCES learning_path_versions(path_id) ON DELETE CASCADE,
                FOREIGN KEY (course_id, node_id) REFERENCES course_nodes(course_id, node_id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES resources(resource_id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        cursor.execute("""
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
                FOREIGN KEY (path_id) REFERENCES learning_path_versions(path_id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES learning_path_items(item_id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

    def _now(self) -> str:
        """获取当前时间戳"""
        return datetime.now().isoformat()

    def _to_str(self, value: Any) -> Optional[str]:
        """将任意时间值转换为ISO字符串（兼容MySQL datetime对象和字符串）"""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)

    def _json(self, payload: Any) -> str:
        """序列化为JSON字符串"""
        return json.dumps(payload, ensure_ascii=False)

    def _table_columns(self, cursor: "pymysql.cursors.Cursor", table_name: str) -> set[str]:
        """读取表字段集合。表不存在时返回空集合。"""
        try:
            cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
            rows = cursor.fetchall() or []
        except Exception:
            return set()
        return {
            str(row["Field"] if isinstance(row, dict) else row[0]).strip()
            for row in rows
            if row
        }

    def _resolve_user_identity_row(
        self,
        cursor: "pymysql.cursors.Cursor",
        identifier: Any,
        user_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """在当前游标上下文中解析用户身份，兼容 username/login_id/user_id。"""
        identity = str(identifier or "").strip()
        if not identity:
            return None

        if user_type:
            cursor.execute(
                """
                SELECT user_id, username, login_id, user_type
                FROM users
                WHERE user_type = %s
                  AND (username = %s OR login_id = %s OR CAST(user_id AS CHAR) = %s)
                ORDER BY CASE
                    WHEN username = %s THEN 0
                    WHEN login_id = %s THEN 1
                    WHEN CAST(user_id AS CHAR) = %s THEN 2
                    ELSE 3
                END
                LIMIT 1
                """,
                (user_type, identity, identity, identity, identity, identity, identity),
            )
        else:
            cursor.execute(
                """
                SELECT user_id, username, login_id, user_type
                FROM users
                WHERE username = %s OR login_id = %s OR CAST(user_id AS CHAR) = %s
                ORDER BY CASE
                    WHEN username = %s THEN 0
                    WHEN login_id = %s THEN 1
                    WHEN CAST(user_id AS CHAR) = %s THEN 2
                    ELSE 3
                END,
                CASE user_type
                    WHEN 'student' THEN 0
                    WHEN 'teacher' THEN 1
                    ELSE 2
                END
                LIMIT 1
                """,
                (identity, identity, identity, identity, identity, identity),
            )

        row = cursor.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row
        return {
            "user_id": row[0],
            "username": row[1],
            "login_id": row[2],
            "user_type": row[3],
        }

    def _ensure_llm_logs_table(self, cursor: "pymysql.cursors.Cursor") -> str:
        """确保 llm_logs 表及关键字段存在，并返回排序列名。"""
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                username VARCHAR(100),
                user_id INT,
                module VARCHAR(100),
                model VARCHAR(100),
                payload_json JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_username (username),
                INDEX idx_module (module)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        columns = self._table_columns(cursor, "llm_logs")
        if "user_id" not in columns:
            cursor.execute("ALTER TABLE llm_logs ADD COLUMN user_id INT NULL AFTER username")
        if "module" not in columns:
            cursor.execute("ALTER TABLE llm_logs ADD COLUMN module VARCHAR(100) NULL AFTER user_id")
        if "model" not in columns:
            cursor.execute("ALTER TABLE llm_logs ADD COLUMN model VARCHAR(100) NULL AFTER module")
        if "payload_json" not in columns:
            cursor.execute("ALTER TABLE llm_logs ADD COLUMN payload_json JSON NULL AFTER model")
        if "created_at" not in columns:
            cursor.execute(
                "ALTER TABLE llm_logs ADD COLUMN created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP AFTER payload_json"
            )

        refreshed = self._table_columns(cursor, "llm_logs")
        if "log_id" in refreshed:
            return "log_id"
        if "id" in refreshed:
            return "id"
        if "created_at" in refreshed:
            return "created_at"
        return "timestamp"

    # ==================== 用户管理方法 ====================
    
    def list_users(self, user_type: str) -> List[Dict[str, Any]]:
        """列出指定类型的所有用户"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT u.*, up.avatar_url, up.phone, up.address, up.bio, up.preferences, up.metadata
                    FROM users u
                    LEFT JOIN user_profiles up ON u.user_id = up.user_id
                    WHERE u.user_type = %s
                    ORDER BY u.username
                """, (user_type,))
                rows = cursor.fetchall()
        
        result = []
        for row in rows:
            user_data = {
                'user_id': row['user_id'],
                'login_id': row['login_id'],
                'user_type': row['user_type'],
                'username': row['username'],
                'password': row['password'],
                'display_name': row['display_name'],
                'teacher_id': row['teacher_id'],
                'email': row['email'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            }
            
            # 添加扩展信息
            if row['avatar_url'] or row['phone'] or row['address'] or row['bio']:
                user_data.update({
                    'avatar_url': row['avatar_url'],
                    'phone': row['phone'],
                    'address': row['address'],
                    'bio': row['bio'],
                    'preferences': json.loads(row['preferences']) if row['preferences'] else {},
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                })
            
            result.append(user_data)
        
        return result

    def get_user(self, user_type: str, username: str) -> Optional[Dict[str, Any]]:
        """根据用户类型和用户名获取用户信息"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT u.*, up.avatar_url, up.phone, up.address, up.bio, up.preferences, up.metadata
                    FROM users u
                    LEFT JOIN user_profiles up ON u.user_id = up.user_id
                    WHERE u.user_type = %s AND u.username = %s
                """, (user_type, username))
                row = cursor.fetchone()
        
        if not row:
            return None
        
        user_data = {
            'user_id': row['user_id'],
            'login_id': row['login_id'],
            'user_type': row['user_type'],
            'username': row['username'],
            'password': row['password'],
            'display_name': row['display_name'],
            'teacher_id': row['teacher_id'],
            'email': row['email'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
        }
        
        # 添加扩展信息
        if row['avatar_url'] or row['phone'] or row['address'] or row['bio']:
            user_data.update({
                'avatar_url': row['avatar_url'],
                'phone': row['phone'],
                'address': row['address'],
                'bio': row['bio'],
                'preferences': json.loads(row['preferences']) if row['preferences'] else {},
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
            })
        
        return user_data

    def get_user_by_identifier(self, user_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """根据标识符获取用户信息"""
        identifier = str(identifier or "").strip()
        if not identifier:
            return None

        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT u.*, up.avatar_url, up.phone, up.address, up.bio, up.preferences, up.metadata
                    FROM users u
                    LEFT JOIN user_profiles up ON u.user_id = up.user_id
                    WHERE u.user_type = %s
                      AND (u.username = %s OR u.login_id = %s OR CAST(u.user_id AS CHAR) = %s)
                    ORDER BY CASE
                        WHEN u.username = %s THEN 0
                        WHEN u.login_id = %s THEN 1
                        WHEN CAST(u.user_id AS CHAR) = %s THEN 2
                        ELSE 3
                    END
                    LIMIT 1
                """, (user_type, identifier, identifier, identifier, identifier, identifier, identifier))
                row = cursor.fetchone()
        
        if not row:
            logger.info("data-source: users miss user_type=%s identifier=%s", user_type, identifier)
            return None
        
        user_data = {
            'user_id': row['user_id'],
            'login_id': row['login_id'],
            'user_type': row['user_type'],
            'username': row['username'],
            'password': row['password'],
            'display_name': row['display_name'],
            'teacher_id': row['teacher_id'],
            'email': row['email'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
        }
        
        # 添加扩展信息
        if row['avatar_url'] or row['phone'] or row['address'] or row['bio']:
            user_data.update({
                'avatar_url': row['avatar_url'],
                'phone': row['phone'],
                'address': row['address'],
                'bio': row['bio'],
                'preferences': json.loads(row['preferences']) if row['preferences'] else {},
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
            })
        
        logger.info(
            "data-source: users hit user_type=%s identifier=%s user_id=%s login_id=%s",
            user_type, identifier, row['user_id'], row['login_id']
        )
        
        return user_data

    def get_user_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据user_id获取用户信息"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT u.*, up.avatar_url, up.phone, up.address, up.bio, up.preferences, up.metadata
                    FROM users u
                    LEFT JOIN user_profiles up ON u.user_id = up.user_id
                    WHERE u.user_id = %s
                    LIMIT 1
                """, (int(user_id),))
                row = cursor.fetchone()
        
        if not row:
            return None
        
        user_data = {
            'user_id': row['user_id'],
            'login_id': row['login_id'],
            'user_type': row['user_type'],
            'username': row['username'],
            'password': row['password'],
            'display_name': row['display_name'],
            'teacher_id': row['teacher_id'],
            'email': row['email'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
        }
        
        # 添加扩展信息
        if row['avatar_url'] or row['phone'] or row['address'] or row['bio']:
            user_data.update({
                'avatar_url': row['avatar_url'],
                'phone': row['phone'],
                'address': row['address'],
                'bio': row['bio'],
                'preferences': json.loads(row['preferences']) if row['preferences'] else {},
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
            })
        
        return user_data

    def resolve_user_identity(self, user_type: str, identifier: str) -> Dict[str, Any]:
        """解析用户身份信息"""
        user = self.get_user_by_identifier(user_type, identifier)
        if user:
            return {
                "username": user.get("username"),
                "user_id": user.get("user_id"),
                "login_id": user.get("login_id"),
            }
        return {
            "username": None,
            "user_id": None,
            "login_id": None,
        }

    # 注意：这里只是MySQLStore的开始部分
    # 由于内容较长，我将分多个部分来实现
    def replace_users(self, user_type: str, users: Iterable[Dict[str, Any]]) -> None:
        """替换指定类型的所有用户"""
        users = list(users)
        timestamp = self._now()
        
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                # 获取现有用户映射
                cursor.execute("""
                    SELECT username, user_id, login_id FROM users WHERE user_type = %s
                """, (user_type,))
                existing_rows = cursor.fetchall()
                existing_map = {
                    str(row["username"]): {"user_id": row["user_id"], "login_id": row["login_id"]}
                    for row in existing_rows
                }
                
                # 获取当前最大user_id
                cursor.execute("SELECT COALESCE(MAX(user_id), 0) FROM users")
                current_max = cursor.fetchone()['COALESCE(MAX(user_id), 0)'] or 0

                # 删除现有用户
                cursor.execute("DELETE FROM users WHERE user_type = %s", (user_type,))
                if user_type == "teacher":
                    cursor.execute("DELETE FROM teacher_student_links")

                # 插入新用户
                for user in users:
                    username = user.get("username")
                    if not username:
                        continue
                    
                    existing_identity = existing_map.get(str(username), {})
                    user_id = user.get("user_id") or existing_identity.get("user_id")
                    if user_id is None:
                        current_max += 1
                        user_id = current_max
                    
                    login_id = str(user.get("login_id") or existing_identity.get("login_id") or "").strip()
                    if not login_id:
                        login_id = f"{str(user_type)[:3].lower()}{int(user_id):06d}"
                    
                    display_name = user.get("stu_name") or user.get("name") or username
                    
                    # 插入主表
                    cursor.execute("""
                        INSERT INTO users
                        (user_id, login_id, user_type, username, password, display_name, teacher_id, email, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            login_id = VALUES(login_id),
                            password = VALUES(password),
                            display_name = VALUES(display_name),
                            teacher_id = VALUES(teacher_id),
                            email = VALUES(email),
                            updated_at = VALUES(updated_at)
                    """, (
                        int(user_id), login_id, user_type, username,
                        user.get("password"), display_name, None, user.get("email"),
                        timestamp, timestamp
                    ))
                    
                    # 插入扩展信息
                    self._save_user_profile(cursor, int(user_id), user)
                    
                    # 处理教师-学生关系
                    if user_type == "teacher":
                        for student_username in user.get("students", []) or []:
                            cursor.execute("""
                                SELECT user_id FROM users 
                                WHERE user_type = 'student' AND username = %s 
                                LIMIT 1
                            """, (student_username,))
                            student_row = cursor.fetchone()
                            
                            cursor.execute("""
                                INSERT INTO teacher_student_links
                                (teacher_username, student_username, teacher_user_id, student_user_id, updated_at)
                                VALUES (%s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE updated_at = VALUES(updated_at)
                            """, (
                                username, student_username, int(user_id),
                                student_row["user_id"] if student_row else None, timestamp
                            ))

    def _save_user_profile(self, cursor, user_id: int, user_data: Dict[str, Any]) -> None:
        """保存用户扩展信息到规范化表"""
        # 提取扩展字段
        avatar_url = user_data.get('avatar_url')
        phone = user_data.get('phone')
        address = user_data.get('address')
        bio = user_data.get('bio')
        preferences = user_data.get('preferences', {})
        metadata = user_data.get('metadata', {})
        
        # 如果有扩展信息才插入
        if any([avatar_url, phone, address, bio, preferences, metadata]):
            cursor.execute("""
                INSERT INTO user_profiles 
                (user_id, avatar_url, phone, address, bio, preferences, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    avatar_url = VALUES(avatar_url),
                    phone = VALUES(phone),
                    address = VALUES(address),
                    bio = VALUES(bio),
                    preferences = VALUES(preferences),
                    metadata = VALUES(metadata),
                    updated_at = VALUES(updated_at)
            """, (
                user_id, avatar_url, phone, address, bio,
                self._json(preferences), self._json(metadata),
                self._now(), self._now()
            ))

    # ==================== 教师-学生关系 ====================
    
    def list_teacher_students(self, teacher_identifier: str) -> List[Dict[str, Any]]:
        """列出教师的所有学生"""
        teacher = self.get_user_by_identifier("teacher", teacher_identifier)
        teacher_user_id = teacher.get("user_id") if teacher else None
        if teacher_user_id is None:
            logger.info("data-source: teacher_student_links miss teacher_identifier=%s", teacher_identifier)
            return []
        
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        l.teacher_username,
                        l.teacher_user_id,
                        l.student_username,
                        l.student_user_id,
                        l.updated_at,
                        u.login_id AS student_login_id,
                        u.user_type, u.username, u.display_name, u.email,
                        up.avatar_url, up.phone, up.address, up.bio, up.preferences, up.metadata
                    FROM teacher_student_links l
                    LEFT JOIN users u ON u.user_type = 'student' AND l.student_user_id = u.user_id
                    LEFT JOIN user_profiles up ON u.user_id = up.user_id
                    WHERE l.teacher_user_id = %s AND l.student_user_id IS NOT NULL
                    ORDER BY l.student_username
                """, (teacher_user_id,))
                rows = cursor.fetchall()
        
        logger.info(
            "data-source: teacher_student_links hit teacher_identifier=%s teacher_user_id=%s rows=%s",
            teacher_identifier, teacher_user_id, len(rows)
        )
        
        result = []
        for row in rows:
            student_payload = {
                'user_id': row['student_user_id'],
                'login_id': row['student_login_id'],
                'user_type': row['user_type'],
                'username': row['username'],
                'display_name': row['display_name'],
                'email': row['email'],
            }
            
            # 添加扩展信息
            if row['avatar_url'] or row['phone'] or row['address'] or row['bio']:
                student_payload.update({
                    'avatar_url': row['avatar_url'],
                    'phone': row['phone'],
                    'address': row['address'],
                    'bio': row['bio'],
                    'preferences': json.loads(row['preferences']) if row['preferences'] else {},
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                })
            
            result.append({
                "teacher_username": row["teacher_username"],
                "teacher_user_id": row["teacher_user_id"],
                "student_username": row["student_username"],
                "student_user_id": row["student_user_id"],
                "student_login_id": row["student_login_id"],
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                "student_payload": student_payload,
            })
        
        return result

    # ==================== 占位符方法 ====================
    # 注意：以下方法是占位符，需要根据MySQL规范化表结构来实现
    # 这里先提供基本的框架，具体实现将在后续任务中完成
    
    def save_twin_profile(self, username: str, payload: Dict[str, Any]) -> None:
        """保存数字孪生画像到MySQL"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                resolved = self._resolve_user_identity_row(
                    cursor,
                    payload.get("user_id") or payload.get("username") or username,
                    "student",
                )
                user_id = int(payload.get("user_id")) if payload.get("user_id") is not None else (
                    int(resolved["user_id"]) if resolved and resolved.get("user_id") is not None else None
                )
                canonical_username = str(
                    payload.get("username")
                    or (resolved.get("username") if resolved else "")
                    or username
                ).strip()
                if user_id is None:
                    raise ValueError(f"Unable to resolve student user_id for twin profile: {username}")
                
                # 保存主表
                cursor.execute("""
                    INSERT INTO twin_profiles (username, user_id, last_updated, overall_mastery, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        user_id = VALUES(user_id),
                        last_updated = VALUES(last_updated),
                        overall_mastery = VALUES(overall_mastery),
                        updated_at = VALUES(updated_at)
                """, (
                    canonical_username, user_id,
                    payload.get("last_updated"),
                    payload.get("overall_mastery", 0),
                    self._now(), self._now()
                ))
                
                # 保存节点数据到twin_profile_nodes
                nodes = payload.get("knowledge_nodes") if isinstance(payload, dict) else None
                if isinstance(nodes, list):
                    cursor.execute("DELETE FROM twin_profile_nodes WHERE username = %s", (canonical_username,))
                    now = self._now()
                    for item in nodes:
                        if not isinstance(item, dict):
                            continue
                        node_id = str(item.get("node_id") or "").strip()
                        if not node_id:
                            continue
                        node_path = item.get("node_path", [])
                        if not isinstance(node_path, list):
                            node_path = []
                        try:
                            quiz_score = float(item["quiz_score"]) if item.get("quiz_score") is not None else None
                        except (TypeError, ValueError):
                            quiz_score = None
                        course_id = str(item.get("course_id") or payload.get("course_id") or "course_big_data").strip()
                        cursor.execute("""
                            INSERT INTO twin_profile_nodes
                            (username, user_id, course_id, node_id, node_path_json, quiz_score, progress,
                             study_duration_minutes, llm_interaction_count, mastery_score, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                node_path_json = VALUES(node_path_json),
                                quiz_score = VALUES(quiz_score),
                                progress = VALUES(progress),
                                study_duration_minutes = VALUES(study_duration_minutes),
                                llm_interaction_count = VALUES(llm_interaction_count),
                                mastery_score = VALUES(mastery_score),
                                updated_at = VALUES(updated_at)
                        """, (
                            canonical_username, user_id, course_id, node_id,
                            self._json(node_path),
                            quiz_score,
                            float(item.get("progress", 0) or 0),
                            float(item.get("study_duration_minutes", 0) or 0),
                            int(item.get("llm_interaction_count", 0) or 0),
                            float(item.get("mastery_score", 0) or 0),
                            now
                        ))

    def get_twin_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """获取数字孪生画像"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT username, user_id, last_updated, overall_mastery FROM twin_profiles WHERE username = %s",
                    (username,)
                )
                row = cursor.fetchone()
        if not row:
            return None
        r = dict(row) if isinstance(row, dict) else {
            "username": row[0], "user_id": row[1],
            "last_updated": row[2], "overall_mastery": row[3]
        }
        nodes = self._load_twin_nodes_for_usernames([str(r["username"])])
        return {
            "username": r["username"],
            "user_id": r["user_id"],
            "last_updated": self._to_str(r["last_updated"]),
            "overall_mastery": float(r["overall_mastery"] or 0),
            "knowledge_nodes": nodes.get(str(r["username"]), []),
        }

    def list_twin_profiles(self) -> List[Dict[str, Any]]:
        """列出所有数字孪生画像"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT username, user_id, last_updated, overall_mastery, updated_at
                    FROM twin_profiles
                    ORDER BY username
                """)
                rows = cursor.fetchall()
        usernames = []
        profiles = []
        for row in rows:
            r = dict(row) if isinstance(row, dict) else {
                "username": row[0], "user_id": row[1],
                "last_updated": row[2], "overall_mastery": row[3], "updated_at": row[4]
            }
            usernames.append(str(r["username"]))
            profiles.append(r)
        
        nodes_map = self._load_twin_nodes_for_usernames(usernames)
        return [
            {
                "username": p["username"],
                "user_id": p["user_id"],
                "last_updated": self._to_str(p["last_updated"]),
                "overall_mastery": float(p["overall_mastery"] or 0),
                "updated_at": self._to_str(p.get("updated_at")),
                "knowledge_nodes": nodes_map.get(str(p["username"]), []),
            }
            for p in profiles
        ]

    def _load_twin_nodes_for_usernames(self, usernames: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """加载指定用户的数字孪生节点数据"""
        if not usernames:
            return {}
        placeholders = ", ".join(["%s"] * len(usernames))
        sql = f"""
            SELECT username, node_id, node_path_json, quiz_score, progress,
                   study_duration_minutes, llm_interaction_count, mastery_score
            FROM twin_profile_nodes
            WHERE username IN ({placeholders})
            ORDER BY username, node_id
        """
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(usernames))
                rows = cursor.fetchall()
        
        result: Dict[str, List[Dict[str, Any]]] = {name: [] for name in usernames}
        for row in rows:
            node_path = []
            raw_path = row.get("node_path_json") if isinstance(row, dict) else None
            if raw_path:
                try:
                    import json as _json
                    parsed = _json.loads(raw_path) if isinstance(raw_path, str) else raw_path
                    if isinstance(parsed, list):
                        node_path = parsed
                except Exception:
                    node_path = []
            
            username = row["username"] if isinstance(row, dict) else row[0]
            result.setdefault(str(username), []).append({
                "node_id": row["node_id"] if isinstance(row, dict) else row[1],
                "node_path": node_path,
                "quiz_score": float(row["quiz_score"]) if (row["quiz_score"] if isinstance(row, dict) else row[3]) is not None else None,
                "progress": float((row["progress"] if isinstance(row, dict) else row[4]) or 0),
                "study_duration_minutes": float((row["study_duration_minutes"] if isinstance(row, dict) else row[5]) or 0),
                "llm_interaction_count": int((row["llm_interaction_count"] if isinstance(row, dict) else row[6]) or 0),
                "mastery_score": float((row["mastery_score"] if isinstance(row, dict) else row[7]) or 0),
            })
        return result

    def save_twin_history(self, username: str, snapshot_date: str, payload: Dict[str, Any]) -> None:
        """保存数字孪生历史快照"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                resolved = self._resolve_user_identity_row(
                    cursor,
                    payload.get("user_id") or payload.get("username") or username,
                    "student",
                )
                user_id = int(resolved["user_id"]) if resolved and resolved.get("user_id") is not None else None
                canonical_username = str(
                    payload.get("username")
                    or (resolved.get("username") if resolved else "")
                    or username
                ).strip()
                cursor.execute("""
                    INSERT INTO twin_history
                    (username, user_id, snapshot_date, overall_mastery, payload_json, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        overall_mastery = VALUES(overall_mastery),
                        payload_json = VALUES(payload_json),
                        updated_at = VALUES(updated_at)
                """, (
                    canonical_username, user_id, snapshot_date,
                    payload.get("overall_mastery", 0),
                    self._json(payload), self._now()
                ))

    def get_twin_history(self, username: str) -> List[Dict[str, Any]]:
        """获取数字孪生历史记录"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT payload_json FROM twin_history
                    WHERE username = %s ORDER BY snapshot_date
                """, (username,))
                rows = cursor.fetchall()
        result = []
        for row in rows:
            try:
                data = row["payload_json"] if isinstance(row, dict) else row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict):
                    result.append(data)
            except Exception:
                pass
        return result

    def save_session(self, session_id: str, payload: Dict[str, Any]) -> None:
        """保存会话信息到MySQL sessions表"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO sessions (
                        session_id, user_id, username, user_type,
                        created_at, last_accessed, current_pdf_path,
                        current_node, payload_json, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        last_accessed = VALUES(last_accessed),
                        current_pdf_path = VALUES(current_pdf_path),
                        current_node = VALUES(current_node),
                        payload_json = VALUES(payload_json),
                        updated_at = VALUES(updated_at)
                """, (
                    session_id,
                    payload.get('user_id'),
                    payload.get('username', ''),
                    payload.get('user_type', 'student'),
                    payload.get('created_at'),
                    payload.get('last_accessed'),
                    payload.get('current_pdf_path'),
                    payload.get('current_node', '')[:500] if payload.get('current_node') else None,
                    self._json(payload),
                    self._now()
                ))

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从MySQL sessions表获取会话信息"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT payload_json FROM sessions WHERE session_id = %s LIMIT 1",
                    (session_id,)
                )
                row = cursor.fetchone()
        if not row:
            return None
        try:
            data = row["payload_json"] if isinstance(row, dict) else row[0]
            if isinstance(data, str):
                return json.loads(data)
            if isinstance(data, dict):
                return data
            return None
        except Exception:
            return None

    def delete_session(self, session_id: str) -> None:
        """从MySQL sessions表删除会话"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT payload_json FROM sessions ORDER BY updated_at DESC")
                rows = cursor.fetchall()
        result = []
        for row in rows:
            try:
                data = row["payload_json"] if isinstance(row, dict) else row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict):
                    result.append(data)
            except Exception:
                pass
        return result

    def list_sessions_for_user(self, user_type: str, user_identifier: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """列出用户的会话"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT payload_json FROM sessions
                    WHERE user_type = %s AND (username = %s OR user_id = %s)
                    ORDER BY updated_at DESC
                """
                params = [user_type, user_identifier, user_identifier]
                if limit:
                    sql += " LIMIT %s"
                    params.append(limit)
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        result = []
        for row in rows:
            try:
                data = row["payload_json"] if isinstance(row, dict) else row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                if isinstance(data, dict):
                    result.append(data)
            except Exception:
                pass
        return result

    def save_user_state(self, username: str, payload: Dict[str, Any]) -> None:
        """保存用户状态到MySQL user_states表"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                # 查找user_id
                cursor.execute("SELECT user_id FROM users WHERE username = %s LIMIT 1", (username,))
                row = cursor.fetchone()
                user_id = (row["user_id"] if isinstance(row, dict) else row[0]) if row else None
                
                cursor.execute("""
                    INSERT INTO user_states (username, user_id, payload_json, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        user_id = VALUES(user_id),
                        payload_json = VALUES(payload_json),
                        updated_at = VALUES(updated_at)
                """, (username, user_id, self._json(payload), self._now()))

    def get_user_state(self, username: str) -> Optional[Dict[str, Any]]:
        """从MySQL user_states表获取用户状态"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT payload_json FROM user_states WHERE username = %s LIMIT 1",
                    (username,)
                )
                row = cursor.fetchone()
        if not row:
            return None
        try:
            data = row["payload_json"] if isinstance(row, dict) else row[0]
            if isinstance(data, str):
                return json.loads(data)
            if isinstance(data, dict):
                return data
            return None
        except Exception:
            return None

    def append_llm_log(self, payload: Dict[str, Any]) -> None:
        """追加LLM日志"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                self._ensure_llm_logs_table(cursor)
                request = payload.get("request") if isinstance(payload.get("request"), dict) else {}
                resolved = None
                user_id = payload.get("user_id")
                if user_id is None and payload.get("username"):
                    resolved = self._resolve_user_identity_row(cursor, payload.get("username"))
                    user_id = resolved.get("user_id") if resolved else None
                canonical_username = payload.get("username") or (resolved.get("username") if resolved else None)
                cursor.execute("""
                    INSERT INTO llm_logs (timestamp, username, user_id, module, model, payload_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    payload.get('timestamp') or self._now(),
                    canonical_username,
                    user_id,
                    payload.get('module'),
                    payload.get('model') or request.get('model'),
                    self._json(payload),
                    self._now()
                ))

    def replace_llm_logs(self, logs: Iterable[Dict[str, Any]]) -> None:
        """替换所有LLM日志"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                self._ensure_llm_logs_table(cursor)
                cursor.execute("DELETE FROM llm_logs")
                for log in logs:
                    request = log.get("request") if isinstance(log.get("request"), dict) else {}
                    resolved = None
                    user_id = log.get("user_id")
                    if user_id is None and log.get("username"):
                        resolved = self._resolve_user_identity_row(cursor, log.get("username"))
                        user_id = resolved.get("user_id") if resolved else None
                    cursor.execute("""
                        INSERT INTO llm_logs (timestamp, username, user_id, module, model, payload_json, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        log.get('timestamp') or self._now(),
                        log.get('username') or (resolved.get("username") if resolved else None),
                        user_id,
                        log.get('module'),
                        log.get('model') or request.get('model'),
                        self._json(log),
                        self._now()
                    ))

    def list_llm_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """列出LLM日志"""
        try:
            with self._lock, self.connection() as conn:
                with conn.cursor() as cursor:
                    order_column = self._ensure_llm_logs_table(cursor)
                    sql = f"SELECT payload_json FROM llm_logs ORDER BY {order_column} DESC"
                    params: List[Any] = []
                    if limit:
                        sql += " LIMIT %s"
                        params.append(limit)
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
            result = []
            for row in rows:
                try:
                    data = row["payload_json"] if isinstance(row, dict) else row[0]
                    if isinstance(data, str):
                        data = json.loads(data)
                    if isinstance(data, dict):
                        result.append(data)
                except Exception:
                    pass
            return result
        except Exception:
            # 表不存在时返回空列表
            return []

    def list_llm_logs_for_user(self, user_identifier: str, user_type: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """列出用户的LLM日志"""
        try:
            with self._lock, self.connection() as conn:
                with conn.cursor() as cursor:
                    order_column = self._ensure_llm_logs_table(cursor)
                    resolved = self._resolve_user_identity_row(cursor, user_identifier, user_type)
                    usernames = [str(user_identifier).strip()]
                    user_id = None
                    if resolved:
                        if resolved.get("username"):
                            usernames.append(str(resolved["username"]))
                        if resolved.get("login_id"):
                            usernames.append(str(resolved["login_id"]))
                        user_id = resolved.get("user_id")
                    seen = set()
                    usernames = [name for name in usernames if name and not (name in seen or seen.add(name))]
                    username_placeholders = ", ".join(["%s"] * len(usernames))
                    sql = (
                        f"SELECT payload_json FROM llm_logs WHERE username IN ({username_placeholders})"
                    )
                    params: List[Any] = list(usernames)
                    if user_id is not None:
                        sql += " OR user_id = %s"
                        params.append(user_id)
                    sql += f" ORDER BY {order_column} DESC"
                    if limit:
                        sql += " LIMIT %s"
                        params.append(limit)
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
            result = []
            for row in rows:
                try:
                    data = row["payload_json"] if isinstance(row, dict) else row[0]
                    if isinstance(data, str):
                        data = json.loads(data)
                    if isinstance(data, dict):
                        result.append(data)
                except Exception:
                    pass
            return result
        except Exception:
            return []

    def save_learning_plan(self, username: str, filename: str, payload: Any, plan_path: Optional[str] = None, category: Optional[str] = None) -> None:
        """保存学习计划"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE username = %s LIMIT 1", (username,))
                row = cursor.fetchone()
                user_id = (row["user_id"] if isinstance(row, dict) else row[0]) if row else None
                
                # 从payload提取标题
                title = filename
                course_id = None
                if isinstance(payload, dict):
                    title = payload.get('title', filename)
                    diagnosis = payload.get("diagnosis") if isinstance(payload.get("diagnosis"), dict) else {}
                    course_id = str(payload.get("course_id") or diagnosis.get("course_id") or "").strip() or None
                normalized_category = category or "user"
                if normalized_category == "path":
                    self._save_learning_path_version_cursor(
                        cursor,
                        username=username,
                        user_id=user_id,
                        filename=filename,
                        payload=payload,
                    )
                    return
                plan_type = "global" if normalized_category == "global" else "schedule"
                
                cursor.execute("""
                    INSERT INTO learning_plans
                    (username, user_id, course_id, filename, plan_path, category, plan_type, title, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        user_id = VALUES(user_id),
                        course_id = VALUES(course_id),
                        plan_path = VALUES(plan_path),
                        category = VALUES(category),
                        plan_type = VALUES(plan_type),
                        title = VALUES(title),
                        status = VALUES(status),
                        updated_at = VALUES(updated_at)
                """, (username, user_id, course_id, filename, plan_path, normalized_category,
                      plan_type, title, 'active', self._now(), self._now()))
                
                plan_id = cursor.lastrowid
                if not plan_id:
                    cursor.execute(
                        """
                        SELECT plan_id FROM learning_plans
                        WHERE username = %s AND filename = %s
                          AND (course_id <=> %s)
                        """,
                        (username, filename, course_id),
                    )
                    r = cursor.fetchone()
                    plan_id = (r["plan_id"] if isinstance(r, dict) else r[0]) if r else None
                
                # 保存payload到learning_plan_nodes（作为单个节点存储完整数据）
                if plan_id and payload:
                    cursor.execute("""
                        INSERT INTO learning_plan_nodes
                        (plan_id, node_key, node_name, node_type, sequence_order, content, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            content = VALUES(content),
                            updated_at = VALUES(updated_at)
                    """, (plan_id, 'payload', filename, 'payload', 0,
                          self._json(payload), self._now(), self._now()))

    def save_learning_path_version(
        self,
        username: str,
        payload: Any,
        *,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save a personalized path version into the canonical path tables."""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id FROM users WHERE username = %s LIMIT 1", (username,))
                row = cursor.fetchone()
                user_id = (row["user_id"] if isinstance(row, dict) else row[0]) if row else None
                return self._save_learning_path_version_cursor(
                    cursor,
                    username=username,
                    user_id=user_id,
                    filename=filename,
                    payload=payload,
                )

    def _save_learning_path_version_cursor(
        self,
        cursor,
        *,
        username: str,
        user_id: Optional[int],
        filename: Optional[str],
        payload: Any,
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("learning path payload must be a dict")
        nodes = payload.get("formal_path_nodes")
        if not isinstance(nodes, list):
            nodes = []
        supplemental_items = payload.get("supplemental_items")
        if not isinstance(supplemental_items, list):
            supplemental_items = []
        diagnosis = payload.get("diagnosis") if isinstance(payload.get("diagnosis"), dict) else {}
        course_id = str(payload.get("course_id") or diagnosis.get("course_id") or "course_big_data").strip()
        if not course_id:
            course_id = "course_big_data"
        title = str(payload.get("title") or filename or "个性化学习路径").strip()
        summary = str(payload.get("summary") or diagnosis.get("summary") or "").strip() or None
        generated_reason = str(payload.get("trigger_type") or payload.get("manual_goal") or "diagnosis_based").strip()
        now = self._now()

        cursor.execute(
            """
            UPDATE learning_path_versions
            SET status = 'archived', updated_at = %s
            WHERE username = %s AND course_id = %s AND status = 'active'
            """,
            (now, username, course_id),
        )
        cursor.execute(
            """
            SELECT COALESCE(MAX(version_no), 0) + 1 AS next_version
            FROM learning_path_versions
            WHERE username = %s AND course_id = %s
            """,
            (username, course_id),
        )
        row = cursor.fetchone()
        version_no = int(row["next_version"] if isinstance(row, dict) else row[0])
        payload = dict(payload)
        payload["version_no"] = version_no
        payload["lifecycle_status"] = "active"
        cursor.execute(
            """
            INSERT INTO learning_path_versions
            (username, user_id, course_id, diagnosis_report_id, version_no,
             title, summary, status, generated_reason, source_payload_json,
             created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s)
            """,
            (
                username,
                user_id,
                course_id,
                diagnosis.get("report_id") or payload.get("basis_report_id"),
                version_no,
                title,
                summary,
                generated_reason,
                self._json(payload),
                now,
                now,
            ),
        )
        path_id = int(cursor.lastrowid)

        cursor.execute("DELETE FROM learning_path_items WHERE path_id = %s", (path_id,))
        formal_count = len(nodes)
        for index, item in enumerate([*nodes, *supplemental_items], start=1):
            if not isinstance(item, dict):
                continue
            item_course_id = str(item.get("course_id") or course_id).strip() or course_id
            node_id = str(item.get("node_id") or "").strip() or None
            if node_id:
                cursor.execute(
                    "SELECT 1 FROM course_nodes WHERE course_id = %s AND node_id = %s LIMIT 1",
                    (item_course_id, node_id),
                )
                if not cursor.fetchone():
                    node_id = None
            try:
                target_mastery = item.get("target_mastery")
                target_mastery = None if target_mastery is None else float(target_mastery)
            except (TypeError, ValueError):
                target_mastery = None
            try:
                resource_id = item.get("resource_id")
                resource_id = None if resource_id in (None, "") else int(resource_id)
            except (TypeError, ValueError):
                resource_id = None
            reason = str(
                item.get("recommendation_reason")
                or item.get("reason")
                or item.get("weak_reason")
                or "根据当前画像与诊断结果推荐"
            ).strip()
            cursor.execute(
                """
                INSERT INTO learning_path_items
                (path_id, course_id, node_id, resource_id, sequence_order, item_type,
                 recommendation_reason, target_mastery, status, payload_json, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s)
                """,
                (
                    path_id,
                    item_course_id,
                    node_id,
                    resource_id,
                    int(item.get("sequence_order") or index),
                    str(item.get("item_type") or "knowledge_point"),
                    reason,
                    target_mastery,
                    self._json(item),
                    now,
                    now,
                ),
            )
            item_id = int(cursor.lastrowid)
            if index <= formal_count:
                self._sync_learning_path_node_status(
                    cursor,
                    path_id=path_id,
                    item_id=item_id,
                    username=username,
                    user_id=user_id,
                    payload_item=item,
                    course_id=course_id,
                )
        return {
            "path_id": path_id,
            "username": username,
            "course_id": course_id,
            "version_no": version_no,
            "filename": filename or f"{username}_path_v{version_no}.json",
        }

    def _sync_learning_path_node_status(
        self,
        cursor,
        *,
        path_id: int,
        item_id: Optional[int],
        username: str,
        user_id: Optional[int],
        payload_item: Dict[str, Any],
        course_id: Optional[str],
    ) -> None:
        if not isinstance(payload_item, dict):
            return
        now = self._now()
        node_id = str(payload_item.get("node_id") or "").strip()
        if not node_id:
            return
        item_course_id = str(payload_item.get("course_id") or course_id or "").strip() or None
        item_type = str(payload_item.get("item_type") or "course_knowledge_point").strip() or "course_knowledge_point"
        source_type = str(payload_item.get("source") or payload_item.get("source_type") or "published_course_graph").strip() or "published_course_graph"
        try:
            mastery_before = payload_item.get("mastery_score")
            mastery_before = None if mastery_before is None else float(mastery_before)
        except (TypeError, ValueError):
            mastery_before = None
        cursor.execute(
            """
            INSERT INTO learning_path_node_status
            (path_id, item_id, username, user_id, course_id, node_id,
             item_type, source_type, status, mastery_before, payload_json,
             created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                item_id = VALUES(item_id),
                user_id = VALUES(user_id),
                course_id = VALUES(course_id),
                status = IF(status = 'completed', status, VALUES(status)),
                mastery_before = COALESCE(mastery_before, VALUES(mastery_before)),
                payload_json = VALUES(payload_json),
                updated_at = VALUES(updated_at)
            """,
            (
                path_id,
                item_id,
                username,
                user_id,
                item_course_id,
                node_id,
                item_type,
                source_type,
                "pending",
                mastery_before,
                self._json(payload_item),
                now,
                now,
            ),
        )

    def list_learning_path_node_status(
        self,
        username: str,
        *,
        path_id: Optional[int] = None,
        plan_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        username = str(username or "").strip()
        if not username:
            return []
        clauses = ["username = %s"]
        params: List[Any] = [username]
        resolved_path_id = path_id if path_id is not None else plan_id
        if resolved_path_id:
            clauses.append("path_id = %s")
            params.append(int(resolved_path_id))
        if status:
            clauses.append("status = %s")
            params.append(str(status).strip())
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT status_id, path_id, item_id, username, user_id, course_id,
                           node_id, item_type, source_type, status, mastery_before,
                           mastery_after, started_at, completed_at, payload_json,
                           created_at, updated_at
                    FROM learning_path_node_status
                    WHERE {' AND '.join(clauses)}
                    ORDER BY path_id DESC, status_id ASC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json")) if item.get("payload_json") else {}
            for key in ("mastery_before", "mastery_after"):
                if item.get(key) is not None:
                    item[key] = float(item[key])
            for key in ("started_at", "completed_at", "created_at", "updated_at"):
                item[key] = self._to_str(item.get(key))
            result.append(item)
        return result

    def update_learning_path_node_status(
        self,
        username: str,
        node_id: str,
        *,
        path_id: Optional[int] = None,
        plan_id: Optional[int] = None,
        status: str,
        mastery_after: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新学生个性化路径节点状态。"""
        username = str(username or "").strip()
        node_id = str(node_id or "").strip()
        status = str(status or "").strip().lower()
        if not username or not node_id:
            raise ValueError("username and node_id are required")
        if status not in {"pending", "in_progress", "completed", "skipped"}:
            raise ValueError("status must be pending, in_progress, completed or skipped")
        if mastery_after is not None:
            try:
                mastery_after = max(0.0, min(float(mastery_after), 100.0))
            except (TypeError, ValueError):
                mastery_after = None

        clauses = ["username = %s", "node_id = %s"]
        params: List[Any] = [username, node_id]
        resolved_path_id = path_id if path_id is not None else plan_id
        if resolved_path_id:
            clauses.append("path_id = %s")
            params.append(int(resolved_path_id))

        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT status_id, payload_json
                    FROM learning_path_node_status
                    WHERE {' AND '.join(clauses)}
                    ORDER BY path_id DESC, status_id ASC
                    LIMIT 1
                    """,
                    tuple(params),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                status_id = int(row["status_id"] if isinstance(row, dict) else row[0])
                current_payload_raw = row.get("payload_json") if isinstance(row, dict) else row[1]
                try:
                    current_payload = json.loads(current_payload_raw) if current_payload_raw else {}
                except Exception:
                    current_payload = {}
                if payload:
                    current_payload = {
                        **(current_payload if isinstance(current_payload, dict) else {}),
                        "status_update": payload,
                    }

                started_at_expr = "started_at"
                completed_at_expr = "completed_at"
                if status == "in_progress":
                    started_at_expr = "COALESCE(started_at, %s)"
                elif status == "completed":
                    started_at_expr = "COALESCE(started_at, %s)"
                    completed_at_expr = "COALESCE(completed_at, %s)"

                update_params: List[Any] = [status]
                if status in {"in_progress", "completed"}:
                    update_params.append(now)
                if status == "completed":
                    update_params.append(now)
                update_params.extend([mastery_after, self._json(current_payload), now, status_id])
                cursor.execute(
                    f"""
                    UPDATE learning_path_node_status
                    SET status = %s,
                        started_at = {started_at_expr},
                        completed_at = {completed_at_expr},
                        mastery_after = COALESCE(%s, mastery_after),
                        payload_json = %s,
                        updated_at = %s
                    WHERE status_id = %s
                    """,
                    tuple(update_params),
                )

        updated = self.list_learning_path_node_status(username, path_id=resolved_path_id)
        return next((item for item in updated if int(item.get("status_id") or 0) == status_id), None)

    def list_learning_plans(self, username: Optional[str] = None, categories: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        """列出学习计划"""
        sql = """
            SELECT lp.plan_id, lp.username, lp.course_id, lp.filename, lp.plan_path,
                   lp.category, lp.plan_type, lp.title, lp.status, lp.updated_at,
                   lpn.content as payload_json
            FROM learning_plans lp
            LEFT JOIN learning_plan_nodes lpn ON lpn.plan_id = lp.plan_id AND lpn.node_key = 'payload'
        """
        clauses: List[str] = []
        params: List[Any] = []
        if username:
            clauses.append("lp.username = %s")
            params.append(username)
        if categories:
            cat_list = [c for c in categories if c]
            if cat_list:
                placeholders = ", ".join(["%s"] * len(cat_list))
                clauses.append(f"lp.category IN ({placeholders})")
                params.extend(cat_list)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY lp.updated_at DESC, lp.filename DESC"
        
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        
        result = []
        for row in rows:
            r = dict(row) if isinstance(row, dict) else {
                "plan_id": row[0], "username": row[1], "course_id": row[2],
                "filename": row[3], "plan_path": row[4], "category": row[5],
                "plan_type": row[6], "title": row[7], "status": row[8],
                "updated_at": row[9], "payload_json": row[10]
            }
            try:
                data = r["payload_json"]
                if isinstance(data, str):
                    data = json.loads(data)
                elif data is None:
                    data = {}
            except Exception:
                data = {}
            result.append({
                "plan_id": r["plan_id"],
                "username": r["username"],
                "course_id": r.get("course_id"),
                "filename": r["filename"],
                "title": r.get("title") or r["filename"],
                "path": r["plan_path"] or "",
                "category": r["category"] or "",
                "plan_type": r.get("plan_type") or "",
                "status": r["status"] or "",
                "data": data,
                "updated_at": self._to_str(r["updated_at"]) or "",
            })
        return result

    def list_learning_plans_by_user_identifier(self, user_identifier: str, user_type: Optional[str] = None, categories: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        """根据用户标识符列出学习计划"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT username FROM users WHERE user_id = %s OR login_id = %s OR username = %s LIMIT 1",
                               (user_identifier, user_identifier, user_identifier))
                row = cursor.fetchone()
        username = (row["username"] if isinstance(row, dict) else row[0]) if row else user_identifier
        return self.list_learning_plans(username=username, categories=categories)

    def get_latest_learning_plan(self, username: str, category: Optional[str] = None, filename_prefix: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取最新的学习计划"""
        plans = self.list_learning_plans(username=username, categories=[category] if category else None)
        if filename_prefix:
            plans = [p for p in plans if p.get("filename", "").startswith(filename_prefix)]
        return plans[0] if plans else None

    def list_learning_path_versions(
        self,
        *,
        username: str,
        course_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """List personalized path versions from the dedicated path tables."""
        username = str(username or "").strip()
        course_id = str(course_id or "").strip()
        if not username:
            return []
        clauses = ["lpv.username = %s"]
        params: List[Any] = [username]
        if course_id:
            clauses.append("lpv.course_id = %s")
            params.append(course_id)
        safe_limit = max(1, min(int(limit or 10), 50))
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT lpv.path_id, lpv.username, lpv.user_id,
                           lpv.course_id, lpv.diagnosis_report_id, lpv.version_no,
                           lpv.title, lpv.summary, lpv.status, lpv.generated_reason,
                           lpv.source_payload_json, lpv.created_at, lpv.updated_at
                    FROM learning_path_versions lpv
                    WHERE {' AND '.join(clauses)}
                    ORDER BY lpv.updated_at DESC, lpv.path_id DESC
                    LIMIT %s
                    """,
                    tuple([*params, safe_limit]),
                )
                rows = cursor.fetchall()
        return [self._learning_path_version_to_plan(row) for row in rows]

    def archive_active_learning_paths(self, *, username: str, course_id: Optional[str] = None) -> int:
        """Archive previous active personalized path versions for a student/course."""
        username = str(username or "").strip()
        course_id = str(course_id or "").strip()
        if not username:
            return 0
        clauses = ["username = %s", "status = 'active'"]
        params: List[Any] = [username]
        if course_id:
            clauses.append("course_id = %s")
            params.append(course_id)
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE learning_path_versions
                    SET status = 'archived', updated_at = %s
                    WHERE {' AND '.join(clauses)}
                    """,
                    tuple([now, *params]),
                )
                return int(cursor.rowcount or 0)

    def get_active_learning_path(
        self,
        *,
        username: str,
        course_id: Optional[str] = None,
        filename_prefix: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the latest active personalized path, optionally scoped to a course."""
        username = str(username or "").strip()
        if not username:
            return None
        course_id = str(course_id or "").strip()
        try:
            versions = self.list_learning_path_versions(
                username=username,
                course_id=course_id or None,
                limit=10,
            )
            active_versions = [
                item for item in versions
                if str(item.get("status") or "").lower() == "active"
            ]
            if active_versions:
                if filename_prefix:
                    active_versions = [
                        item for item in active_versions
                        if str(item.get("filename") or "").startswith(filename_prefix)
                    ]
                if active_versions:
                    return active_versions[0]
        except Exception:
            logger.exception("Failed to read active learning path version for %s", username)
        return None

    def _learning_path_version_to_plan(self, row: Dict[str, Any]) -> Dict[str, Any]:
        data = row.get("source_payload_json")
        try:
            if isinstance(data, str):
                data = json.loads(data)
            elif data is None:
                data = {}
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        data.setdefault("course_id", row.get("course_id"))
        data.setdefault("version_no", row.get("version_no"))
        data.setdefault("path_id", row.get("path_id"))
        data.setdefault("lifecycle_status", row.get("status"))
        data.setdefault("basis_report_id", row.get("diagnosis_report_id"))
        if row.get("generated_reason") and not data.get("trigger_type"):
            data["trigger_type"] = row.get("generated_reason")
        return {
            "path_id": row.get("path_id"),
            "username": row.get("username"),
            "user_id": row.get("user_id"),
            "course_id": row.get("course_id"),
            "filename": f"{row.get('username')}_path_v{row.get('version_no')}.json",
            "title": row.get("title") or "个性化学习路径",
            "path": "",
            "category": "path",
            "plan_type": "personalized_path",
            "status": row.get("status") or "",
            "data": data,
            "updated_at": self._to_str(row.get("updated_at")) or "",
            "created_at": self._to_str(row.get("created_at")) or "",
        }

    def _iter_graph_children(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """遍历图谱节点的子节点"""
        for key in ("children", "grandchildren", "great-grandchildren"):
            children = node.get(key)
            if isinstance(children, list):
                return [item for item in children if isinstance(item, dict)]
        return []

    def sync_course_from_graph(
        self,
        course_id: str,
        graph_data: Dict[str, Any],
        *,
        course_name: Optional[str] = None,
        source_path: Optional[str] = None,
        lifecycle_status: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Dict[str, int]:
        """从课程图谱同步课程数据到MySQL"""
        if not isinstance(graph_data, dict):
            return {"nodes": 0, "resources": 0}
        course_id = str(course_id or "").strip()
        if not course_id:
            return {"nodes": 0, "resources": 0}

        now = self._now()
        course_name = str(course_name or graph_data.get("name") or course_id)
        normalized_status = str(lifecycle_status or "published").strip().lower()
        if normalized_status not in {"draft", "published", "archived"}:
            normalized_status = "draft"
        nodes: List[Dict[str, Any]] = []
        resources: List[Dict[str, Any]] = []

        name_counts: Dict[str, int] = {}

        def collect_names(node: Dict[str, Any]) -> None:
            node_name = str(node.get("name") or "").strip()
            if node_name:
                name_counts[node_name] = name_counts.get(node_name, 0) + 1
            for child in self._iter_graph_children(node):
                collect_names(child)

        for root_child in self._iter_graph_children(graph_data):
            collect_names(root_child)

        def build_node_id(node_name: str, node_path: List[str]) -> str:
            raw_id = str(node_path[-1] if node_path else node_name).strip()
            explicit_id = raw_id if name_counts.get(node_name, 0) <= 1 else " / ".join(node_path)
            return explicit_id[:200]

        def infer_resource_type(resource_path: str) -> Optional[str]:
            value = str(resource_path or "").strip().lower()
            if not value:
                return None
            if value.startswith(("http://", "https://")) or ".m3u8" in value:
                return "video"
            from pathlib import Path as _Path
            suffix = _Path(value).suffix.lower().lstrip(".")
            return suffix[:200] if suffix else None

        def walk(node: Dict[str, Any], path: List[str], parent_node_id: Optional[str]) -> None:
            node_name = str(node.get("name") or "").strip()
            if not node_name:
                return
            node_path = path + [node_name]
            node_id = str(node.get("node_id") or node.get("id") or build_node_id(node_name, node_path)).strip()
            nodes.append({
                "node_id": node_id, "node_name": node_name,
                "node_path": node_path, "depth": max(len(node_path) - 1, 0),
                "parent_node_id": parent_node_id, "payload": node,
            })
            raw_res = node.get("resource_path", [])
            if isinstance(raw_res, str):
                raw_res = [raw_res] if raw_res else []
            if isinstance(raw_res, list):
                for item in raw_res:
                    rp = str(item or "").strip()
                    if not rp:
                        continue
                    from pathlib import Path as _Path
                    resources.append({
                        "node_id": node_id, "resource_path": rp,
                        "resource_type": infer_resource_type(rp),
                        "title": _Path(rp).name[:500],
                        "source": "external" if rp.startswith(("http://", "https://")) else "local",
                        "payload": {"resource_path": rp, "node_id": node_id},
                    })
            for child in self._iter_graph_children(node):
                walk(child, node_path, node_id)

        for root_child in self._iter_graph_children(graph_data):
            walk(root_child, [], None)

        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                # 更新courses表
                cursor.execute("""
                    INSERT INTO courses
                    (course_id, course_name, source_path, lifecycle_status, published_at, published_by, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        course_name = VALUES(course_name),
                        source_path = VALUES(source_path),
                        lifecycle_status = VALUES(lifecycle_status),
                        published_at = CASE WHEN VALUES(lifecycle_status) = 'published' THEN VALUES(published_at) ELSE published_at END,
                        published_by = CASE WHEN VALUES(lifecycle_status) = 'published' THEN VALUES(published_by) ELSE published_by END,
                        payload_json = VALUES(payload_json),
                        updated_at = VALUES(updated_at)
                """, (
                    course_id,
                    course_name,
                    source_path,
                    normalized_status,
                    now if normalized_status == "published" else None,
                    updated_by if normalized_status == "published" else None,
                    self._json(graph_data),
                    now,
                    now,
                ))
                
                # 更新course_metadata
                cursor.execute("""
                    INSERT INTO course_metadata (course_id, additional_data, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        additional_data = VALUES(additional_data),
                        updated_at = VALUES(updated_at)
                """, (course_id, self._json({"root_name": graph_data.get("root_name", ""), "structure": graph_data}), now, now))
                
                cursor.execute(
                    """
                    SELECT node_id, resource_path, quality_status, review_status,
                           is_enabled, is_deleted, deleted_at, deleted_by
                    FROM resources
                    WHERE course_id = %s
                    """,
                    (course_id,),
                )
                existing_resource_state = {
                    (str(row.get("node_id") or ""), str(row.get("resource_path") or "")): row
                    for row in cursor.fetchall()
                }

                incoming_node_ids = sorted({
                    str(node.get("node_id") or "").strip()
                    for node in nodes
                    if str(node.get("node_id") or "").strip()
                })

                # Rebuild the managed graph while preserving homework-bound legacy
                # nodes; homework_assignments has a restrictive FK on
                # (course_id, node_id), so a full table wipe can strand demos.
                if incoming_node_ids:
                    for start in range(0, len(incoming_node_ids), 100):
                        chunk = incoming_node_ids[start:start + 100]
                        placeholders = ", ".join(["%s"] * len(chunk))
                        cursor.execute(
                            f"""
                            DELETE FROM resources
                            WHERE course_id = %s AND node_id IN ({placeholders})
                            """,
                            tuple([course_id, *chunk]),
                        )
                    placeholders = ", ".join(["%s"] * len(incoming_node_ids))
                    cursor.execute(
                        f"""
                        DELETE FROM course_nodes
                        WHERE course_id = %s
                          AND node_id NOT IN ({placeholders})
                          AND NOT EXISTS (
                              SELECT 1
                              FROM homework_assignments ha
                              WHERE ha.course_id = course_nodes.course_id
                                AND ha.node_id = course_nodes.node_id
                          )
                        """,
                        tuple([course_id, *incoming_node_ids]),
                    )
                else:
                    cursor.execute("DELETE FROM resources WHERE course_id = %s", (course_id,))
                    cursor.execute(
                        """
                        DELETE FROM course_nodes
                        WHERE course_id = %s
                          AND NOT EXISTS (
                              SELECT 1
                              FROM homework_assignments ha
                              WHERE ha.course_id = course_nodes.course_id
                                AND ha.node_id = course_nodes.node_id
                          )
                        """,
                        (course_id,),
                    )
                
                for node in nodes:
                    cursor.execute("""
                        INSERT INTO course_nodes
                        (course_id, node_id, node_name, node_path_json, depth, parent_node_id, payload_json, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            node_name = VALUES(node_name),
                            node_path_json = VALUES(node_path_json),
                            depth = VALUES(depth),
                            parent_node_id = VALUES(parent_node_id),
                            payload_json = VALUES(payload_json),
                            updated_at = VALUES(updated_at)
                    """, (course_id, node["node_id"], node["node_name"],
                          self._json(node["node_path"]), node["depth"],
                          node["parent_node_id"], self._json(node["payload"]), now, now))
                
                for resource in resources:
                    rp = resource["resource_path"][:1000]
                    previous = existing_resource_state.get((str(resource["node_id"]), rp), {})
                    quality_status = previous.get("quality_status") or "passed"
                    review_status = previous.get("review_status") or "enabled"
                    is_enabled = previous.get("is_enabled")
                    if is_enabled is None:
                        is_enabled = 1
                    is_deleted = previous.get("is_deleted")
                    if is_deleted is None:
                        is_deleted = 0
                    cursor.execute("""
                        INSERT INTO resources
                        (course_id, node_id, resource_path, resource_type, title, payload_json,
                         resource_source, quality_status, review_status, is_enabled,
                         is_deleted, deleted_at, deleted_by, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            resource_type = VALUES(resource_type),
                            title = VALUES(title),
                            payload_json = VALUES(payload_json),
                            resource_source = VALUES(resource_source),
                            quality_status = VALUES(quality_status),
                            review_status = VALUES(review_status),
                            is_enabled = VALUES(is_enabled),
                            is_deleted = VALUES(is_deleted),
                            deleted_at = VALUES(deleted_at),
                            deleted_by = VALUES(deleted_by),
                            updated_at = VALUES(updated_at)
                    """, (course_id, resource["node_id"], rp,
                          resource["resource_type"], resource["title"],
                          self._json(resource["payload"]),
                          resource["source"],
                          quality_status,
                          review_status,
                          1 if bool(is_enabled) else 0,
                          1 if bool(is_deleted) else 0,
                          previous.get("deleted_at"),
                          previous.get("deleted_by"),
                          now,
                          now))
        
        return {"nodes": len(nodes), "resources": len(resources)}

    def list_courses(self) -> List[Dict[str, Any]]:
        """列出课程建设底座。"""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.course_id, c.course_name, c.description, c.lifecycle_status,
                           c.published_at, c.published_by, c.created_at, c.updated_at,
                           COUNT(DISTINCT n.node_detail_id) AS node_count,
                           COUNT(DISTINCT r.resource_id) AS resource_count
                    FROM courses c
                    LEFT JOIN course_nodes n ON n.course_id = c.course_id
                    LEFT JOIN resources r ON r.course_id = c.course_id AND r.is_deleted = 0
                    GROUP BY c.course_id, c.course_name, c.description, c.lifecycle_status,
                             c.published_at, c.published_by, c.created_at, c.updated_at
                    ORDER BY c.updated_at DESC, c.course_id
                    """
                )
                rows = cursor.fetchall()
        return [
            {
                "course_id": row["course_id"],
                "course_name": row["course_name"],
                "description": row.get("description"),
                "lifecycle_status": row.get("lifecycle_status") or "draft",
                "published_at": self._to_str(row.get("published_at")),
                "published_by": row.get("published_by"),
                "created_at": self._to_str(row.get("created_at")),
                "updated_at": self._to_str(row.get("updated_at")),
                "node_count": int(row.get("node_count") or 0),
                "resource_count": int(row.get("resource_count") or 0),
            }
            for row in rows
        ]

    def list_student_courses(self, username: str) -> List[Dict[str, Any]]:
        """List published courses visible to a student, enrollment first."""
        username = str(username or "").strip()
        if not username:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                enrollment_columns = self._table_columns(cursor, "course_enrollments")
                class_name_select = "ce.class_name" if "class_name" in enrollment_columns else "NULL"
                cursor.execute(
                    f"""
                    SELECT c.course_id, c.course_name, c.description, c.lifecycle_status,
                           c.published_at, c.published_by, c.created_at, c.updated_at,
                           ce.status AS enrollment_status, {class_name_select} AS class_name,
                           COALESCE(nc.node_count, 0) AS node_count,
                           COALESCE(rc.resource_count, 0) AS resource_count
                    FROM course_enrollments ce
                    JOIN courses c ON c.course_id = ce.course_id
                    LEFT JOIN (
                        SELECT course_id, COUNT(*) AS node_count
                        FROM course_nodes
                        GROUP BY course_id
                    ) nc ON nc.course_id = c.course_id
                    LEFT JOIN (
                        SELECT course_id, COUNT(*) AS resource_count
                        FROM resources
                        WHERE is_deleted = 0
                          AND is_enabled = 1
                        GROUP BY course_id
                    ) rc ON rc.course_id = c.course_id
                    WHERE ce.student_username = %s
                      AND ce.status = 'active'
                      AND c.lifecycle_status = 'published'
                    ORDER BY ce.enrolled_at DESC, c.updated_at DESC, c.course_id
                    """,
                    (username,),
                )
                rows = cursor.fetchall()
                if not rows:
                    cursor.execute(
                        """
                        SELECT c.course_id, c.course_name, c.description, c.lifecycle_status,
                               c.published_at, c.published_by, c.created_at, c.updated_at,
                               NULL AS enrollment_status, NULL AS class_name,
                               COALESCE(nc.node_count, 0) AS node_count,
                               COALESCE(rc.resource_count, 0) AS resource_count
                        FROM courses c
                        LEFT JOIN (
                            SELECT course_id, COUNT(*) AS node_count
                            FROM course_nodes
                            GROUP BY course_id
                        ) nc ON nc.course_id = c.course_id
                        LEFT JOIN (
                            SELECT course_id, COUNT(*) AS resource_count
                            FROM resources
                            WHERE is_deleted = 0
                              AND is_enabled = 1
                            GROUP BY course_id
                        ) rc ON rc.course_id = c.course_id
                        WHERE c.lifecycle_status = 'published'
                        ORDER BY c.updated_at DESC, c.course_id
                        """
                    )
                    rows = cursor.fetchall()
        return [
            {
                "course_id": row["course_id"],
                "course_name": row["course_name"],
                "description": row.get("description"),
                "lifecycle_status": row.get("lifecycle_status") or "published",
                "published_at": self._to_str(row.get("published_at")),
                "published_by": row.get("published_by"),
                "created_at": self._to_str(row.get("created_at")),
                "updated_at": self._to_str(row.get("updated_at")),
                "enrollment_status": row.get("enrollment_status") or "available",
                "class_name": row.get("class_name"),
                "node_count": int(row.get("node_count") or 0),
                "resource_count": int(row.get("resource_count") or 0),
            }
            for row in rows
        ]

    def get_course_summary(self, course_id: str) -> Optional[Dict[str, Any]]:
        """获取课程结构、资源和发布状态摘要。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return None
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT course_id, course_name, description, lifecycle_status,
                           published_at, published_by, created_at, updated_at
                    FROM courses
                    WHERE course_id = %s
                    LIMIT 1
                    """,
                    (course_id,),
                )
                course = cursor.fetchone()
                if not course:
                    return None
                cursor.execute(
                    """
                    SELECT
                        COUNT(DISTINCT n.node_detail_id) AS node_count,
                        COUNT(DISTINCT CASE WHEN child.node_id IS NULL THEN n.node_detail_id END) AS leaf_node_count
                    FROM course_nodes n
                    LEFT JOIN course_nodes child
                      ON child.course_id = n.course_id AND child.parent_node_id = n.node_id
                    WHERE n.course_id = %s
                    """,
                    (course_id,),
                )
                node_stats = cursor.fetchone() or {}
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS resource_count,
                        SUM(CASE WHEN is_enabled = 1 AND is_deleted = 0 THEN 1 ELSE 0 END) AS enabled_resource_count,
                        SUM(CASE WHEN resource_source = 'external' AND is_deleted = 0 THEN 1 ELSE 0 END) AS external_resource_count,
                        SUM(CASE WHEN review_status <> 'enabled' AND is_deleted = 0 THEN 1 ELSE 0 END) AS pending_or_disabled_count
                    FROM resources
                    WHERE course_id = %s
                    """,
                    (course_id,),
                )
                resource_stats = cursor.fetchone() or {}
        return {
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "description": course.get("description"),
            "lifecycle_status": course.get("lifecycle_status") or "draft",
            "published_at": self._to_str(course.get("published_at")),
            "published_by": course.get("published_by"),
            "created_at": self._to_str(course.get("created_at")),
            "updated_at": self._to_str(course.get("updated_at")),
            "node_count": int(node_stats.get("node_count") or 0),
            "leaf_node_count": int(node_stats.get("leaf_node_count") or 0),
            "resource_count": int(resource_stats.get("resource_count") or 0),
            "enabled_resource_count": int(resource_stats.get("enabled_resource_count") or 0),
            "external_resource_count": int(resource_stats.get("external_resource_count") or 0),
            "pending_or_disabled_resource_count": int(resource_stats.get("pending_or_disabled_count") or 0),
        }

    def publish_course(self, course_id: str, published_by: Optional[str] = None) -> bool:
        """发布课程底座，供学生端、诊断、路径和看板读取。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return False
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE courses
                    SET lifecycle_status = 'published',
                        published_at = %s,
                        published_by = %s,
                        updated_at = %s
                    WHERE course_id = %s
                    """,
                    (now, published_by, now, course_id),
                )
                return int(cursor.rowcount or 0) > 0

    def list_course_resources(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程资源审核清单。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT r.resource_id, r.course_id, r.node_id, n.node_name,
                           r.resource_path, r.resource_type, r.title,
                           r.resource_source, r.quality_status, r.review_status,
                           r.is_enabled, r.is_deleted, r.deleted_at, r.deleted_by,
                           r.created_at, r.updated_at
                    FROM resources r
                    LEFT JOIN course_nodes n ON n.course_id = r.course_id AND n.node_id = r.node_id
                    WHERE r.course_id = %s
                    ORDER BY n.depth, n.node_name, r.resource_id
                    """,
                    (course_id,),
                )
                rows = cursor.fetchall()
        return [
            {
                "resource_id": row["resource_id"],
                "course_id": row["course_id"],
                "node_id": row["node_id"],
                "node_name": row.get("node_name"),
                "resource_path": row["resource_path"],
                "resource_type": row.get("resource_type"),
                "title": row.get("title"),
                "resource_source": row.get("resource_source") or "local",
                "quality_status": row.get("quality_status") or "unchecked",
                "review_status": row.get("review_status") or "enabled",
                "is_enabled": bool(row.get("is_enabled")),
                "is_deleted": bool(row.get("is_deleted")),
                "deleted_at": self._to_str(row.get("deleted_at")),
                "deleted_by": row.get("deleted_by"),
                "created_at": self._to_str(row.get("created_at")),
                "updated_at": self._to_str(row.get("updated_at")),
            }
            for row in rows
        ]

    def set_resource_review_status(
        self,
        course_id: str,
        node_id: str,
        resource_path: str,
        *,
        is_enabled: bool,
        review_status: str = "enabled",
        quality_status: Optional[str] = None,
    ) -> bool:
        """设置资源是否启用和审核状态。"""
        course_id = str(course_id or "").strip()
        node_id = str(node_id or "").strip()
        resource_path = str(resource_path or "").strip()
        status = str(review_status or ("enabled" if is_enabled else "disabled")).strip().lower()
        if status not in {"enabled", "disabled", "pending", "rejected"}:
            status = "enabled" if is_enabled else "disabled"
        if not course_id or not node_id or not resource_path:
            return False
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                if quality_status:
                    cursor.execute(
                        """
                        UPDATE resources
                        SET is_enabled = %s,
                            review_status = %s,
                            quality_status = %s,
                            updated_at = %s
                        WHERE course_id = %s AND node_id = %s AND resource_path = %s
                        """,
                        (1 if is_enabled else 0, status, quality_status, now, course_id, node_id, resource_path),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE resources
                        SET is_enabled = %s,
                            review_status = %s,
                            updated_at = %s
                        WHERE course_id = %s AND node_id = %s AND resource_path = %s
                        """,
                        (1 if is_enabled else 0, status, now, course_id, node_id, resource_path),
                    )
                return int(cursor.rowcount or 0) > 0

    def _normalize_position_name(self, value: str) -> str:
        return " ".join(str(value or "").strip().lower().split())[:200]

    def _normalize_support_level(self, value: Optional[str]) -> str:
        raw = str(value or "").strip().lower()
        mapping = {
            "high": "high",
            "medium": "medium",
            "mid": "medium",
            "low": "low",
            "高": "high",
            "中": "medium",
            "低": "low",
        }
        return mapping.get(raw, "medium")

    def _support_weight(self, support_level: Optional[str], explicit_weight: Optional[Any] = None) -> float:
        if explicit_weight is not None:
            try:
                return max(0.0, min(float(explicit_weight), 1.0))
            except (TypeError, ValueError):
                pass
        return {"high": 1.0, "medium": 0.6, "low": 0.3}.get(self._normalize_support_level(support_level), 0.6)

    def upsert_career_position(
        self,
        course_id: str,
        position_name: str,
        *,
        position_type: str = "related",
        target_rank: int = 0,
        source_keyword: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """保存课程目标岗位配置。"""
        course_id = str(course_id or "").strip()
        position_name = str(position_name or "").strip()
        normalized_name = self._normalize_position_name(position_name)
        if not course_id or not position_name or not normalized_name:
            raise ValueError("course_id and position_name are required")
        normalized_type = str(position_type or "related").strip().lower()
        if normalized_type not in {"primary", "related"}:
            normalized_type = "related"
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT course_id FROM courses WHERE course_id = %s LIMIT 1", (course_id,))
                if not cursor.fetchone():
                    raise ValueError(f"course not found: {course_id}")
                cursor.execute(
                    """
                    INSERT INTO career_positions
                    (course_id, position_name, normalized_name, source_keyword,
                     position_type, target_rank, created_by, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        position_name = VALUES(position_name),
                        source_keyword = VALUES(source_keyword),
                        position_type = VALUES(position_type),
                        target_rank = VALUES(target_rank),
                        created_by = COALESCE(VALUES(created_by), created_by),
                        updated_at = VALUES(updated_at)
                    """,
                    (
                        course_id,
                        position_name,
                        normalized_name,
                        source_keyword,
                        normalized_type,
                        int(target_rank or 0),
                        created_by,
                        now,
                        now,
                    ),
                )
                cursor.execute(
                    """
                    SELECT position_id, course_id, position_name, normalized_name,
                           source_keyword, position_type, target_rank, created_by,
                           created_at, updated_at
                    FROM career_positions
                    WHERE course_id = %s AND normalized_name = %s
                    LIMIT 1
                    """,
                    (course_id, normalized_name),
                )
                row = cursor.fetchone()
        return self._career_position_row(row) if row else {}

    def _career_position_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "position_id": int(row["position_id"]),
            "course_id": row["course_id"],
            "position_name": row["position_name"],
            "normalized_name": row.get("normalized_name"),
            "source_keyword": row.get("source_keyword"),
            "position_type": row.get("position_type") or "related",
            "target_rank": int(row.get("target_rank") or 0),
            "created_by": row.get("created_by"),
            "created_at": self._to_str(row.get("created_at")),
            "updated_at": self._to_str(row.get("updated_at")),
        }

    def list_course_positions(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程已配置的主要岗位和关联岗位。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT position_id, course_id, position_name, normalized_name,
                           source_keyword, position_type, target_rank, created_by,
                           created_at, updated_at
                    FROM career_positions
                    WHERE course_id = %s
                    ORDER BY CASE WHEN position_type = 'primary' THEN 0 ELSE 1 END,
                             target_rank, position_id
                    """,
                    (course_id,),
                )
                rows = cursor.fetchall()
        return [self._career_position_row(row) for row in rows]

    def upsert_career_abilities(self, position_id: int, abilities: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """保存某岗位下的职业能力候选。"""
        items = [item for item in abilities if isinstance(item, dict)]
        if not position_id:
            raise ValueError("position_id is required")
        now = self._now()
        ability_ids: List[int] = []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT position_id FROM career_positions WHERE position_id = %s LIMIT 1", (position_id,))
                if not cursor.fetchone():
                    raise ValueError(f"position not found: {position_id}")
                for item in items:
                    ability_name = str(item.get("ability_name") or item.get("name") or "").strip()
                    if not ability_name:
                        continue
                    support_level = self._normalize_support_level(item.get("support_level") or item.get("demand_level_label"))
                    demand_level = item.get("demand_level")
                    if demand_level is None and item.get("count") is not None:
                        demand_level = item.get("count")
                    try:
                        demand_value = float(demand_level) if demand_level is not None else None
                    except (TypeError, ValueError):
                        demand_value = None
                    evidence = item.get("evidence") or item.get("evidence_json") or item
                    cursor.execute(
                        """
                        INSERT INTO career_abilities
                        (position_id, ability_name, ability_category, demand_level,
                         support_level, evidence_json, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            ability_category = VALUES(ability_category),
                            demand_level = VALUES(demand_level),
                            support_level = VALUES(support_level),
                            evidence_json = VALUES(evidence_json),
                            updated_at = VALUES(updated_at)
                        """,
                        (
                            position_id,
                            ability_name[:300],
                            str(item.get("ability_category") or item.get("category") or "")[:100] or None,
                            demand_value,
                            support_level,
                            self._json(evidence),
                            now,
                            now,
                        ),
                    )
                    cursor.execute(
                        """
                        SELECT ability_id FROM career_abilities
                        WHERE position_id = %s AND ability_name = %s
                        LIMIT 1
                        """,
                        (position_id, ability_name[:300]),
                    )
                    row = cursor.fetchone()
                    if row:
                        ability_ids.append(int(row["ability_id"]))
        return {"position_id": int(position_id), "saved": len(ability_ids), "ability_ids": ability_ids}

    def list_course_abilities(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程岗位下的职业能力。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT a.ability_id, a.position_id, p.course_id, p.position_name,
                           p.position_type, a.ability_name, a.ability_category,
                           a.demand_level, a.support_level, a.evidence_json,
                           a.created_at, a.updated_at
                    FROM career_abilities a
                    JOIN career_positions p ON p.position_id = a.position_id
                    WHERE p.course_id = %s
                    ORDER BY CASE WHEN p.position_type = 'primary' THEN 0 ELSE 1 END,
                             p.target_rank, p.position_id, a.demand_level DESC, a.ability_id
                    """,
                    (course_id,),
                )
                rows = cursor.fetchall()
        result = []
        for row in rows:
            evidence = row.get("evidence_json")
            if isinstance(evidence, str):
                try:
                    evidence = json.loads(evidence)
                except Exception:
                    evidence = {}
            result.append(
                {
                    "ability_id": int(row["ability_id"]),
                    "position_id": int(row["position_id"]),
                    "course_id": row["course_id"],
                    "position_name": row["position_name"],
                    "position_type": row.get("position_type") or "related",
                    "ability_name": row["ability_name"],
                    "ability_category": row.get("ability_category"),
                    "demand_level": float(row["demand_level"]) if row.get("demand_level") is not None else None,
                    "support_level": row.get("support_level") or "medium",
                    "evidence": evidence or {},
                    "created_at": self._to_str(row.get("created_at")),
                    "updated_at": self._to_str(row.get("updated_at")),
                }
            )
        return result

    def upsert_course_ability_mappings(
        self,
        course_id: str,
        mappings: Iterable[Dict[str, Any]],
        *,
        updated_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """保存职业能力与叶子知识点支撑关系。"""
        course_id = str(course_id or "").strip()
        items = [item for item in mappings if isinstance(item, dict)]
        if not course_id:
            raise ValueError("course_id is required")
        now = self._now()
        saved = 0
        rejected: List[Dict[str, Any]] = []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                for item in items:
                    node_id = str(item.get("node_id") or "").strip()
                    ability_id = item.get("ability_id")
                    try:
                        ability_id_int = int(ability_id)
                    except (TypeError, ValueError):
                        rejected.append({"node_id": node_id, "ability_id": ability_id, "reason": "invalid ability_id"})
                        continue
                    cursor.execute(
                        """
                        SELECT n.node_id
                        FROM course_nodes n
                        LEFT JOIN course_nodes child
                          ON child.course_id = n.course_id AND child.parent_node_id = n.node_id
                        WHERE n.course_id = %s AND n.node_id = %s AND child.node_id IS NULL
                        LIMIT 1
                        """,
                        (course_id, node_id),
                    )
                    if not cursor.fetchone():
                        rejected.append({"node_id": node_id, "ability_id": ability_id_int, "reason": "node is not a leaf knowledge point"})
                        continue
                    cursor.execute(
                        """
                        SELECT a.ability_id
                        FROM career_abilities a
                        JOIN career_positions p ON p.position_id = a.position_id
                        WHERE a.ability_id = %s AND p.course_id = %s
                        LIMIT 1
                        """,
                        (ability_id_int, course_id),
                    )
                    if not cursor.fetchone():
                        rejected.append({"node_id": node_id, "ability_id": ability_id_int, "reason": "ability does not belong to course"})
                        continue
                    support_level = self._normalize_support_level(item.get("support_level"))
                    support_weight = self._support_weight(support_level, item.get("support_weight"))
                    review_status = str(item.get("review_status") or "draft").strip().lower()
                    if review_status not in {"draft", "confirmed", "rejected"}:
                        review_status = "draft"
                    reviewed_by = updated_by if review_status in {"confirmed", "rejected"} else None
                    reviewed_at = now if reviewed_by else None
                    cursor.execute(
                        """
                        INSERT INTO course_ability_mappings
                        (course_id, node_id, ability_id, support_weight, support_level,
                         match_reason, evidence_json, review_status, reviewed_by,
                         reviewed_at, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            support_weight = VALUES(support_weight),
                            support_level = VALUES(support_level),
                            match_reason = VALUES(match_reason),
                            evidence_json = VALUES(evidence_json),
                            review_status = VALUES(review_status),
                            reviewed_by = VALUES(reviewed_by),
                            reviewed_at = VALUES(reviewed_at),
                            updated_at = VALUES(updated_at)
                        """,
                        (
                            course_id,
                            node_id,
                            ability_id_int,
                            support_weight,
                            support_level,
                            item.get("match_reason"),
                            self._json(item.get("evidence") or item.get("evidence_json") or {}),
                            review_status,
                            reviewed_by,
                            reviewed_at,
                            now,
                            now,
                        ),
                    )
                    saved += 1
        return {"course_id": course_id, "saved": saved, "rejected": rejected}

    def list_course_ability_mappings(self, course_id: str) -> List[Dict[str, Any]]:
        """列出课程职业能力到叶子知识点的映射矩阵。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT m.mapping_id, m.course_id, m.node_id, n.node_name,
                           n.node_path_json, m.ability_id, a.ability_name,
                           a.ability_category, p.position_id, p.position_name,
                           p.position_type, m.support_weight, m.support_level,
                           m.match_reason, m.evidence_json, m.review_status,
                           m.reviewed_by, m.reviewed_at, m.created_at, m.updated_at
                    FROM course_ability_mappings m
                    JOIN course_nodes n ON n.course_id = m.course_id AND n.node_id = m.node_id
                    JOIN career_abilities a ON a.ability_id = m.ability_id
                    JOIN career_positions p ON p.position_id = a.position_id
                    WHERE m.course_id = %s
                    ORDER BY CASE WHEN p.position_type = 'primary' THEN 0 ELSE 1 END,
                             p.target_rank, p.position_id, a.ability_id,
                             m.support_weight DESC, n.depth, n.node_name
                    """,
                    (course_id,),
                )
                rows = cursor.fetchall()
        result = []
        for row in rows:
            evidence = row.get("evidence_json")
            node_path = row.get("node_path_json")
            for key, value in (("evidence", evidence), ("node_path", node_path)):
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                    except Exception:
                        parsed = {} if key == "evidence" else []
                    if key == "evidence":
                        evidence = parsed
                    else:
                        node_path = parsed
            result.append(
                {
                    "mapping_id": int(row["mapping_id"]),
                    "course_id": row["course_id"],
                    "node_id": row["node_id"],
                    "node_name": row.get("node_name"),
                    "node_path": node_path if isinstance(node_path, list) else [],
                    "ability_id": int(row["ability_id"]),
                    "ability_name": row["ability_name"],
                    "ability_category": row.get("ability_category"),
                    "position_id": int(row["position_id"]),
                    "position_name": row["position_name"],
                    "position_type": row.get("position_type") or "related",
                    "support_weight": float(row.get("support_weight") or 0),
                    "support_level": row.get("support_level") or "medium",
                    "match_reason": row.get("match_reason"),
                    "evidence": evidence if isinstance(evidence, dict) else {},
                    "review_status": row.get("review_status") or "draft",
                    "reviewed_by": row.get("reviewed_by"),
                    "reviewed_at": self._to_str(row.get("reviewed_at")),
                    "created_at": self._to_str(row.get("created_at")),
                    "updated_at": self._to_str(row.get("updated_at")),
                }
            )
        return result

    def generate_course_ability_mapping_candidates(
        self,
        course_id: str,
        *,
        updated_by: Optional[int] = None,
        max_candidates_per_ability: int = 3,
        min_score: float = 0.24,
    ) -> Dict[str, Any]:
        """Generate draft ability-to-leaf-node mapping candidates for teacher review."""
        course_id = str(course_id or "").strip()
        if not course_id:
            raise ValueError("course_id is required")
        try:
            max_candidates = max(1, min(int(max_candidates_per_ability or 3), 5))
        except (TypeError, ValueError):
            max_candidates = 3
        try:
            threshold = max(0.05, min(float(min_score), 1.0))
        except (TypeError, ValueError):
            threshold = 0.24

        abilities = self.list_course_abilities(course_id)
        leaf_nodes = [
            node for node in self.list_course_node_binding_candidates(course_id)
            if node.get("is_leaf")
        ]
        existing_keys: Set[Tuple[int, str]] = {
            (int(item.get("ability_id") or 0), str(item.get("node_id") or ""))
            for item in self.list_course_ability_mappings(course_id)
        }

        candidates: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        for ability in abilities:
            ability_id = int(ability.get("ability_id") or 0)
            if not ability_id:
                continue
            scored_nodes = []
            for node in leaf_nodes:
                node_id = str(node.get("node_id") or "").strip()
                if not node_id or (ability_id, node_id) in existing_keys:
                    continue
                score_detail = self._score_ability_node_candidate(ability, node)
                if score_detail["score"] >= threshold:
                    scored_nodes.append((score_detail["score"], score_detail, node))
            scored_nodes.sort(key=lambda item: item[0], reverse=True)
            selected = scored_nodes[:max_candidates]
            if not selected:
                skipped.append({
                    "ability_id": ability_id,
                    "ability_name": ability.get("ability_name"),
                    "reason": "未找到达到阈值的叶子知识点候选",
                })
                continue
            for _, score_detail, node in selected:
                overlap = score_detail.get("overlap_terms") or []
                support_level = self._candidate_support_level(score_detail["score"])
                candidates.append({
                    "ability_id": ability_id,
                    "node_id": node["node_id"],
                    "support_level": support_level,
                    "review_status": "draft",
                    "match_reason": self._ability_candidate_reason(ability, node, score_detail),
                    "evidence": {
                        "source": "system_generated_ability_mapping_candidate",
                        "score": round(float(score_detail["score"]), 4),
                        "overlap_terms": overlap,
                        "position_name": ability.get("position_name"),
                        "ability_category": ability.get("ability_category"),
                        "requires_teacher_review": True,
                    },
                })

        if candidates:
            result = self.upsert_course_ability_mappings(
                course_id,
                candidates,
                updated_by=updated_by,
            )
        else:
            result = {"course_id": course_id, "saved": 0, "rejected": []}

        return {
            "course_id": course_id,
            "generated": int(result.get("saved") or 0),
            "rejected": result.get("rejected") or [],
            "skipped": skipped,
            "candidate_count": len(candidates),
        }

    def review_course_ability_mapping(
        self,
        mapping_id: int,
        *,
        review_status: str,
        support_level: Optional[str] = None,
        reviewed_by: Optional[int] = None,
    ) -> bool:
        """教师审核、确认或驳回能力映射。"""
        try:
            mapping_id_int = int(mapping_id)
        except (TypeError, ValueError):
            return False
        status = str(review_status or "").strip().lower()
        if status not in {"draft", "confirmed", "rejected"}:
            return False
        now = self._now()
        normalized_level = self._normalize_support_level(support_level) if support_level is not None else None
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                if normalized_level:
                    cursor.execute(
                        """
                        UPDATE course_ability_mappings
                        SET review_status = %s,
                            support_level = %s,
                            support_weight = %s,
                            reviewed_by = %s,
                            reviewed_at = %s,
                            updated_at = %s
                        WHERE mapping_id = %s
                        """,
                        (
                            status,
                            normalized_level,
                            self._support_weight(normalized_level),
                            reviewed_by,
                            now if status in {"confirmed", "rejected"} else None,
                            now,
                            mapping_id_int,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE course_ability_mappings
                        SET review_status = %s,
                            reviewed_by = %s,
                            reviewed_at = %s,
                            updated_at = %s
                        WHERE mapping_id = %s
                        """,
                        (
                            status,
                            reviewed_by,
                            now if status in {"confirmed", "rejected"} else None,
                            now,
                            mapping_id_int,
                        ),
                )
                return int(cursor.rowcount or 0) > 0

    def _candidate_support_level(self, score: float) -> str:
        if score >= 0.58:
            return "high"
        if score >= 0.36:
            return "medium"
        return "low"

    def _ability_candidate_reason(
        self,
        ability: Dict[str, Any],
        node: Dict[str, Any],
        score_detail: Dict[str, Any],
    ) -> str:
        overlap = score_detail.get("overlap_terms") or []
        overlap_text = "、".join(overlap[:5]) if overlap else "名称语义相近"
        path = " / ".join(node.get("node_path") or [node.get("node_name") or node.get("node_id")])
        return (
            f"系统依据能力名称、能力类别、岗位方向与叶子知识点路径生成候选："
            f"「{ability.get('ability_name')}」与「{path}」存在关键词匹配（{overlap_text}）。"
            "该关系仅为候选，需教师确认后才可发布。"
        )

    def _score_ability_node_candidate(self, ability: Dict[str, Any], node: Dict[str, Any]) -> Dict[str, Any]:
        name_terms = self._candidate_terms(ability.get("ability_name"))
        context_terms = self._candidate_terms(
            ability.get("ability_category"),
            ability.get("position_name"),
            *(self._flatten_candidate_evidence(ability.get("evidence"))[:8]),
        )
        ability_terms = set(name_terms) | set(context_terms)
        node_name_terms = self._candidate_terms(node.get("node_name"))
        node_terms = set(node_name_terms) | self._candidate_terms(" ".join(node.get("node_path") or []))
        if not ability_terms or not node_terms:
            return {"score": 0.0, "overlap_terms": []}
        name_specific_matches = self._candidate_specific_matches(name_terms, node_name_terms)
        if not name_specific_matches:
            return {"score": 0.0, "overlap_terms": []}
        overlap = sorted(ability_terms & node_terms)
        contain_matches = sorted(
            term for term in ability_terms
            if len(term) >= 2 and any(term in node_term or node_term in term for node_term in node_terms if len(node_term) >= 2)
        )
        effective_overlap = sorted(set(overlap + contain_matches + name_specific_matches))
        jaccard = len(overlap) / max(len(ability_terms | node_terms), 1)
        contain_score = min(len(contain_matches) / max(len(ability_terms), 1), 1.0)
        prefix_score = self._candidate_prefix_score(ability_terms, node_terms)
        specific_score = min(len(name_specific_matches) / max(len(name_terms), 1), 1.0)
        score = min(1.0, 0.35 * jaccard + 0.25 * contain_score + 0.10 * prefix_score + 0.30 * specific_score)
        return {
            "score": score,
            "overlap_terms": effective_overlap,
        }

    def _candidate_specific_matches(self, ability_name_terms: Set[str], node_terms: Set[str]) -> List[str]:
        matches = []
        for term in ability_name_terms:
            is_specific = len(term) >= 4 or bool(re.search(r"[a-z0-9+#]", term))
            if not is_specific:
                continue
            if term in node_terms or any(
                len(node_term) >= 2 and (term in node_term or node_term in term)
                for node_term in node_terms
            ):
                matches.append(term)
        return sorted(set(matches))

    def _candidate_prefix_score(self, ability_terms: Set[str], node_terms: Set[str]) -> float:
        if not ability_terms or not node_terms:
            return 0.0
        hits = 0
        for ability_term in ability_terms:
            if len(ability_term) < 3:
                continue
            if any(
                len(node_term) >= 3 and (
                    ability_term[:3] == node_term[:3]
                    or ability_term[-3:] == node_term[-3:]
                )
                for node_term in node_terms
            ):
                hits += 1
        return min(hits / max(len(ability_terms), 1), 1.0)

    def _candidate_terms(self, *values: Any) -> Set[str]:
        terms: Set[str] = set()
        stopwords = {
            "and", "or", "the", "with", "for", "of", "to", "in", "on",
            "能力", "岗位", "课程", "知识", "知识点", "基础", "掌握", "应用", "相关", "进行", "实现",
        }
        for value in values:
            text = str(value or "").strip().lower()
            if not text:
                continue
            for token in re.findall(r"[a-z0-9+#._-]{2,}|[\u4e00-\u9fff]{2,}", text):
                normalized = token.strip("._-")
                if not normalized or normalized in stopwords:
                    continue
                terms.add(normalized)
                if re.search(r"[\u4e00-\u9fff]", normalized) and len(normalized) >= 4:
                    for size in (2, 3, 4):
                        for index in range(0, len(normalized) - size + 1):
                            piece = normalized[index:index + size]
                            if piece not in stopwords:
                                terms.add(piece)
        return terms

    def _flatten_candidate_evidence(self, value: Any) -> List[str]:
        flattened: List[str] = []
        if isinstance(value, dict):
            for item in value.values():
                flattened.extend(self._flatten_candidate_evidence(item))
        elif isinstance(value, list):
            for item in value:
                flattened.extend(self._flatten_candidate_evidence(item))
        elif value is not None:
            text = str(value).strip()
            if text:
                flattened.append(text)
        return flattened

    def _safe_ratio(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(float(numerator) / float(denominator), 4)

    def _score_from_ratio(self, numerator: int, denominator: int) -> float:
        return round(self._safe_ratio(numerator, denominator) * 100, 2)

    def evaluate_course_runtime(
        self,
        course_id: str,
        *,
        window_days: int = 30,
        min_quiz_attempts: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """按需求文档五个角度评估课程发布后的运行状态。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return None
        window_days = max(1, min(int(window_days or 30), 365))
        since_time = datetime.now() - timedelta(days=window_days)

        def load_json(value: Any, default: Any) -> Any:
            if value is None:
                return default
            if isinstance(value, (dict, list)):
                return value
            try:
                return json.loads(value)
            except Exception:
                return default

        def clamp_score(value: Optional[float]) -> float:
            if value is None:
                return 0.0
            return round(max(0.0, min(float(value), 100.0)), 2)

        def chapter_key(path: List[str]) -> str:
            return str(path[0]) if path else "未归属章节"

        def node_description(payload: Any) -> str:
            if not isinstance(payload, dict):
                return ""
            for key in ("description", "desc", "objective", "learning_objective", "summary"):
                text = str(payload.get(key) or "").strip()
                if text:
                    return text
            return ""

        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT course_id, course_name, lifecycle_status, published_at, published_by
                    FROM courses
                    WHERE course_id = %s
                    LIMIT 1
                    """,
                    (course_id,),
                )
                course = cursor.fetchone()
                if not course:
                    return None

                cursor.execute(
                    """
                    SELECT n.node_id, n.node_name, n.node_path_json, n.depth,
                           n.parent_node_id, n.payload_json,
                           CASE WHEN NOT EXISTS (
                               SELECT 1 FROM course_nodes child
                               WHERE child.course_id = n.course_id
                                 AND child.parent_node_id = n.node_id
                               LIMIT 1
                           ) THEN 1 ELSE 0 END AS is_leaf
                    FROM course_nodes n
                    WHERE n.course_id = %s
                    ORDER BY n.depth, n.node_name, n.node_id
                    """,
                    (course_id,),
                )
                node_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT resource_id, node_id, resource_path, resource_type, title,
                           resource_source, quality_status, review_status, is_enabled,
                           is_deleted, payload_json
                    FROM resources
                    WHERE course_id = %s
                    ORDER BY node_id, resource_id
                    """,
                    (course_id,),
                )
                resource_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT node_id,
                           COUNT(*) AS event_count,
                           COUNT(DISTINCT username) AS learner_count,
                           SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) AS click_count,
                           SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS completed_count,
                           AVG(progress_percent) AS avg_progress_percent,
                           SUM(duration_seconds) AS total_duration_seconds,
                           MAX(occurred_at) AS last_event_at
                    FROM resource_learning_events
                    WHERE course_id = %s
                      AND occurred_at >= %s
                    GROUP BY node_id
                    """,
                    (course_id, since_time),
                )
                resource_event_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT node_id,
                           COUNT(*) AS quiz_attempt_count,
                           COUNT(DISTINCT COALESCE(username, CAST(user_id AS CHAR))) AS participant_count,
                           AVG(CASE WHEN total > 0 THEN score / total * 100 ELSE NULL END) AS avg_quiz_percent
                    FROM quiz_attempts
                    WHERE course_id = %s
                      AND created_at >= %s
                    GROUP BY node_id
                    """,
                    (course_id, since_time),
                )
                quiz_rows = {
                    str(row["node_id"]): {
                        "quiz_attempt_count": int(row.get("quiz_attempt_count") or 0),
                        "participant_count": int(row.get("participant_count") or 0),
                        "avg_quiz_percent": float(row["avg_quiz_percent"]) if row.get("avg_quiz_percent") is not None else None,
                    }
                    for row in cursor.fetchall()
                }

                cursor.execute(
                    """
                    SELECT username, payload_json, updated_at
                    FROM user_states
                    WHERE username LIKE %s
                    """,
                    (f"{QUIZ_DEFINITION_STATE_PREFIX}{course_id}::%",),
                )
                quiz_definition_state_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT node_id, COUNT(DISTINCT username) AS student_count,
                           AVG(mastery_score) AS avg_mastery,
                           AVG(progress) AS avg_progress,
                           AVG(study_duration_minutes) AS avg_study_minutes
                    FROM twin_profile_nodes
                    WHERE course_id = %s
                    GROUP BY node_id
                    """,
                    (course_id,),
                )
                mastery_rows = {
                    str(row["node_id"]): {
                        "student_count": int(row.get("student_count") or 0),
                        "avg_mastery": float(row["avg_mastery"]) if row.get("avg_mastery") is not None else None,
                        "avg_progress": float(row["avg_progress"]) if row.get("avg_progress") is not None else None,
                        "avg_study_minutes": float(row["avg_study_minutes"]) if row.get("avg_study_minutes") is not None else None,
                    }
                    for row in cursor.fetchall()
                }

                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT learner) AS learner_count
                    FROM (
                        SELECT username AS learner FROM twin_profile_nodes
                        WHERE course_id = %s AND username IS NOT NULL
                        UNION
                        SELECT username AS learner FROM quiz_attempts
                        WHERE course_id = %s AND username IS NOT NULL
                        UNION
                        SELECT s.student_username AS learner
                        FROM homework_assignments a
                        JOIN homework_submissions s ON s.assignment_id = a.id
                        WHERE a.course_id = %s AND s.student_username IS NOT NULL
                    ) learners
                    """,
                    (course_id, course_id, course_id),
                )
                class_row = cursor.fetchone() or {}
                observed_class_size = int(class_row.get("learner_count") or 0)

                cursor.execute(
                    """
                    SELECT a.id, a.title, a.assignment_type, a.status, a.node_id,
                           a.node_name, a.node_path_json, a.chapter_context,
                           a.total_score, COUNT(DISTINCT s.student_username) AS submitted_count,
                           AVG(CASE WHEN a.total_score > 0
                                THEN COALESCE(s.teacher_score, s.ai_score) / a.total_score * 100
                                ELSE NULL END) AS avg_homework_percent
                    FROM homework_assignments a
                    LEFT JOIN homework_submissions s ON s.assignment_id = a.id
                    WHERE a.course_id = %s
                      AND COALESCE(a.status, 'draft') = 'published'
                    GROUP BY a.id, a.title, a.assignment_type, a.status, a.node_id,
                             a.node_name, a.node_path_json, a.chapter_context, a.total_score
                    ORDER BY a.created_at DESC
                    """,
                    (course_id,),
                )
                homework_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT node_id,
                           COUNT(DISTINCT assignment_id) AS assignment_count,
                           AVG(confidence) AS avg_confidence
                    FROM homework_assignment_knowledge_points
                    WHERE course_id = %s
                      AND confirmed_by_teacher = 1
                    GROUP BY node_id
                    """,
                    (course_id,),
                )
                homework_coverage_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT m.mapping_id, m.node_id, m.ability_id, m.support_level,
                           m.support_weight, m.review_status, a.ability_name,
                           a.demand_level, a.support_level AS ability_demand_level,
                           p.position_id, p.position_name, p.position_type, p.target_rank
                    FROM career_abilities a
                    JOIN career_positions p ON p.position_id = a.position_id
                    LEFT JOIN course_ability_mappings m
                      ON m.ability_id = a.ability_id
                     AND m.course_id = p.course_id
                     AND m.review_status = 'confirmed'
                    WHERE p.course_id = %s
                    ORDER BY CASE WHEN p.position_type = 'primary' THEN 0 ELSE 1 END,
                             p.target_rank, p.position_id, a.ability_id, m.mapping_id
                    """,
                    (course_id,),
                )
                ability_mapping_rows = cursor.fetchall()

        all_nodes: List[Dict[str, Any]] = []
        leaf_rows: List[Dict[str, Any]] = []
        for row in node_rows:
            node_path = load_json(row.get("node_path_json"), [])
            payload = load_json(row.get("payload_json"), {})
            normalized = {
                "node_id": str(row["node_id"]),
                "node_name": str(row.get("node_name") or row["node_id"]),
                "node_path": node_path if isinstance(node_path, list) else [],
                "depth": int(row.get("depth") or 0),
                "parent_node_id": row.get("parent_node_id"),
                "payload": payload,
                "is_leaf": int(row.get("is_leaf") or 0) == 1,
            }
            all_nodes.append(normalized)
            if normalized["is_leaf"]:
                leaf_rows.append(normalized)

        leaf_ids = {row["node_id"] for row in leaf_rows}
        resources_by_node: Dict[str, List[Dict[str, Any]]] = {}
        valid_resources_by_node: Dict[str, List[Dict[str, Any]]] = {}
        resource_quality_issues: List[Dict[str, Any]] = []
        resource_events_by_node: Dict[str, Dict[str, Any]] = {
            str(row.get("node_id") or ""): {
                "event_count": int(row.get("event_count") or 0),
                "learner_count": int(row.get("learner_count") or 0),
                "click_count": int(row.get("click_count") or 0),
                "completed_count": int(row.get("completed_count") or 0),
                "avg_progress_percent": round(float(row.get("avg_progress_percent") or 0), 2),
                "total_duration_seconds": int(row.get("total_duration_seconds") or 0),
                "last_event_at": self._to_str(row.get("last_event_at")),
            }
            for row in resource_event_rows
        }
        homework_coverage_by_node: Dict[str, Dict[str, Any]] = {
            str(row.get("node_id") or ""): {
                "assignment_count": int(row.get("assignment_count") or 0),
                "avg_confidence": round(float(row.get("avg_confidence") or 0), 2),
            }
            for row in homework_coverage_rows
        }
        published_quiz_definitions_by_node = published_definition_index_from_state_rows(
            quiz_definition_state_rows,
            course_id,
        )
        for row in resource_rows:
            node_id = str(row.get("node_id") or "")
            resources_by_node.setdefault(node_id, [])
            item = {
                "resource_id": int(row.get("resource_id") or 0),
                "node_id": node_id,
                "resource_path": str(row.get("resource_path") or ""),
                "title": str(row.get("title") or row.get("resource_path") or ""),
                "resource_type": row.get("resource_type"),
                "resource_source": row.get("resource_source") or "local",
                "quality_status": row.get("quality_status") or "unchecked",
                "review_status": row.get("review_status") or "enabled",
                "is_enabled": bool(row.get("is_enabled")),
                "is_deleted": bool(row.get("is_deleted")),
            }
            resources_by_node[node_id].append(item)

        for node_id, items in resources_by_node.items():
            seen_keys: set[str] = set()
            for item in items:
                key = " ".join((item["title"] or item["resource_path"]).strip().lower().split())
                is_duplicate = bool(key and key in seen_keys)
                if key:
                    seen_keys.add(key)
                invalid_quality = str(item["quality_status"]).lower() in {
                    "failed", "invalid", "broken", "inaccessible", "duplicate", "mismatch"
                }
                is_valid = (
                    item["is_enabled"]
                    and not item["is_deleted"]
                    and str(item["review_status"]).lower() == "enabled"
                    and not invalid_quality
                    and not is_duplicate
                )
                if is_valid:
                    valid_resources_by_node.setdefault(node_id, []).append(item)
                else:
                    node = next((n for n in leaf_rows if n["node_id"] == node_id), None)
                    resource_quality_issues.append({
                        "node_id": node_id,
                        "node_name": node["node_name"] if node else node_id,
                        "resource_id": item["resource_id"],
                        "resource_title": item["title"],
                        "reason": "资源被禁用、未审核通过、质量状态异常或重复",
                        "suggested_action": "教师复核资源可访问性、匹配度和是否启用",
                    })

        active_learners = max(observed_class_size, 1)
        required_participants = max(1, min(10, int(active_learners * 0.3 + 0.9999)))
        if min_quiz_attempts and min_quiz_attempts > required_participants:
            required_participants = min(min_quiz_attempts, active_learners)

        homework_by_chapter: Dict[str, List[Dict[str, Any]]] = {}
        chapter_practice_gaps: List[Dict[str, Any]] = []
        chapter_practice_stats: List[Dict[str, Any]] = []
        for row in homework_rows:
            path = load_json(row.get("node_path_json"), [])
            path = path if isinstance(path, list) else []
            assignment_type = str(row.get("assignment_type") or "").lower()
            is_practice = assignment_type in {"subjective", "code", "coding"}
            chapter = str(row.get("chapter_context") or chapter_key(path))
            submitted_count = int(row.get("submitted_count") or 0)
            completion_rate = self._safe_ratio(submitted_count, active_learners)
            avg_homework_percent = (
                float(row["avg_homework_percent"]) if row.get("avg_homework_percent") is not None else None
            )
            homework_item = {
                "assignment_id": row["id"],
                "title": row.get("title"),
                "assignment_type": assignment_type,
                "node_id": str(row.get("node_id") or ""),
                "node_name": row.get("node_name"),
                "node_path": path,
                "chapter": chapter,
                "is_chapter_practice": is_practice,
                "submitted_count": submitted_count,
                "completion_rate": completion_rate,
                "avg_homework_percent": round(avg_homework_percent, 2) if avg_homework_percent is not None else None,
            }
            if is_practice:
                homework_by_chapter.setdefault(chapter, []).append(homework_item)

        chapters = sorted({chapter_key(row["node_path"]) for row in leaf_rows})
        for chapter in chapters:
            items = homework_by_chapter.get(chapter, [])
            published_count = len(items)
            submitted_count = sum(item["submitted_count"] for item in items)
            avg_completion = (
                round(sum(item["completion_rate"] for item in items) / published_count, 4)
                if published_count else 0.0
            )
            scored_items = [item["avg_homework_percent"] for item in items if item["avg_homework_percent"] is not None]
            avg_score = round(sum(scored_items) / len(scored_items), 2) if scored_items else None
            stat = {
                "chapter": chapter,
                "published_subjective_or_code_assignments": published_count,
                "submitted_count": submitted_count,
                "completion_rate": avg_completion,
                "avg_homework_percent": avg_score,
            }
            chapter_practice_stats.append(stat)
            if published_count <= 0:
                chapter_practice_gaps.append({
                    **stat,
                    "gap_type": "missing_chapter_practice",
                    "reason": "该章节没有已发布的主观题或代码题章节实践证据",
                    "suggested_action": "补充章节主观题或代码题，用于章节综合实践能力评估",
                })
            elif avg_completion < 0.5:
                chapter_practice_gaps.append({
                    **stat,
                    "gap_type": "low_completion",
                    "reason": "章节作业已发布但学生完成率低于 50%",
                    "suggested_action": "提醒学生完成作业，暂不直接判定课程安排有问题",
                })

        confirmed_mapping_by_node: Dict[str, List[Dict[str, Any]]] = {}
        ability_map: Dict[int, Dict[str, Any]] = {}
        for row in ability_mapping_rows:
            ability_id = int(row["ability_id"])
            ability = ability_map.setdefault(
                ability_id,
                {
                    "ability_id": ability_id,
                    "ability_name": row.get("ability_name"),
                    "demand_level": float(row["demand_level"]) if row.get("demand_level") is not None else None,
                    "ability_demand_level": row.get("ability_demand_level"),
                    "position_id": int(row["position_id"]),
                    "position_name": row.get("position_name"),
                    "position_type": row.get("position_type") or "related",
                    "target_rank": int(row.get("target_rank") or 0),
                    "mappings": [],
                },
            )
            if row.get("mapping_id") is not None:
                mapping = {
                    "mapping_id": int(row["mapping_id"]),
                    "node_id": str(row.get("node_id") or ""),
                    "support_level": row.get("support_level") or "medium",
                    "support_weight": float(row.get("support_weight") or self._support_weight(row.get("support_level"))),
                }
                ability["mappings"].append(mapping)
                confirmed_mapping_by_node.setdefault(mapping["node_id"], []).append({
                    "ability_id": ability_id,
                    "ability_name": ability["ability_name"],
                    "support_weight": mapping["support_weight"],
                })

        total_leaf_nodes = len(leaf_rows)
        structure_issues: List[Dict[str, Any]] = []
        resource_gaps: List[Dict[str, Any]] = []
        assessment_gaps: List[Dict[str, Any]] = []
        risk_nodes: List[Dict[str, Any]] = []
        chapter_risks: List[Dict[str, Any]] = []
        valid_resource_nodes = 0
        valid_quiz_nodes = 0
        valid_assessment_nodes = 0
        complete_structure_nodes = 0
        resource_event_nodes = 0
        resource_clicked_nodes = 0
        resource_completed_nodes = 0
        resource_progress_values: List[float] = []
        mastery_values: List[float] = []
        risk_by_chapter: Dict[str, Dict[str, int]] = {}

        chapter_study_values: Dict[str, List[float]] = {}
        for node in leaf_rows:
            mastery_stats = mastery_rows.get(node["node_id"], {})
            avg_study = mastery_stats.get("avg_study_minutes")
            if avg_study is not None:
                chapter_study_values.setdefault(chapter_key(node["node_path"]), []).append(float(avg_study))
        chapter_study_avg = {
            chapter: sum(values) / len(values)
            for chapter, values in chapter_study_values.items()
            if values
        }

        for node in leaf_rows:
            node_id = node["node_id"]
            node_name = node["node_name"]
            node_path = node["node_path"]
            chapter = chapter_key(node_path)
            valid_resource_count = len(valid_resources_by_node.get(node_id, []))
            resource_count = len(resources_by_node.get(node_id, []))
            resource_event_stats = resource_events_by_node.get(node_id, {})
            resource_event_count = int(resource_event_stats.get("event_count") or 0)
            resource_click_count = int(resource_event_stats.get("click_count") or 0)
            resource_completed_count = int(resource_event_stats.get("completed_count") or 0)
            resource_avg_progress = resource_event_stats.get("avg_progress_percent")
            homework_coverage = homework_coverage_by_node.get(node_id, {})
            quiz_stats = quiz_rows.get(node_id, {})
            quiz_participants = int(quiz_stats.get("participant_count") or 0)
            quiz_attempt_count = int(quiz_stats.get("quiz_attempt_count") or 0)
            avg_quiz_percent = quiz_stats.get("avg_quiz_percent")
            published_quiz_definition = published_quiz_definitions_by_node.get(node_id)
            has_published_quiz_definition = published_quiz_definition is not None
            quiz_valid = quiz_participants >= required_participants
            ability_support_count = len(confirmed_mapping_by_node.get(node_id, []))
            mastery_stats = mastery_rows.get(node_id, {})
            avg_mastery = mastery_stats.get("avg_mastery")
            avg_study_minutes = mastery_stats.get("avg_study_minutes")

            if valid_resource_count > 0:
                valid_resource_nodes += 1
            else:
                resource_gaps.append({
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_path": node_path,
                    "resource_count": resource_count,
                    "valid_resource_count": valid_resource_count,
                    "reason": "该叶子知识点没有可访问、未重复且已启用的有效资源",
                    "suggested_action": "补充或重新审核 B 站、YouTube、CSDN、本地课件等资源",
                })
            if resource_event_count > 0:
                resource_event_nodes += 1
            if resource_click_count > 0:
                resource_clicked_nodes += 1
            if resource_completed_count > 0:
                resource_completed_nodes += 1
            if isinstance(resource_avg_progress, (int, float)) and float(resource_avg_progress) > 0:
                resource_progress_values.append(float(resource_avg_progress))

            if quiz_valid:
                valid_quiz_nodes += 1
            if quiz_valid:
                valid_assessment_nodes += 1
            else:
                assessment_gaps.append({
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_path": node_path,
                    "quiz_participant_count": quiz_participants,
                    "required_participant_count": required_participants,
                    "quiz_attempt_count": quiz_attempt_count,
                    "has_published_quiz_definition": has_published_quiz_definition,
                    "published_quiz_definition_id": published_quiz_definition.get("definition_id") if published_quiz_definition else None,
                    "confirmed_homework_coverage_count": int(homework_coverage.get("assignment_count") or 0),
                    "reason": "已发布小测但作答证据不足" if has_published_quiz_definition else "知识点缺少已发布小测入口，尚不足以支撑强诊断",
                    "suggested_action": "推动学生完成已发布小测，形成有效作答证据" if has_published_quiz_definition else "先发布知识点小测；章节作业默认只作为章节实践证据，需等教师确认覆盖知识点后才作为辅助证据",
                })

            missing_categories: List[str] = []
            if not node_name.strip():
                missing_categories.append("名称")
            if not node_description(node["payload"]):
                missing_categories.append("描述")
            if valid_resource_count <= 0:
                missing_categories.append("资源绑定")
            if not has_published_quiz_definition:
                missing_categories.append("测评入口")
            if ability_support_count <= 0:
                missing_categories.append("能力支撑")
            if len(missing_categories) < 2:
                complete_structure_nodes += 1
            else:
                structure_issues.append({
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_path": node_path,
                    "issue_type": "incomplete_knowledge_point",
                    "missing_categories": missing_categories,
                    "reason": "叶子知识点缺少两类及以上关键信息",
                    "suggested_action": "补充节点说明、资源、测评入口或职业能力支撑关系",
                })

            low_learning_result = (
                (avg_quiz_percent is not None and float(avg_quiz_percent) < 60)
            )
            broad_name_hint = any(token in node_name for token in ("、", "及", "与", "和", "/", "，", ",", "与分析"))
            if broad_name_hint and low_learning_result:
                structure_issues.append({
                    "node_id": node_id,
                    "node_name": node_name,
                    "node_path": node_path,
                    "issue_type": "coarse_granularity_candidate",
                    "reason": "知识点名称可能覆盖多个技能动作，且测验或作业表现低于 60 分",
                    "suggested_action": "由教师判断是否拆分为更细的叶子知识点",
                })

            if avg_mastery is not None:
                mastery_values.append(float(avg_mastery))
            if quiz_valid and avg_mastery is not None:
                mastery_risk = max(0.0, 1.0 - clamp_score(float(avg_mastery)) / 100.0)
                quiz_risk = max(0.0, 1.0 - clamp_score(avg_quiz_percent) / 100.0) if avg_quiz_percent is not None else 0.5
                chapter_avg_study = chapter_study_avg.get(chapter)
                study_burden = (
                    1.0
                    if chapter_avg_study and avg_study_minutes and avg_study_minutes > chapter_avg_study * 1.5
                    else 0.0
                )
                k_risk = round(0.50 * mastery_risk + 0.35 * quiz_risk + 0.15 * study_burden, 4)
                risk_by_chapter.setdefault(chapter, {"total": 0, "high": 0})
                risk_by_chapter[chapter]["total"] += 1
                if k_risk >= 0.60:
                    risk_by_chapter[chapter]["high"] += 1
                    risk_nodes.append({
                        "node_id": node_id,
                        "node_name": node_name,
                        "node_path": node_path,
                        "risk_level": "high",
                        "k_risk": k_risk,
                        "avg_mastery": round(float(avg_mastery), 2),
                        "avg_quiz_percent": round(float(avg_quiz_percent), 2) if avg_quiz_percent is not None else None,
                        "avg_study_minutes": round(float(avg_study_minutes), 2) if avg_study_minutes is not None else None,
                    "reason": "知识点掌握度和测验正确率综合风险达到高风险阈值",
                    "suggested_action": "复核讲解重点、示例资源、小测和章节主观题/代码题支撑",
                    })

        if total_leaf_nodes <= 0:
            structure_issues.append({
                "node_id": None,
                "node_name": "课程结构",
                "node_path": [],
                "issue_type": "empty_structure",
                "reason": "课程没有可学习的叶子知识点",
                "suggested_action": "先补充章节、小节和叶子知识点后再发布课程底座",
            })

        for chapter, stat in risk_by_chapter.items():
            total = int(stat.get("total") or 0)
            high = int(stat.get("high") or 0)
            chapter_risk_rate = self._safe_ratio(high, total)
            if total > 0 and chapter_risk_rate >= 0.4:
                chapter_risks.append({
                    "chapter": chapter,
                    "high_risk_node_count": high,
                    "evidence_sufficient_node_count": total,
                    "chapter_risk_rate": chapter_risk_rate,
                    "reason": "章节内高风险知识点占比达到 40%",
                    "suggested_action": "将该章节列为课程维护重点，补充讲解、示例、小测或代码题",
                })

        ability_gaps: List[Dict[str, Any]] = []
        ability_results: List[Dict[str, Any]] = []
        ability_supported_count = 0
        for ability in ability_map.values():
            mappings = ability["mappings"]
            if not mappings:
                ability_gaps.append({
                    "ability_id": ability["ability_id"],
                    "ability_name": ability["ability_name"],
                    "position_id": ability["position_id"],
                    "position_name": ability["position_name"],
                    "position_type": ability["position_type"],
                    "gap_type": "missing_mapping",
                    "a_sup": None,
                    "reason": "该职业能力没有经教师确认的叶子知识点支撑关系",
                    "suggested_action": "进入能力缺口补知识点流程，由大模型给出候选知识点，教师决定是否新增或忽略",
                })
                ability_results.append({**ability, "a_sup": None, "support_status": "mapping_gap"})
                continue
            denominator = sum(float(item.get("support_weight") or 0) for item in mappings)
            numerator = 0.0
            missing_mastery_nodes: List[str] = []
            for mapping in mappings:
                mastery = mastery_rows.get(mapping["node_id"], {}).get("avg_mastery")
                if mastery is None:
                    missing_mastery_nodes.append(mapping["node_id"])
                    node_mastery = 0.0
                else:
                    node_mastery = clamp_score(float(mastery))
                numerator += float(mapping.get("support_weight") or 0) * node_mastery
            a_sup = round(numerator / denominator, 2) if denominator > 0 else None
            is_primary_high_demand = (
                ability["position_type"] == "primary"
                and (
                    str(ability.get("ability_demand_level") or "").lower() == "high"
                    or (ability.get("demand_level") is not None and float(ability["demand_level"]) >= 7)
                )
            )
            if a_sup is not None and a_sup >= 60:
                ability_supported_count += 1
            if denominator <= 0:
                ability_gaps.append({
                    "ability_id": ability["ability_id"],
                    "ability_name": ability["ability_name"],
                    "position_id": ability["position_id"],
                    "position_name": ability["position_name"],
                    "position_type": ability["position_type"],
                    "gap_type": "zero_weight_mapping",
                    "a_sup": None,
                    "reason": "能力映射权重分母为 0，无法计算支撑达成",
                    "suggested_action": "教师调整高/中/低支撑强度后重新发布",
                })
            elif is_primary_high_demand and a_sup < 60:
                ability_gaps.append({
                    "ability_id": ability["ability_id"],
                    "ability_name": ability["ability_name"],
                    "position_id": ability["position_id"],
                    "position_name": ability["position_name"],
                    "position_type": ability["position_type"],
                    "gap_type": "primary_high_demand_low_support",
                    "a_sup": a_sup,
                    "missing_mastery_nodes": missing_mastery_nodes,
                    "reason": "主要岗位高需求能力的课程支撑达成低于 60",
                    "suggested_action": "复核能力-知识点支撑关系，补充资源、练习、代码题或候选知识点草稿",
                })
            ability_results.append({
                **ability,
                "a_sup": a_sup,
                "support_status": "sufficient" if a_sup is not None and a_sup >= 60 else "risk",
                "missing_mastery_nodes": missing_mastery_nodes,
            })

        structure_score = self._score_from_ratio(complete_structure_nodes, total_leaf_nodes)
        resource_coverage_score = self._score_from_ratio(valid_resource_nodes, total_leaf_nodes)
        resource_engagement_score = self._score_from_ratio(resource_event_nodes, valid_resource_nodes)
        published_quiz_definition_nodes = len(
            [node_id for node_id in leaf_ids if node_id in published_quiz_definitions_by_node]
        )
        if resource_event_nodes > 0:
            resource_score = round(resource_coverage_score * 0.70 + resource_engagement_score * 0.30, 2)
        else:
            resource_score = resource_coverage_score
        assessment_score = self._score_from_ratio(valid_assessment_nodes, total_leaf_nodes)
        mastery_score = round(sum(mastery_values) / len(mastery_values), 2) if mastery_values else 0.0
        ability_score = self._score_from_ratio(ability_supported_count, len(ability_map))
        resource_avg_progress_overall = (
            round(sum(resource_progress_values) / len(resource_progress_values), 2)
            if resource_progress_values else 0.0
        )
        course_health_score = round(
            0.20 * structure_score
            + 0.20 * resource_score
            + 0.20 * assessment_score
            + 0.25 * mastery_score
            + 0.15 * ability_score,
            2,
        )

        unavailable_metrics = [
            {
                "metric": "revisit_count_and_path_stagnation",
                "reason": "当前数据库未稳定沉淀重复访问次数和路径停滞记录，K_risk 暂用掌握度、测验正确率和学习时长负担计算",
                "required_data": "知识点访问日志、路径节点停滞状态、最近访问时间",
            },
        ]
        if resource_event_nodes <= 0:
            unavailable_metrics.append({
                "metric": "resource_learning_effectiveness",
                "reason": "当前时间窗口内没有资源学习事件，资源有效性只能按资源是否存在、是否启用和质量状态近似判断",
                "required_data": "资源点击、浏览进度和完成事件：course_id、node_id、resource_id、username、occurred_at",
            })

        action_items: List[Dict[str, Any]] = []
        if structure_issues:
            action_items.append({
                "type": "structure_issue",
                "priority": "high",
                "title": "补齐课程结构信息或拆分过粗知识点",
                "count": len(structure_issues),
            })
        if resource_gaps or resource_quality_issues:
            action_items.append({
                "type": "resource_gap_or_quality",
                "priority": "high" if self._safe_ratio(len(resource_gaps), max(total_leaf_nodes, 1)) >= 0.3 else "medium",
                "title": "补充、替换或重新审核知识点资源",
                "count": len(resource_gaps) + len(resource_quality_issues),
            })
        if assessment_gaps or chapter_practice_gaps:
            action_items.append({
                "type": "assessment_evidence_gap",
                "priority": "medium",
                "title": "补充知识点小测或章节主观题/代码题证据",
                "count": len(assessment_gaps) + len(chapter_practice_gaps),
            })
        if risk_nodes or chapter_risks:
            action_items.append({
                "type": "course_runtime_risk",
                "priority": "high",
                "title": "优先维护高风险知识点或章节",
                "count": len(risk_nodes) + len(chapter_risks),
            })
        if ability_gaps:
            action_items.append({
                "type": "ability_support_gap",
                "priority": "high",
                "title": "复核职业能力支撑关系或补充候选知识点草稿",
                "count": len(ability_gaps),
            })
        if not action_items:
            action_items.append({
                "type": "healthy",
                "priority": "low",
                "title": "课程运行状态暂未发现需要优先处理的问题",
                "count": 0,
            })

        return {
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "lifecycle_status": course.get("lifecycle_status") or "draft",
            "published_at": self._to_str(course.get("published_at")),
            "published_by": course.get("published_by"),
            "formula_version": "course_runtime_v2",
            "window_days": window_days,
            "min_quiz_attempts": min_quiz_attempts,
            "class_size_source": "observed_active_learners",
            "observed_class_size": observed_class_size,
            "required_participant_count": required_participants,
            "metrics": {
                "total_nodes": len(all_nodes),
                "total_leaf_nodes": total_leaf_nodes,
                "structure_complete_nodes": complete_structure_nodes,
                "structure_score": structure_score,
                "valid_resource_nodes": valid_resource_nodes,
                "resource_coverage_rate": self._safe_ratio(valid_resource_nodes, total_leaf_nodes),
                "resource_event_nodes": resource_event_nodes,
                "resource_click_rate": self._safe_ratio(resource_clicked_nodes, valid_resource_nodes),
                "resource_completion_rate": self._safe_ratio(resource_completed_nodes, valid_resource_nodes),
                "resource_avg_progress_percent": resource_avg_progress_overall,
                "resource_score": resource_score,
                "published_quiz_definition_nodes": published_quiz_definition_nodes,
                "published_quiz_definition_coverage_rate": self._safe_ratio(published_quiz_definition_nodes, total_leaf_nodes),
                "valid_quiz_nodes": valid_quiz_nodes,
                "valid_assessment_nodes": valid_assessment_nodes,
                "assessment_coverage_rate": self._safe_ratio(valid_assessment_nodes, total_leaf_nodes),
                "assessment_score": assessment_score,
                "mastery_score": mastery_score,
                "total_abilities": len(ability_map),
                "supported_abilities": ability_supported_count,
                "ability_support_rate": self._safe_ratio(ability_supported_count, len(ability_map)),
                "ability_score": ability_score,
                "course_health_score": course_health_score,
            },
            "sections": {
                "structure_quality": {
                    "score": structure_score,
                    "issues": structure_issues,
                },
                "resource_coverage_and_effectiveness": {
                    "score": resource_score,
                    "resource_gaps": resource_gaps,
                    "resource_quality_issues": resource_quality_issues,
                    "resource_learning_events": resource_events_by_node,
                },
                "assessment_evidence_and_learning_effect": {
                    "score": assessment_score,
                    "knowledge_point_evidence_gaps": assessment_gaps,
                    "published_quiz_definitions_by_node": published_quiz_definitions_by_node,
                    "chapter_practice_stats": chapter_practice_stats,
                    "chapter_practice_gaps": chapter_practice_gaps,
                    "homework_coverage_by_node": homework_coverage_by_node,
                },
                "runtime_weak_points": {
                    "risk_nodes": risk_nodes,
                    "chapter_risks": chapter_risks,
                },
                "career_ability_support": {
                    "score": ability_score,
                    "ability_results": ability_results,
                    "ability_gaps": ability_gaps,
                },
            },
            "formulas": {
                "structure_score": "100 * 结构信息完整的叶子知识点数 / 叶子知识点总数；缺少名称、描述、资源、测评入口、能力支撑中的两类及以上即为不完整",
                "resource_coverage_rate": "有效资源覆盖率 R_cov = 有效资源数 >= RequiredResourceCount(k) 的叶子知识点数 / 叶子知识点总数，RequiredResourceCount(k)=1",
                "resource_click_rate": "资源触达率 R_click = 发生资源学习事件的叶子知识点数 / 有有效资源的叶子知识点数",
                "resource_completion_rate": "资源完成率 R_done = 发生完成事件的叶子知识点数 / 有有效资源的叶子知识点数",
                "assessment_coverage_rate": "测评覆盖率 Q_cov = 有效作答人数达到 min(10, 班级人数*30%) 的叶子知识点数 / 叶子知识点总数；小班按实际活跃人数折算",
                "chapter_practice_coverage": "章节实践覆盖 H_cov(ch)=1 表示章节存在已发布主观题或代码题；完成率低于 50% 只提示完成不足",
                "k_risk": "K_risk(k)=0.50*(1-Mastery(k)/100)+0.35*(1-QuizCorrect(k)/100)+0.15*StudyBurden(k)，当前缺少 Revisit 时不参与计算；K_risk>=0.60 标记高风险",
                "chapter_risk_rate": "ChapterRiskRate(ch)=章节内高风险知识点数 / 证据充分知识点数；>=40% 标记章节教学重点复核",
                "a_sup": "A_sup(a)=sum(w(k,a)*Mastery(k))/sum(w(k,a))，高/中/低支撑强度分别折算为 1.0/0.6/0.3；未经教师确认的映射不参与计算",
                "course_health_score": "0.20*structure_score + 0.20*resource_score + 0.20*assessment_score + 0.25*mastery_score + 0.15*ability_score",
            },
            "thresholds": {
                "resource_gap": "R_cov(k)=0",
                "quiz_valid_participants": f"有效作答人数 >= {required_participants}",
                "min_quiz_attempts": "兼容旧接口的最低作答人数下限；实际规则仍优先按班级人数 30% 或 10 人折算",
                "homework_low_completion": "章节作业完成率 < 50%",
                "knowledge_high_risk": "K_risk(k) >= 0.60",
                "chapter_risk": "ChapterRiskRate(ch) >= 40%",
                "ability_support_risk": "主要岗位高需求能力 A_sup(a) < 60",
                "ability_mapping_gap": "sum(w(k,a)) = 0 或没有教师确认映射",
            },
            "unavailable_metrics": unavailable_metrics,
            "action_items": action_items,
            "generated_at": self._to_str(datetime.now()),
        }

    def get_course_payload(self, course_id: str) -> Optional[Dict[str, Any]]:
        """获取课程完整JSON数据（从course_metadata的additional_data中读取）"""
        import time as _time
        _start = _time.time()
        
        course_id = str(course_id or "").strip()
        if not course_id:
            return None
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT additional_data FROM course_metadata WHERE course_id = %s ORDER BY metadata_id DESC LIMIT 1",
                    (course_id,)
                )
                row = cursor.fetchone()
        
        _query_time = _time.time() - _start
        
        if not row:
            return None
        try:
            data = row["additional_data"] if isinstance(row, dict) else row[0]
            if isinstance(data, str):
                import json as _json
                data = _json.loads(data)
            if isinstance(data, dict):
                # additional_data存储了{'root_name': ..., 'structure': {...}}
                structure = data.get('structure')
                if isinstance(structure, dict):
                    import logging
                    logging.info(f"⏱️  数据库查询耗时: {_query_time:.3f}秒")
                    return structure
                return data
            return None
        except Exception:
            return None

    def get_course_id_by_resource_path(self, resource_path: str) -> Optional[str]:
        """根据资源路径获取课程ID"""
        resource_path = str(resource_path or "").strip()
        if not resource_path:
            return None
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT course_id FROM resources
                    WHERE resource_path = %s
                    ORDER BY resource_id DESC LIMIT 1
                    """,
                    (resource_path,)
                )
                row = cursor.fetchone()
        if row:
            return str(row["course_id"] if isinstance(row, dict) else row[0])
        return None

    def list_learning_nodes_for_course(self, course_id: str) -> List[str]:
        """列出课程的所有学习节点名称"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DISTINCT node_name FROM course_nodes
                    WHERE course_id = %s AND node_name IS NOT NULL AND TRIM(node_name) <> ''
                    ORDER BY node_name
                    """,
                    (course_id,)
                )
                rows = cursor.fetchall()
        return [str(row["node_name"] if isinstance(row, dict) else row[0]) for row in rows]

    def list_course_node_binding_candidates(self, course_id: str) -> List[Dict[str, Any]]:
        course_id = str(course_id or "").strip()
        if not course_id:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT n.node_id, n.node_name, n.node_path_json,
                           CASE WHEN NOT EXISTS (
                               SELECT 1 FROM course_nodes child
                               WHERE child.course_id = n.course_id
                                 AND child.parent_node_id = n.node_id
                               LIMIT 1
                           ) THEN 1 ELSE 0 END AS is_leaf
                    FROM course_nodes n
                    WHERE n.course_id = %s
                    ORDER BY is_leaf DESC, n.depth DESC, n.node_name, n.node_id
                    """,
                    (course_id,),
                )
                rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            payload = dict(row) if isinstance(row, dict) else {}
            node_path_raw = payload.get("node_path_json")
            node_path: List[str] = []
            if isinstance(node_path_raw, str) and node_path_raw.strip():
                try:
                    parsed_path = json.loads(node_path_raw)
                    if isinstance(parsed_path, list):
                        node_path = [str(item) for item in parsed_path if str(item).strip()]
                except Exception:
                    node_path = []
            elif isinstance(node_path_raw, list):
                node_path = [str(item) for item in node_path_raw if str(item).strip()]
            result.append(
                {
                    "node_id": str(payload.get("node_id") or "").strip(),
                    "node_name": str(payload.get("node_name") or "").strip(),
                    "node_path": node_path,
                    "is_leaf": int(payload.get("is_leaf") or 0) == 1,
                }
            )
        return [item for item in result if item["node_id"]]

    def list_resources_for_node_name(self, course_id: str, node_name: str) -> List[str]:
        """列出节点的所有资源路径"""
        course_id = str(course_id or "").strip()
        node_name = str(node_name or "").strip()
        if not course_id or not node_name:
            return []
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT r.resource_path
                    FROM resources r
                    JOIN course_nodes n ON n.course_id = r.course_id AND n.node_id = r.node_id
                    WHERE r.course_id = %s AND n.node_name = %s
                      AND (r.is_deleted IS NULL OR r.is_deleted = 0)
                      AND (r.is_enabled IS NULL OR r.is_enabled = 1)
                    ORDER BY r.resource_id
                """, (course_id, node_name))
                rows = cursor.fetchall()
        return [str(row["resource_path"] if isinstance(row, dict) else row[0]) for row in rows if (row["resource_path"] if isinstance(row, dict) else row[0])]

    def record_quiz_attempt(self, *, username: Optional[str], user_id: Optional[int], course_id: Optional[str], node_id: Optional[str], score: float, total: float, passed: bool, extra_payload: Optional[Dict[str, Any]] = None) -> int:
        """记录测验尝试"""
        payload = {
            "username": username, "user_id": user_id,
            "course_id": course_id, "node_id": node_id,
            "score": score, "total": total, "passed": bool(passed),
            "extra": extra_payload or {},
        }
        now = self._now()
        # 确保quiz_attempts表存在
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quiz_attempts (
                        attempt_id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT, username VARCHAR(100),
                        course_id VARCHAR(100), node_id VARCHAR(200),
                        score DECIMAL(6,2), total DECIMAL(6,2),
                        passed TINYINT(1) DEFAULT 0,
                        payload_json JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user_id (user_id), INDEX idx_username (username)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                cursor.execute("""
                    INSERT INTO quiz_attempts
                    (user_id, username, course_id, node_id, score, total, passed, payload_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (user_id, username, course_id, node_id,
                      float(score or 0), float(total or 0),
                      1 if passed else 0, self._json(payload), now))
                return cursor.lastrowid or 0

    def soft_delete_resource(self, course_id: str, node_id: str, resource_path: str, deleted_by: Optional[str] = None) -> bool:
        """软删除资源（标记为已删除）"""
        course_id = str(course_id or "").strip()
        node_id = str(node_id or "").strip()
        resource_path = str(resource_path or "").strip()
        if not course_id or not node_id or not resource_path:
            return False
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE resources
                    SET is_deleted = 1, deleted_at = %s, deleted_by = %s, updated_at = %s
                    WHERE course_id = %s AND node_id = %s AND resource_path = %s
                      AND (is_deleted IS NULL OR is_deleted = 0)
                """, (now, deleted_by, now, course_id, node_id, resource_path))
                return cursor.rowcount > 0

    def restore_resource(self, course_id: str, node_id: str, resource_path: str) -> bool:
        """恢复已删除的资源"""
        course_id = str(course_id or "").strip()
        node_id = str(node_id or "").strip()
        resource_path = str(resource_path or "").strip()
        if not course_id or not node_id or not resource_path:
            return False
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE resources
                    SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL, updated_at = %s
                    WHERE course_id = %s AND node_id = %s AND resource_path = %s AND is_deleted = 1
                """, (now, course_id, node_id, resource_path))
                return cursor.rowcount > 0

    def list_deleted_resources(self, course_id: Optional[str] = None, node_id: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """列出已删除的资源（回收站）"""
        sql = """
            SELECT resource_id, course_id, node_id, resource_path, resource_type,
                   title, deleted_at, deleted_by, payload_json
            FROM resources WHERE is_deleted = 1
        """
        params: List[Any] = []
        if course_id:
            sql += " AND course_id = %s"
            params.append(str(course_id).strip())
        if node_id:
            sql += " AND node_id = %s"
            params.append(str(node_id).strip())
        sql += " ORDER BY deleted_at DESC"
        if limit:
            sql += " LIMIT %s"
            params.append(limit)
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
        result = []
        for row in rows:
            r = dict(row) if isinstance(row, dict) else {
                "resource_id": row[0], "course_id": row[1], "node_id": row[2],
                "resource_path": row[3], "resource_type": row[4], "title": row[5],
                "deleted_at": row[6], "deleted_by": row[7], "payload_json": row[8]
            }
            try:
                payload = r["payload_json"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
            except Exception:
                payload = {}
            result.append({
                "resource_id": r["resource_id"],
                "course_id": r["course_id"],
                "node_id": r["node_id"],
                "resource_path": r["resource_path"],
                "resource_type": r["resource_type"],
                "title": r["title"],
                "deleted_at": r["deleted_at"],
                "deleted_by": r["deleted_by"],
                "payload": payload,
            })
        return result

    def record_resource_learning_event(
        self,
        *,
        username: str,
        user_id: Optional[int],
        course_id: str,
        node_id: str,
        resource_id: Optional[int] = None,
        resource_path: Optional[str] = None,
        event_type: str,
        duration_seconds: int = 0,
        progress_percent: Optional[float] = None,
        is_completed: bool = False,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """记录资源学习事件，用于课程资源有效性和学生学习证据回流。"""
        username = str(username or "").strip()
        course_id = str(course_id or "").strip()
        node_id = str(node_id or "").strip()
        event_type = str(event_type or "").strip().lower()
        event_type_aliases = {
            "viewed": "view",
            "completed": "complete",
            "clicked": "click",
        }
        event_type = event_type_aliases.get(event_type, event_type)
        if not username or not course_id or not node_id or not event_type:
            raise ValueError("username, course_id, node_id and event_type are required")
        if event_type not in {"click", "view", "progress", "complete"}:
            raise ValueError("event_type must be click, view, progress or complete")
        try:
            duration_seconds = max(0, int(duration_seconds or 0))
        except (TypeError, ValueError):
            duration_seconds = 0
        if progress_percent is not None:
            try:
                progress_percent = max(0.0, min(float(progress_percent), 100.0))
            except (TypeError, ValueError):
                progress_percent = None
        if event_type == "complete":
            is_completed = True
            if progress_percent is None:
                progress_percent = 100.0
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO resource_learning_events
                    (username, user_id, course_id, node_id, resource_id, resource_path,
                     event_type, duration_seconds, progress_percent, is_completed,
                     occurred_at, payload_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        username,
                        user_id,
                        course_id,
                        node_id,
                        resource_id,
                        str(resource_path or "").strip() or None,
                        event_type,
                        duration_seconds,
                        progress_percent,
                        1 if is_completed else 0,
                        now,
                        self._json(payload or {}),
                        now,
                    ),
                )
                return int(cursor.lastrowid)

    def summarize_resource_learning_events(
        self,
        *,
        course_id: str,
        node_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按课程/知识点汇总资源学习事件。"""
        course_id = str(course_id or "").strip()
        if not course_id:
            return {"course_id": "", "event_count": 0, "node_summaries": []}
        clauses = ["course_id = %s"]
        params: List[Any] = [course_id]
        if node_id:
            clauses.append("node_id = %s")
            params.append(str(node_id).strip())
        if username:
            clauses.append("username = %s")
            params.append(str(username).strip())
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT node_id,
                           COUNT(*) AS event_count,
                           COUNT(DISTINCT username) AS learner_count,
                           SUM(CASE WHEN event_type = 'click' THEN 1 ELSE 0 END) AS click_count,
                           SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS completed_count,
                           AVG(progress_percent) AS avg_progress_percent,
                           SUM(duration_seconds) AS total_duration_seconds,
                           MAX(occurred_at) AS last_event_at
                    FROM resource_learning_events
                    WHERE {' AND '.join(clauses)}
                    GROUP BY node_id
                    ORDER BY node_id
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        summaries: List[Dict[str, Any]] = []
        total_events = 0
        for row in rows:
            event_count = int(row.get("event_count") or 0)
            total_events += event_count
            summaries.append(
                {
                    "node_id": row.get("node_id"),
                    "event_count": event_count,
                    "learner_count": int(row.get("learner_count") or 0),
                    "click_count": int(row.get("click_count") or 0),
                    "completed_count": int(row.get("completed_count") or 0),
                    "avg_progress_percent": round(float(row.get("avg_progress_percent") or 0), 2),
                    "total_duration_seconds": int(row.get("total_duration_seconds") or 0),
                    "last_event_at": self._to_str(row.get("last_event_at")),
                }
            )
        return {
            "course_id": course_id,
            "node_id": node_id,
            "username": username,
            "event_count": total_events,
            "node_summaries": summaries,
        }

    def list_fivee_effectiveness_records(
        self,
        *,
        course_id: Optional[str] = None,
        student_username: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """List 5E effectiveness records for teacher-side evidence summaries."""
        clauses: List[str] = []
        params: List[Any] = []
        clean_course_id = str(course_id or "").strip()
        clean_student = str(student_username or "").strip()
        if clean_course_id:
            clauses.append("course_id = %s")
            params.append(clean_course_id)
        if clean_student:
            clauses.append("(student_username = %s OR user_identifier = %s)")
            params.extend([clean_student, clean_student])
        limit = max(1, min(int(limit or 500), 2000))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT record_id, user_identifier, student_user_id, student_username,
                           course_id, node_id, session_id, stage,
                           interaction_count, valid_interaction_count,
                           completion_rate, quiz_score_before, quiz_score_after,
                           path_continue_rate, effectiveness_score,
                           payload_json, calculated_at, created_at
                    FROM fivee_effectiveness_records
                    {where}
                    ORDER BY calculated_at DESC, record_id DESC
                    LIMIT %s
                    """,
                    tuple([*params, limit]),
                )
                rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            payload = item.pop("payload_json", None)
            try:
                payload = json.loads(payload) if isinstance(payload, str) else (payload or {})
            except Exception:
                payload = {}
            item["payload"] = payload
            for key in (
                "completion_rate",
                "quiz_score_before",
                "quiz_score_after",
                "path_continue_rate",
                "effectiveness_score",
            ):
                if item.get(key) is not None:
                    item[key] = float(item[key])
            for key in ("calculated_at", "created_at"):
                item[key] = self._to_str(item.get(key))
            result.append(item)
        return result

    def list_intervention_completion_evidence(
        self,
        *,
        course_id: Optional[str] = None,
        student_username: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """List completed teacher intervention package records as learning evidence."""
        clean_course_id = str(course_id or "").strip()
        clean_student = str(student_username or "").strip()
        if not clean_student:
            return []
        clauses = [
            "r.student_username = %s",
            "r.status = 'completed'",
        ]
        params: List[Any] = [clean_student]
        if clean_course_id:
            clauses.append("(p.course_id = %s OR JSON_UNQUOTE(JSON_EXTRACT(p.payload_json, '$.diagnosis.course_id')) = %s)")
            params.extend([clean_course_id, clean_course_id])
        limit = max(1, min(int(limit or 500), 2000))
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT r.record_id, r.package_id, r.student_username,
                           r.status, r.score, r.feedback, r.started_at,
                           r.completed_at, r.payload_json AS record_payload_json,
                           r.created_at, r.updated_at,
                           p.teacher_username, p.course_id, p.package_title,
                           p.risk_level, p.diagnosis_report_id,
                           p.payload_json AS package_payload_json,
                           GROUP_CONCAT(
                               CONCAT_WS('|||FIELD|||',
                                   COALESCE(i.item_id, ''),
                                   COALESCE(i.item_type, ''),
                                   COALESCE(i.node_id, ''),
                                   COALESCE(i.reminder_text, ''),
                                   COALESCE(i.payload_json, '')
                               )
                               ORDER BY i.sequence_order ASC SEPARATOR '|||ITEM|||'
                           ) AS item_summary
                    FROM intervention_package_student_records r
                    JOIN intervention_packages p ON p.package_id = r.package_id
                    LEFT JOIN intervention_package_items i ON i.package_id = r.package_id
                    WHERE {' AND '.join(clauses)}
                    GROUP BY r.record_id, r.package_id, r.student_username,
                             r.status, r.score, r.feedback, r.started_at,
                             r.completed_at, r.payload_json, r.created_at,
                             r.updated_at, p.teacher_username, p.course_id,
                             p.package_title, p.risk_level, p.diagnosis_report_id,
                             p.payload_json
                    ORDER BY COALESCE(r.completed_at, r.updated_at, r.created_at) DESC, r.record_id DESC
                    LIMIT %s
                    """,
                    tuple([*params, limit]),
                )
                rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        node_candidate_cache: Dict[str, set[str]] = {}

        def valid_leaf_node_ids(item_course_id: Optional[str]) -> set[str]:
            clean_item_course_id = str(item_course_id or "").strip()
            if not clean_item_course_id:
                return set()
            if clean_item_course_id not in node_candidate_cache:
                node_candidate_cache[clean_item_course_id] = {
                    str(node.get("node_id") or "").strip()
                    for node in self.list_course_node_binding_candidates(clean_item_course_id)
                    if node.get("is_leaf") and str(node.get("node_id") or "").strip()
                }
            return node_candidate_cache[clean_item_course_id]

        for row in rows:
            item = dict(row)
            for key in ("record_payload_json", "package_payload_json"):
                payload = item.pop(key, None)
                try:
                    item[key.replace("_json", "")] = json.loads(payload) if isinstance(payload, str) else (payload or {})
                except Exception:
                    item[key.replace("_json", "")] = {}
            if item.get("score") is not None:
                item["score"] = float(item["score"])
            package_payload = item.get("package_payload") if isinstance(item.get("package_payload"), dict) else {}
            diagnosis = package_payload.get("diagnosis") if isinstance(package_payload.get("diagnosis"), dict) else {}
            if not item.get("course_id") and diagnosis.get("course_id"):
                item["course_id"] = str(diagnosis.get("course_id"))
            for key in ("started_at", "completed_at", "created_at", "updated_at"):
                item[key] = self._to_str(item.get(key))
            raw_items = str(item.pop("item_summary", "") or "")
            parsed_items: List[Dict[str, Any]] = []
            item_parts = raw_items.split("|||ITEM|||") if "|||ITEM|||" in raw_items else raw_items.split("||")
            for raw in [part for part in item_parts if part]:
                if "|||FIELD|||" in raw:
                    item_id, item_type, node_id, reminder_text, payload_text = (
                        raw.split("|||FIELD|||", 4) + ["", "", "", "", ""]
                    )[:5]
                else:
                    item_id, item_type, node_id, reminder_text, payload_text = (raw.split("|", 4) + ["", "", "", "", ""])[:5]
                payload: Dict[str, Any] = {}
                if payload_text:
                    try:
                        parsed = json.loads(payload_text)
                        payload = parsed if isinstance(parsed, dict) else {}
                    except Exception:
                        payload = {}
                item_course_id = str(item.get("course_id") or clean_course_id or "").strip() or None
                clean_node_id = str(node_id or "").strip()
                if clean_node_id and item_course_id:
                    valid_node_ids = valid_leaf_node_ids(item_course_id)
                    if valid_node_ids and clean_node_id not in valid_node_ids:
                        clean_node_id = ""
                parsed_items.append(
                    {
                        "item_id": int(item_id) if str(item_id).isdigit() else None,
                        "item_type": item_type or None,
                        "node_id": clean_node_id or None,
                        "reminder_text": reminder_text or None,
                        "payload": payload,
                    }
                )
            item["items"] = parsed_items
            result.append(item)
        return result

    def record_fivee_effectiveness(
        self,
        *,
        user_identifier: str,
        course_id: Optional[str],
        node_id: Optional[str],
        session_id: Optional[str],
        stage: str,
        interaction_count: int = 0,
        valid_interaction_count: int = 0,
        completion_rate: Optional[float] = None,
        quiz_score_before: Optional[float] = None,
        quiz_score_after: Optional[float] = None,
        path_continue_rate: Optional[float] = None,
        effectiveness_score: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
        student_username: Optional[str] = None,
    ) -> int:
        """Record one 5E interaction effectiveness evidence row."""
        user_identifier = str(user_identifier or "").strip()
        if not user_identifier:
            raise ValueError("user_identifier is required")
        stage = str(stage or "engagement").strip() or "engagement"
        student_username = str(student_username or user_identifier).strip() or None
        student_user_id = None
        if student_username:
            try:
                user = self.get_user_by_identifier("student", student_username)
                student_user_id = int(user["user_id"]) if user and user.get("user_id") else None
                if user and user.get("username"):
                    student_username = str(user["username"])
            except Exception:
                logger.debug("Unable to resolve 5E student user id for %s", student_username)

        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO fivee_effectiveness_records
                    (user_identifier, student_user_id, student_username, course_id, node_id,
                     session_id, stage, interaction_count, valid_interaction_count,
                     completion_rate, quiz_score_before, quiz_score_after,
                     path_continue_rate, effectiveness_score, payload_json,
                     calculated_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_identifier,
                        student_user_id,
                        student_username,
                        str(course_id or "").strip() or None,
                        str(node_id or "").strip() or None,
                        str(session_id or "").strip() or None,
                        stage,
                        max(0, int(interaction_count or 0)),
                        max(0, int(valid_interaction_count or 0)),
                        completion_rate,
                        quiz_score_before,
                        quiz_score_after,
                        path_continue_rate,
                        effectiveness_score,
                        self._json(payload or {}),
                        now,
                        now,
                    ),
                )
                return int(cursor.lastrowid or 0)

    def update_fivee_effectiveness_outcome(
        self,
        *,
        record_id: int,
        quiz_score_before: Optional[float] = None,
        quiz_score_after: Optional[float] = None,
        path_continue_rate: Optional[float] = None,
        effectiveness_score: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Attach later outcome evidence to an existing 5E effectiveness row."""
        if not record_id:
            return False
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE fivee_effectiveness_records
                    SET quiz_score_before = %s,
                        quiz_score_after = %s,
                        path_continue_rate = %s,
                        effectiveness_score = %s,
                        payload_json = %s,
                        calculated_at = %s
                    WHERE record_id = %s
                    """,
                    (
                        quiz_score_before,
                        quiz_score_after,
                        path_continue_rate,
                        effectiveness_score,
                        self._json(payload or {}),
                        now,
                        record_id,
                    ),
                )
                return int(cursor.rowcount or 0) > 0

    def record_diagnosis_correction(
        self,
        *,
        report_id: str,
        username: str,
        course_id: str,
        teacher_username: str,
        node_id: Optional[str] = None,
        original_reason_type: Optional[str] = None,
        corrected_reason_type: Optional[str] = None,
        original_evidence_level: Optional[str] = None,
        corrected_evidence_level: Optional[str] = None,
        correction_note: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """保存教师对诊断结论的人工修正，供证据下钻和后续诊断优化使用。"""
        report_id = str(report_id or "").strip()
        username = str(username or "").strip()
        course_id = str(course_id or "").strip()
        teacher_username = str(teacher_username or "").strip()
        if not report_id or not username or not course_id or not teacher_username:
            raise ValueError("report_id, username, course_id and teacher_username are required")
        teacher_user = self.get_user("teacher", teacher_username)
        teacher_user_id = int(teacher_user["user_id"]) if teacher_user and teacher_user.get("user_id") else None
        now = self._now()
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO diagnosis_corrections
                    (report_id, username, course_id, node_id, teacher_username, teacher_user_id,
                     original_reason_type, corrected_reason_type,
                     original_evidence_level, corrected_evidence_level,
                     correction_note, payload_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report_id,
                        username,
                        course_id,
                        str(node_id or "").strip() or None,
                        teacher_username,
                        teacher_user_id,
                        str(original_reason_type or "").strip() or None,
                        str(corrected_reason_type or "").strip() or None,
                        str(original_evidence_level or "").strip() or None,
                        str(corrected_evidence_level or "").strip() or None,
                        str(correction_note or "").strip() or None,
                        self._json(payload or {}),
                        now,
                    ),
                )
                return int(cursor.lastrowid)

    def list_diagnosis_corrections(
        self,
        *,
        report_id: Optional[str] = None,
        username: Optional[str] = None,
        course_id: Optional[str] = None,
        teacher_username: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询诊断人工修正记录。"""
        clauses: List[str] = []
        params: List[Any] = []
        for column, value in (
            ("report_id", report_id),
            ("username", username),
            ("course_id", course_id),
            ("teacher_username", teacher_username),
        ):
            clean = str(value or "").strip()
            if clean:
                clauses.append(f"{column} = %s")
                params.append(clean)
        limit = max(1, min(int(limit or 100), 500))
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT correction_id, report_id, username, course_id, node_id,
                           teacher_username, teacher_user_id,
                           original_reason_type, corrected_reason_type,
                           original_evidence_level, corrected_evidence_level,
                           correction_note, payload_json, created_at
                    FROM diagnosis_corrections
                    {where}
                    ORDER BY created_at DESC, correction_id DESC
                    LIMIT %s
                    """,
                    tuple([*params, limit]),
                )
                rows = cursor.fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            payload = row.get("payload_json")
            try:
                payload = json.loads(payload) if isinstance(payload, str) else (payload or {})
            except Exception:
                payload = {}
            result.append({
                "correction_id": int(row.get("correction_id") or 0),
                "report_id": row.get("report_id"),
                "username": row.get("username"),
                "course_id": row.get("course_id"),
                "node_id": row.get("node_id"),
                "teacher_username": row.get("teacher_username"),
                "teacher_user_id": row.get("teacher_user_id"),
                "original_reason_type": row.get("original_reason_type"),
                "corrected_reason_type": row.get("corrected_reason_type"),
                "original_evidence_level": row.get("original_evidence_level"),
                "corrected_evidence_level": row.get("corrected_evidence_level"),
                "correction_note": row.get("correction_note"),
                "payload": payload,
                "created_at": self._to_str(row.get("created_at")),
            })
        return result

    def permanently_delete_resource(self, course_id: str, node_id: str, resource_path: str) -> bool:
        """永久删除资源"""
        course_id = str(course_id or "").strip()
        node_id = str(node_id or "").strip()
        resource_path = str(resource_path or "").strip()
        if not course_id or not node_id or not resource_path:
            return False
        with self._lock, self.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM resources
                    WHERE course_id = %s AND node_id = %s AND resource_path = %s
                """, (course_id, node_id, resource_path))
                return cursor.rowcount > 0
