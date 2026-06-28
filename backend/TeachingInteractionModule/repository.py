from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from DatabaseModule.store import get_database_store


class TeachingInteractionRepository:
    """MySQL repository for announcements, discussion topics, and posts."""

    def __init__(self) -> None:
        self.store = get_database_store()
        if os.getenv("DB_AUTO_MIGRATE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            self._initialize()

    def _initialize(self) -> None:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
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
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
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
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
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
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO teaching_announcements
                    (id, teacher_username, title, content, class_name, course_id,
                     status, published_at, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

    def get_announcement(self, announcement_id: str) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, teacher_username, title, content, class_name, course_id,
                           status, published_at, created_at, updated_at
                    FROM teaching_announcements
                    WHERE id = %s
                    """,
                    (announcement_id,),
                )
                row = cursor.fetchone()
        return dict(row) if row else None

    def update_announcement(self, announcement_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM teaching_announcements WHERE id = %s", (announcement_id,))
                if not cursor.fetchone():
                    return None
                cursor.execute(
                    """
                    UPDATE teaching_announcements
                    SET title = %s,
                        content = %s,
                        class_name = %s,
                        course_id = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        str(payload.get("title") or "").strip(),
                        str(payload.get("content") or "").strip(),
                        str(payload.get("class_name") or "").strip(),
                        str(payload.get("course_id") or "").strip(),
                        self._now(),
                        announcement_id,
                    ),
                )
        return self.get_announcement(announcement_id)

    def delete_announcement(self, announcement_id: str) -> bool:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM teaching_announcements WHERE id = %s", (announcement_id,))
                return int(cursor.rowcount or 0) > 0

    def list_announcements(self, teacher_username: str) -> List[Dict[str, Any]]:
        return self._list_announcements("WHERE teacher_username = %s", (teacher_username,))

    def list_announcements_all(self) -> List[Dict[str, Any]]:
        return self._list_announcements("", ())

    def _list_announcements(self, where_sql: str, params: tuple[Any, ...]) -> List[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, teacher_username, title, content, class_name, course_id,
                           status, published_at, created_at, updated_at
                    FROM teaching_announcements
                    {where_sql}
                    ORDER BY published_at DESC, created_at DESC
                    """,
                    params,
                )
                return [dict(row) for row in cursor.fetchall()]

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
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO teaching_discussion_topics
                    (id, teacher_username, title, content, class_name, course_id, status,
                     student_question_count, teacher_reply_count, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, teacher_username, title, content, class_name, course_id, status,
                           student_question_count, teacher_reply_count, created_at, updated_at
                    FROM teaching_discussion_topics
                    WHERE id = %s
                    """,
                    (topic_id,),
                )
                row = cursor.fetchone()
        return dict(row) if row else None

    def list_topics(self, teacher_username: str) -> List[Dict[str, Any]]:
        return self._list_topics("WHERE teacher_username = %s", (teacher_username,))

    def list_topics_all(self) -> List[Dict[str, Any]]:
        return self._list_topics("", ())

    def _list_topics(self, where_sql: str, params: tuple[Any, ...]) -> List[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, teacher_username, title, content, class_name, course_id, status,
                           student_question_count, teacher_reply_count, created_at, updated_at
                    FROM teaching_discussion_topics
                    {where_sql}
                    ORDER BY created_at DESC
                    """,
                    params,
                )
                return [dict(row) for row in cursor.fetchall()]

    def update_topic_counters(
        self,
        topic_id: str,
        *,
        student_question_delta: int = 0,
        teacher_reply_delta: int = 0,
    ) -> None:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE teaching_discussion_topics
                    SET student_question_count = student_question_count + %s,
                        teacher_reply_count = teacher_reply_count + %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (student_question_delta, teacher_reply_delta, self._now(), topic_id),
                )

    def update_topic(self, topic_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM teaching_discussion_topics WHERE id = %s", (topic_id,))
                if not cursor.fetchone():
                    return None
                cursor.execute(
                    """
                    UPDATE teaching_discussion_topics
                    SET title = %s,
                        content = %s,
                        class_name = %s,
                        course_id = %s,
                        status = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        str(payload.get("title") or "").strip(),
                        str(payload.get("content") or "").strip(),
                        str(payload.get("class_name") or "").strip(),
                        str(payload.get("course_id") or "").strip(),
                        str(payload.get("status") or "open"),
                        self._now(),
                        topic_id,
                    ),
                )
        return self.get_topic(topic_id)

    def delete_topic(self, topic_id: str) -> bool:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM teaching_discussion_topics WHERE id = %s", (topic_id,))
                return int(cursor.rowcount or 0) > 0

    def create_post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = {
            "id": uuid4().hex,
            "topic_id": str(payload.get("topic_id") or "").strip(),
            "author_username": str(payload.get("author_username") or "").strip(),
            "author_role": str(payload.get("author_role") or "").strip(),
            "content": str(payload.get("content") or "").strip(),
            "replied_to_post_id": str(payload.get("replied_to_post_id") or "").strip() or None,
            "response_minutes": payload.get("response_minutes"),
            "created_at": now,
            "updated_at": now,
        }
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO teaching_discussion_posts
                    (id, topic_id, author_username, author_role, content, replied_to_post_id,
                     response_minutes, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        record["updated_at"],
                    ),
                )
        return record

    def get_post(self, post_id: str) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, topic_id, author_username, author_role, content, replied_to_post_id,
                           response_minutes, created_at, updated_at
                    FROM teaching_discussion_posts
                    WHERE id = %s
                    """,
                    (post_id,),
                )
                row = cursor.fetchone()
        return dict(row) if row else None

    def update_post(self, post_id: str, content: str) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM teaching_discussion_posts WHERE id = %s", (post_id,))
                if not cursor.fetchone():
                    return None
                cursor.execute(
                    "UPDATE teaching_discussion_posts SET content = %s, updated_at = %s WHERE id = %s",
                    (content, self._now(), post_id),
                )
        return self.get_post(post_id)

    def delete_post(self, post_id: str) -> bool:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM teaching_discussion_posts WHERE id = %s", (post_id,))
                return int(cursor.rowcount or 0) > 0

    def list_posts(self, topic_id: str) -> List[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, topic_id, author_username, author_role, content, replied_to_post_id,
                           response_minutes, created_at, updated_at
                    FROM teaching_discussion_posts
                    WHERE topic_id = %s
                    ORDER BY created_at ASC
                    """,
                    (topic_id,),
                )
                return [dict(row) for row in cursor.fetchall()]
