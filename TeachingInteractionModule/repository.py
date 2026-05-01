from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


class TeachingInteractionRepository:
    def __init__(self, db_path: str | Path = "data/app.db") -> None:
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

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _json(self, payload: Any) -> str:
        return json.dumps(payload or {}, ensure_ascii=False)

    def _initialize(self) -> None:
        with self._lock, self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS teaching_announcements (
                    id TEXT PRIMARY KEY,
                    teacher_username TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    class_name TEXT,
                    course_id TEXT,
                    status TEXT NOT NULL DEFAULT 'published',
                    published_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS teaching_discussion_topics (
                    id TEXT PRIMARY KEY,
                    teacher_username TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    class_name TEXT,
                    course_id TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    student_question_count INTEGER NOT NULL DEFAULT 0,
                    teacher_reply_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS teaching_discussion_posts (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL,
                    author_username TEXT NOT NULL,
                    author_role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    replied_to_post_id TEXT,
                    response_minutes REAL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (topic_id) REFERENCES teaching_discussion_topics(id)
                );

                CREATE INDEX IF NOT EXISTS idx_teaching_announcements_teacher ON teaching_announcements(teacher_username, published_at);
                CREATE INDEX IF NOT EXISTS idx_teaching_topics_teacher ON teaching_discussion_topics(teacher_username, created_at);
                CREATE INDEX IF NOT EXISTS idx_teaching_posts_topic ON teaching_discussion_posts(topic_id, created_at);
                """
            )

    def create_announcement(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = {
            "id": uuid4().hex,
            "teacher_username": str(payload.get("teacher_username") or "").strip(),
            "title": str(payload.get("title") or "").strip(),
            "content": str(payload.get("content") or "").strip(),
            "class_name": str(payload.get("class_name") or "").strip(),
            "course_id": str(payload.get("course_id") or "").strip(),
            "status": str(payload.get("status") or "published"),
            "published_at": str(payload.get("published_at") or now),
            "created_at": now,
            "updated_at": now,
        }
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT INTO teaching_announcements
                (id, teacher_username, title, content, class_name, course_id, status, published_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["teacher_username"],
                    record["title"],
                    record["content"],
                    record["class_name"],
                    record["course_id"],
                    record["status"],
                    record["published_at"],
                    record["created_at"],
                    record["updated_at"],
                ),
            )
        return record

    def list_announcements(self, teacher_username: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, teacher_username, title, content, class_name, course_id, status, published_at, created_at, updated_at
                FROM teaching_announcements
                WHERE teacher_username = ?
                ORDER BY published_at DESC, created_at DESC
                """,
                (teacher_username,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_topic(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = {
            "id": uuid4().hex,
            "teacher_username": str(payload.get("teacher_username") or "").strip(),
            "title": str(payload.get("title") or "").strip(),
            "content": str(payload.get("content") or "").strip(),
            "class_name": str(payload.get("class_name") or "").strip(),
            "course_id": str(payload.get("course_id") or "").strip(),
            "status": str(payload.get("status") or "open"),
            "student_question_count": int(payload.get("student_question_count") or 0),
            "teacher_reply_count": int(payload.get("teacher_reply_count") or 0),
            "created_at": now,
            "updated_at": now,
        }
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT INTO teaching_discussion_topics
                (id, teacher_username, title, content, class_name, course_id, status, student_question_count, teacher_reply_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["teacher_username"],
                    record["title"],
                    record["content"],
                    record["class_name"],
                    record["course_id"],
                    record["status"],
                    record["student_question_count"],
                    record["teacher_reply_count"],
                    record["created_at"],
                    record["updated_at"],
                ),
            )
        return record

    def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            row = conn.execute(
                """
                SELECT id, teacher_username, title, content, class_name, course_id, status, student_question_count, teacher_reply_count, created_at, updated_at
                FROM teaching_discussion_topics
                WHERE id = ?
                """,
                (topic_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_topics(self, teacher_username: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, teacher_username, title, content, class_name, course_id, status, student_question_count, teacher_reply_count, created_at, updated_at
                FROM teaching_discussion_topics
                WHERE teacher_username = ?
                ORDER BY updated_at DESC, created_at DESC
                """,
                (teacher_username,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_topic_counters(self, topic_id: str, *, student_question_delta: int = 0, teacher_reply_delta: int = 0) -> None:
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                UPDATE teaching_discussion_topics
                SET student_question_count = student_question_count + ?,
                    teacher_reply_count = teacher_reply_count + ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (student_question_delta, teacher_reply_delta, self._now(), topic_id),
            )

    def create_post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = {
            "id": uuid4().hex,
            "topic_id": str(payload.get("topic_id") or "").strip(),
            "author_username": str(payload.get("author_username") or "").strip(),
            "author_role": str(payload.get("author_role") or "teacher").strip(),
            "content": str(payload.get("content") or "").strip(),
            "replied_to_post_id": str(payload.get("replied_to_post_id") or "").strip() or None,
            "response_minutes": payload.get("response_minutes"),
            "created_at": now,
        }
        with self._lock, self.connection() as conn:
            conn.execute(
                """
                INSERT INTO teaching_discussion_posts
                (id, topic_id, author_username, author_role, content, replied_to_post_id, response_minutes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["topic_id"],
                    record["author_username"],
                    record["author_role"],
                    record["content"],
                    record["replied_to_post_id"],
                    record["response_minutes"],
                    record["created_at"],
                ),
            )
        return record

    def list_posts(self, topic_id: str) -> List[Dict[str, Any]]:
        with self._lock, self.connection() as conn:
            rows = conn.execute(
                """
                SELECT id, topic_id, author_username, author_role, content, replied_to_post_id, response_minutes, created_at
                FROM teaching_discussion_posts
                WHERE topic_id = ?
                ORDER BY created_at ASC
                """,
                (topic_id,),
            ).fetchall()
        return [dict(row) for row in rows]

