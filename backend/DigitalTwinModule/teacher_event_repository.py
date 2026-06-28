from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from DatabaseModule.database_factory import DatabaseFactory


class TeacherEventRepository:
    """MySQL repository for teacher-side structured events."""

    def __init__(self) -> None:
        self.store = DatabaseFactory.get_store()
        if os.getenv("DB_AUTO_MIGRATE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            self._ensure_schema()

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _json(self, payload: Any) -> str:
        return json.dumps(payload or {}, ensure_ascii=False)

    def _execute(self, conn: Any, sql: str, params: Iterable[Any] = ()) -> Any:
        with conn.cursor() as cursor:
            cursor.execute(sql.replace("?", "%s"), tuple(params))
            return cursor

    def _fetchall(self, conn: Any, sql: str, params: Iterable[Any] = ()) -> List[Dict[str, Any]]:
        cursor = self._execute(conn, sql, params)
        rows = cursor.fetchall()
        return [dict(row) if isinstance(row, dict) else row for row in rows]

    def _create_table(self, conn: Any, _legacy_sql: str, mysql_sql: str) -> None:
        with conn.cursor() as cursor:
            cursor.execute(mysql_sql)

    def _create_index(self, conn: Any, name: str, table: str, columns: str) -> None:
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE INDEX {name} ON {table}({columns})")
        except Exception:
            # MySQL may raise when the index already exists.
            pass

    def _ensure_schema(self) -> None:
        with self.store.connection() as conn:
            self._create_table(
                conn,
                """
                CREATE TABLE IF NOT EXISTS teaching_interaction_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_username TEXT NOT NULL,
                    course_id TEXT,
                    class_name TEXT,
                    event_type TEXT NOT NULL,
                    target_id TEXT,
                    student_username TEXT,
                    response_minutes REAL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """,
                """
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
                    created_at VARCHAR(40) NOT NULL
                )
                """,
            )
            self._create_table(
                conn,
                """
                CREATE TABLE IF NOT EXISTS teaching_research_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_username TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    resource_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS teaching_research_events (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    teacher_username VARCHAR(100) NOT NULL,
                    event_type VARCHAR(100) NOT NULL,
                    resource_id VARCHAR(255),
                    payload_json LONGTEXT NOT NULL,
                    created_at VARCHAR(40) NOT NULL
                )
                """,
            )
            self._create_table(
                conn,
                """
                CREATE TABLE IF NOT EXISTS homework_grading_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assignment_id TEXT NOT NULL,
                    submission_id TEXT,
                    teacher_username TEXT NOT NULL,
                    student_username TEXT,
                    event_type TEXT NOT NULL,
                    grading_minutes REAL,
                    is_ai_recommended INTEGER DEFAULT 0,
                    is_ai_executed INTEGER DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """,
                """
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
                    created_at VARCHAR(40) NOT NULL
                )
                """,
            )
            self._create_table(
                conn,
                """
                CREATE TABLE IF NOT EXISTS teacher_intervention_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id TEXT,
                    teacher_username TEXT NOT NULL,
                    student_username TEXT,
                    event_type TEXT NOT NULL,
                    weak_node_count INTEGER DEFAULT 0,
                    completion_rate REAL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS teacher_intervention_events (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    package_id VARCHAR(255),
                    teacher_username VARCHAR(100) NOT NULL,
                    student_username VARCHAR(100),
                    event_type VARCHAR(100) NOT NULL,
                    weak_node_count INT DEFAULT 0,
                    completion_rate DOUBLE DEFAULT 0,
                    payload_json LONGTEXT NOT NULL,
                    created_at VARCHAR(40) NOT NULL
                )
                """,
            )
            self._create_index(conn, "idx_tie_teacher_time", "teaching_interaction_events", "teacher_username, created_at")
            self._create_index(conn, "idx_tie_type_time", "teaching_interaction_events", "event_type, created_at")
            self._create_index(conn, "idx_tre_teacher_time", "teaching_research_events", "teacher_username, created_at")
            self._create_index(conn, "idx_hge_teacher_time", "homework_grading_events", "teacher_username, created_at")
            self._create_index(conn, "idx_hge_assignment", "homework_grading_events", "assignment_id")
            self._create_index(conn, "idx_tievt_teacher_time", "teacher_intervention_events", "teacher_username, created_at")

    def record_interaction_event(
        self,
        *,
        teacher_username: str,
        event_type: str,
        course_id: Optional[str] = None,
        class_name: Optional[str] = None,
        target_id: Optional[str] = None,
        student_username: Optional[str] = None,
        response_minutes: Optional[float] = None,
        payload: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> None:
        timestamp = str(created_at or self._now())
        with self.store.connection() as conn:
            self._execute(
                conn,
                """
                INSERT INTO teaching_interaction_events
                (teacher_username, course_id, class_name, event_type, target_id, student_username, response_minutes, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    teacher_username,
                    course_id,
                    class_name,
                    event_type,
                    target_id,
                    student_username,
                    response_minutes,
                    self._json(payload),
                    timestamp,
                ),
            )

    def record_research_event(
        self,
        *,
        teacher_username: str,
        event_type: str,
        resource_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> None:
        timestamp = str(created_at or self._now())
        with self.store.connection() as conn:
            self._execute(
                conn,
                """
                INSERT INTO teaching_research_events
                (teacher_username, event_type, resource_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (teacher_username, event_type, resource_id, self._json(payload), timestamp),
            )

    def record_grading_event(
        self,
        *,
        assignment_id: str,
        teacher_username: str,
        event_type: str,
        submission_id: Optional[str] = None,
        student_username: Optional[str] = None,
        grading_minutes: Optional[float] = None,
        is_ai_recommended: bool = False,
        is_ai_executed: bool = False,
        payload: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> None:
        timestamp = str(created_at or self._now())
        with self.store.connection() as conn:
            self._execute(
                conn,
                """
                INSERT INTO homework_grading_events
                (assignment_id, submission_id, teacher_username, student_username, event_type, grading_minutes, is_ai_recommended, is_ai_executed, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assignment_id,
                    submission_id,
                    teacher_username,
                    student_username,
                    event_type,
                    grading_minutes,
                    1 if is_ai_recommended else 0,
                    1 if is_ai_executed else 0,
                    self._json(payload),
                    timestamp,
                ),
            )

    def record_intervention_event(
        self,
        *,
        teacher_username: str,
        event_type: str,
        package_id: Optional[str] = None,
        student_username: Optional[str] = None,
        weak_node_count: int = 0,
        completion_rate: float = 0.0,
        payload: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> None:
        timestamp = str(created_at or self._now())
        with self.store.connection() as conn:
            self._execute(
                conn,
                """
                INSERT INTO teacher_intervention_events
                (package_id, teacher_username, student_username, event_type, weak_node_count, completion_rate, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    package_id,
                    teacher_username,
                    student_username,
                    event_type,
                    int(weak_node_count or 0),
                    float(completion_rate or 0.0),
                    self._json(payload),
                    timestamp,
                ),
            )

    def _list_events(
        self,
        *,
        table: str,
        teacher_username: str,
        since: Optional[str] = None,
        event_types: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        sql = f"SELECT * FROM {table} WHERE teacher_username = ?"
        params: List[Any] = [teacher_username]
        if since:
            sql += " AND created_at >= ?"
            params.append(since)
        event_type_list = [str(item).strip() for item in (event_types or []) if str(item).strip()]
        if event_type_list:
            placeholders = ", ".join(["?"] * len(event_type_list))
            sql += f" AND event_type IN ({placeholders})"
            params.extend(event_type_list)
        sql += " ORDER BY created_at DESC, id DESC"
        with self.store.connection() as conn:
            rows = self._fetchall(conn, sql, params)
        result: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            raw_payload = item.get("payload_json")
            try:
                item["payload"] = json.loads(raw_payload) if raw_payload else {}
            except Exception:
                item["payload"] = {}
            result.append(item)
        return result

    def list_interaction_events(
        self,
        teacher_username: str,
        *,
        since: Optional[str] = None,
        event_types: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self._list_events(
            table="teaching_interaction_events",
            teacher_username=teacher_username,
            since=since,
            event_types=event_types,
        )

    def list_research_events(
        self,
        teacher_username: str,
        *,
        since: Optional[str] = None,
        event_types: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self._list_events(
            table="teaching_research_events",
            teacher_username=teacher_username,
            since=since,
            event_types=event_types,
        )

    def list_grading_events(
        self,
        teacher_username: str,
        *,
        since: Optional[str] = None,
        event_types: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self._list_events(
            table="homework_grading_events",
            teacher_username=teacher_username,
            since=since,
            event_types=event_types,
        )

    def list_intervention_events(
        self,
        teacher_username: str,
        *,
        since: Optional[str] = None,
        event_types: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self._list_events(
            table="teacher_intervention_events",
            teacher_username=teacher_username,
            since=since,
            event_types=event_types,
        )


_teacher_event_repository: Optional[TeacherEventRepository] = None


def get_teacher_event_repository() -> TeacherEventRepository:
    global _teacher_event_repository
    if _teacher_event_repository is None:
        _teacher_event_repository = TeacherEventRepository()
    return _teacher_event_repository
