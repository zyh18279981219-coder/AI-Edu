from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class SQLiteStore:
    def __init__(self, db_path: str | Path = "data/app.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize(self):
        with self._lock, self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_type TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT,
                    display_name TEXT,
                    teacher TEXT,
                    email TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_type, username)
                );

                CREATE TABLE IF NOT EXISTS teacher_student_links (
                    teacher_username TEXT NOT NULL,
                    student_username TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (teacher_username, student_username)
                );

                CREATE TABLE IF NOT EXISTS twin_profiles (
                    username TEXT PRIMARY KEY,
                    last_updated TEXT,
                    overall_mastery REAL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS twin_history (
                    username TEXT NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    overall_mastery REAL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (username, snapshot_date)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    user_type TEXT NOT NULL,
                    created_at TEXT,
                    last_accessed TEXT,
                    current_pdf_path TEXT,
                    current_node TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS user_states (
                    username TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS llm_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    username TEXT,
                    module TEXT,
                    model TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS learning_plans (
                    username TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    plan_path TEXT,
                    category TEXT,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (username, filename)
                );

                CREATE INDEX IF NOT EXISTS idx_users_type ON users(user_type);
                CREATE INDEX IF NOT EXISTS idx_sessions_username ON sessions(username);
                CREATE INDEX IF NOT EXISTS idx_logs_username ON llm_logs(username);
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON llm_logs(timestamp);
                CREATE INDEX IF NOT EXISTS idx_plans_username ON learning_plans(username);
                """
            )

    def _json(self, payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def _now(self) -> str:
        return datetime.now().isoformat()

    def list_users(self, user_type: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM users WHERE user_type = ? ORDER BY username",
                (user_type,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_user(self, user_type: str, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM users WHERE user_type = ? AND username = ?",
                (user_type, username),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def replace_users(self, user_type: str, users: Iterable[Dict[str, Any]]) -> None:
        users = list(users)
        timestamp = self._now()
        with self._lock, self.connection() as conn:
            conn.execute("DELETE FROM users WHERE user_type = ?", (user_type,))
            if user_type == "teacher":
                conn.execute("DELETE FROM teacher_student_links")
            for user in users:
                username = user.get("username")
                if not username:
                    continue
                display_name = user.get("stu_name") or user.get("name") or username
                conn.execute(
                    """
                    INSERT OR REPLACE INTO users
                    (user_type, username, password, display_name, teacher, email, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_type,
                        username,
                        user.get("password"),
                        display_name,
                        user.get("teacher"),
                        user.get("email"),
                        self._json(user),
                        timestamp,
                    ),
                )
                if user_type == "teacher":
                    for student_username in user.get("students", []) or []:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO teacher_student_links
                            (teacher_username, student_username, updated_at)
                            VALUES (?, ?, ?)
                            """,
                            (username, student_username, timestamp),
                        )

    def save_twin_profile(self, username: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO twin_profiles
                (username, last_updated, overall_mastery, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    payload.get("last_updated"),
                    payload.get("overall_mastery", 0),
                    self._json(payload),
                    self._now(),
                ),
            )

    def get_twin_profile(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM twin_profiles WHERE username = ?",
                (username,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_twin_profiles(self) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM twin_profiles ORDER BY username"
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_twin_history(self, username: str, snapshot_date: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO twin_history
                (username, snapshot_date, overall_mastery, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    snapshot_date,
                    payload.get("overall_mastery", 0),
                    self._json(payload),
                    self._now(),
                ),
            )

    def get_twin_history(self, username: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM twin_history
                WHERE username = ?
                ORDER BY snapshot_date
                """,
                (username,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_session(self, session_id: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, username, user_type, created_at, last_accessed, current_pdf_path, current_node, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    payload.get("username"),
                    payload.get("user_type"),
                    payload.get("created_at"),
                    payload.get("last_accessed"),
                    payload.get("current_pdf_path"),
                    payload.get("current_node"),
                    self._json(payload),
                    self._now(),
                ),
            )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def delete_session(self, session_id: str) -> None:
        with self._lock, self.connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute("SELECT payload_json FROM sessions").fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_user_state(self, username: str, payload: Dict[str, Any]) -> None:
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO user_states
                (username, payload_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (username, self._json(payload), self._now()),
            )

    def get_user_state(self, username: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM user_states WHERE username = ?",
                (username,),
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def append_llm_log(self, payload: Dict[str, Any]) -> None:
        request = payload.get("request") or {}
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT INTO llm_logs (timestamp, username, module, model, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.get("timestamp"),
                    payload.get("username"),
                    payload.get("module"),
                    request.get("model"),
                    self._json(payload),
                ),
            )

    def replace_llm_logs(self, logs: Iterable[Dict[str, Any]]) -> None:
        with self._lock, self.connection() as conn:
            conn.execute("DELETE FROM llm_logs")
        for item in logs:
            self.append_llm_log(item)

    def list_llm_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = "SELECT payload_json FROM llm_logs ORDER BY id DESC"
        params: tuple[Any, ...] = ()
        if limit:
            sql += " LIMIT ?"
            params = (limit,)
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_learning_plan(
        self,
        username: str,
        filename: str,
        payload: Any,
        plan_path: Optional[str] = None,
        category: Optional[str] = None,
    ) -> None:
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO learning_plans
                (username, filename, plan_path, category, payload_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    filename,
                    plan_path,
                    category,
                    self._json(payload),
                    self._now(),
                ),
            )

    def list_learning_plans(
        self,
        username: Optional[str] = None,
        categories: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        sql = """
            SELECT username, filename, plan_path, category, payload_json, updated_at
            FROM learning_plans
        """
        clauses: list[str] = []
        params: list[Any] = []
        if username:
            clauses.append("username = ?")
            params.append(username)
        if categories:
            category_list = [item for item in categories if item]
            if category_list:
                placeholders = ", ".join(["?"] * len(category_list))
                clauses.append(f"category IN ({placeholders})")
                params.extend(category_list)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, filename DESC"
        with self._lock, self.connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
        return [
            {
                "username": row["username"],
                "filename": row["filename"],
                "path": row["plan_path"] or "",
                "category": row["category"] or "",
                "data": json.loads(row["payload_json"]),
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def get_latest_learning_plan(
        self,
        username: str,
        category: Optional[str] = None,
        filename_prefix: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        sql = """
            SELECT username, filename, plan_path, category, payload_json, updated_at
            FROM learning_plans
            WHERE username = ?
        """
        params: list[Any] = [username]
        if category is not None:
            sql += " AND category = ?"
            params.append(category)
        if filename_prefix is not None:
            sql += " AND filename LIKE ?"
            params.append(f"{filename_prefix}%")
        sql += " ORDER BY updated_at DESC, filename DESC LIMIT 1"

        with self._lock, self.connection() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
        if row is None:
            return None
        return {
            "username": row["username"],
            "filename": row["filename"],
            "path": row["plan_path"] or "",
            "category": row["category"] or "",
            "data": json.loads(row["payload_json"]),
            "updated_at": row["updated_at"],
        }


_sqlite_store: Optional[SQLiteStore] = None


def get_sqlite_store() -> SQLiteStore:
    global _sqlite_store
    if _sqlite_store is None:
        _sqlite_store = SQLiteStore()
    return _sqlite_store
