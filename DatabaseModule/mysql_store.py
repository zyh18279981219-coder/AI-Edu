"""
MySQL数据库存储实现

实现DatabaseStore接口，提供MySQL数据库的具体访问逻辑。
支持连接池、事务管理、参数化查询等MySQL特性。
"""

from __future__ import annotations

import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

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
        
        for attempt in range(max_retries):
            try:
                conn = self._engine.raw_connection()
                self._use_dict_cursor(conn)
                try:
                    yield conn
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
                return  # 成功后退出
            except self._retryable_errors():
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise

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
                    
                    # 分割SQL语句并执行
                    statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                    
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
                activity_date DATE NOT NULL,
                activity_type VARCHAR(50) NOT NULL,
                activity_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_username_date (username, activity_date),
                INDEX idx_activity_date (activity_date),
                UNIQUE KEY unique_user_date_type (username, activity_date, activity_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

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
                INDEX idx_login_id (login_id),
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
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (teacher_username, student_username),
                INDEX idx_teacher_user_id (teacher_user_id),
                INDEX idx_student_user_id (student_user_id),
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
                filename VARCHAR(255) NOT NULL,
                plan_path VARCHAR(500),
                category ENUM('global', 'user', 'path') DEFAULT 'user',
                title VARCHAR(500),
                description TEXT,
                status ENUM('draft', 'active', 'completed', 'archived') DEFAULT 'draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uk_username_filename (username, filename),
                INDEX idx_user_id (user_id),
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
                        cursor.execute("""
                            INSERT INTO twin_profile_nodes
                            (username, user_id, node_id, node_path_json, quiz_score, progress,
                             study_duration_minutes, llm_interaction_count, mastery_score, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                node_path_json = VALUES(node_path_json),
                                quiz_score = VALUES(quiz_score),
                                progress = VALUES(progress),
                                study_duration_minutes = VALUES(study_duration_minutes),
                                llm_interaction_count = VALUES(llm_interaction_count),
                                mastery_score = VALUES(mastery_score),
                                updated_at = VALUES(updated_at)
                        """, (
                            canonical_username, user_id, node_id,
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
                if isinstance(payload, dict):
                    title = payload.get('title', filename)
                
                cursor.execute("""
                    INSERT INTO learning_plans
                    (username, user_id, filename, plan_path, category, title, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        plan_path = VALUES(plan_path),
                        category = VALUES(category),
                        title = VALUES(title),
                        updated_at = VALUES(updated_at)
                """, (username, user_id, filename, plan_path, category or 'user',
                      title, 'active', self._now(), self._now()))
                
                plan_id = cursor.lastrowid
                if not plan_id:
                    cursor.execute("SELECT plan_id FROM learning_plans WHERE username = %s AND filename = %s", (username, filename))
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

    def list_learning_plans(self, username: Optional[str] = None, categories: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        """列出学习计划"""
        sql = """
            SELECT lp.username, lp.filename, lp.plan_path, lp.category, lp.updated_at,
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
                "username": row[0], "filename": row[1], "plan_path": row[2],
                "category": row[3], "updated_at": row[4], "payload_json": row[5]
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
                "username": r["username"],
                "filename": r["filename"],
                "path": r["plan_path"] or "",
                "category": r["category"] or "",
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

    def _iter_graph_children(self, node: Dict[str, Any]) -> List[Dict[str, Any]]:
        """遍历图谱节点的子节点"""
        for key in ("children", "grandchildren", "great-grandchildren"):
            children = node.get(key)
            if isinstance(children, list):
                return [item for item in children if isinstance(item, dict)]
        return []

    def sync_course_from_graph(self, course_id: str, graph_data: Dict[str, Any], *, course_name: Optional[str] = None, source_path: Optional[str] = None) -> Dict[str, int]:
        """从课程图谱同步课程数据到MySQL"""
        if not isinstance(graph_data, dict):
            return {"nodes": 0, "resources": 0}
        course_id = str(course_id or "").strip()
        if not course_id:
            return {"nodes": 0, "resources": 0}

        now = self._now()
        course_name = str(course_name or graph_data.get("name") or course_id)
        nodes: List[Dict[str, Any]] = []
        resources: List[Dict[str, Any]] = []

        def walk(node: Dict[str, Any], path: List[str], parent_node_id: Optional[str]) -> None:
            node_name = str(node.get("name") or "").strip()
            if not node_name:
                return
            node_id = str(node.get("node_id") or node.get("id") or node_name).strip()
            node_path = path + [node_name]
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
                    suffix = _Path(rp).suffix.lower().lstrip(".")
                    resources.append({
                        "node_id": node_id, "resource_path": rp,
                        "resource_type": suffix[:200] if suffix else None,
                        "title": _Path(rp).name[:500],
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
                    INSERT INTO courses (course_id, course_name, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        course_name = VALUES(course_name),
                        updated_at = VALUES(updated_at)
                """, (course_id, course_name, now, now))
                
                # 更新course_metadata
                cursor.execute("""
                    INSERT INTO course_metadata (course_id, additional_data, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        additional_data = VALUES(additional_data),
                        updated_at = VALUES(updated_at)
                """, (course_id, self._json({"root_name": graph_data.get("root_name", ""), "structure": graph_data}), now, now))
                
                # 清空并重建节点和资源
                cursor.execute("DELETE FROM resources WHERE course_id = %s", (course_id,))
                cursor.execute("DELETE FROM course_nodes WHERE course_id = %s", (course_id,))
                
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
                    cursor.execute("""
                        INSERT INTO resources
                        (course_id, node_id, resource_path, resource_type, title, payload_json, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            resource_type = VALUES(resource_type),
                            title = VALUES(title),
                            payload_json = VALUES(payload_json),
                            updated_at = VALUES(updated_at)
                    """, (course_id, resource["node_id"], rp,
                          resource["resource_type"], resource["title"],
                          self._json(resource["payload"]), now, now))
        
        return {"nodes": len(nodes), "resources": len(resources)}

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
