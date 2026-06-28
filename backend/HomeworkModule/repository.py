from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from DatabaseModule.store import get_database_store


class HomeworkRepository:
    """MySQL-backed repository for homework data."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        legacy_store_path: str | Path | None = None,
    ) -> None:
        # Kept for constructor compatibility with older tests/call sites.
        del db_path, legacy_store_path
        self.store = get_database_store()
        if os.getenv("DB_AUTO_MIGRATE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            self._initialize()

    def _initialize(self) -> None:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS homework_assignments (
                        id VARCHAR(100) PRIMARY KEY,
                        title VARCHAR(500) NOT NULL,
                        description TEXT,
                        assignment_type VARCHAR(50) NOT NULL,
                        class_name VARCHAR(200),
                        course_id VARCHAR(100) NOT NULL DEFAULT 'course_big_data',
                        node_id VARCHAR(255),
                        node_name VARCHAR(500),
                        node_path_json JSON NOT NULL,
                        chapter_context TEXT,
                        objective_result_mode VARCHAR(50) NOT NULL DEFAULT 'immediate',
                        due_at DATETIME,
                        allow_late TINYINT(1) NOT NULL DEFAULT 0,
                        total_score DECIMAL(8,2) NOT NULL DEFAULT 100.00,
                        rubric TEXT,
                        questions_json JSON NOT NULL,
                        created_by VARCHAR(100) NOT NULL,
                        created_at DATETIME NOT NULL,
                        status VARCHAR(50),
                        updated_at DATETIME,
                        INDEX idx_homework_assignments_created_by (created_by),
                        INDEX idx_homework_assignments_created_at (created_at),
                        INDEX idx_homework_assignments_course_node (course_id, node_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS homework_submissions (
                        id VARCHAR(100) PRIMARY KEY,
                        assignment_id VARCHAR(100) NOT NULL,
                        student_username VARCHAR(100) NOT NULL,
                        answers_json JSON NOT NULL,
                        submitted_at DATETIME NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'submitted',
                        ai_score DECIMAL(8,2),
                        ai_feedback TEXT,
                        ai_rationale TEXT,
                        teacher_score DECIMAL(8,2),
                        teacher_comment TEXT,
                        graded_at DATETIME,
                        grader_username VARCHAR(100),
                        updated_at DATETIME,
                        INDEX idx_homework_submissions_assignment (assignment_id),
                        INDEX idx_homework_submissions_student (student_username),
                        CONSTRAINT fk_homework_submissions_assignment
                            FOREIGN KEY (assignment_id)
                            REFERENCES homework_assignments(id)
                            ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _json(self, payload: Any) -> str:
        return json.dumps(payload if payload is not None else {}, ensure_ascii=False)

    def _json_list(self, payload: Any) -> str:
        return json.dumps(payload if isinstance(payload, list) else [], ensure_ascii=False)

    def _loads(self, value: Any, fallback: Any) -> Any:
        if value is None:
            return fallback
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(str(value))
        except Exception:
            return fallback

    def _normalize_datetime(self, value: Any) -> Optional[str]:
        if value is None or value == "":
            return None
        text = str(value).strip()
        if not text:
            return None
        if "T" in text:
            text = text.replace("T", " ")
        if "." in text:
            text = text.split(".", 1)[0]
        return text

    def _normalize_assignment_type(self, value: Any) -> str:
        allowed = {"objective", "subjective", "mixed", "coding"}
        text = str(value or "mixed").strip().lower()
        return text if text in allowed else "mixed"

    def _normalize_objective_result_mode(self, value: Any) -> str:
        allowed = {"immediate", "after_due", "manual"}
        text = str(value or "immediate").strip().lower()
        return text if text in allowed else "immediate"

    def _normalize_node_path(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str) and value.strip():
            parsed = self._loads(value, [])
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        return []

    def _assignment_from_row(self, row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        item = dict(row)
        item["questions"] = self._loads(item.pop("questions_json", None), [])
        item["node_path"] = self._loads(item.pop("node_path_json", None), [])
        item["allow_late"] = bool(item.get("allow_late"))
        if item.get("total_score") is not None:
            item["total_score"] = float(item["total_score"])
        item["covered_knowledge_points"] = self.list_assignment_coverage(str(item.get("id") or ""))
        return item

    def _submission_from_row(self, row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        item = dict(row)
        item["answers"] = self._loads(item.pop("answers_json", None), [])
        for key in ("ai_score", "teacher_score"):
            if item.get(key) is not None:
                item[key] = float(item[key])
        return item

    def _coverage_from_row(self, row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        item = dict(row)
        item["recommended_by_system"] = bool(item.get("recommended_by_system"))
        item["confirmed_by_teacher"] = bool(item.get("confirmed_by_teacher"))
        if item.get("confidence") is not None:
            item["confidence"] = float(item["confidence"])
        item["payload"] = self._loads(item.pop("payload_json", None), {})
        return item

    def _normalize_coverage_points(
        self,
        raw_points: Any,
        *,
        assignment_id: str,
        course_id: str,
        teacher_username: str,
    ) -> List[Dict[str, Any]]:
        if not isinstance(raw_points, list):
            return []
        result: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for raw in raw_points:
            if isinstance(raw, str):
                item = {"node_id": raw}
            elif isinstance(raw, dict):
                item = dict(raw)
            else:
                continue
            node_id = str(item.get("node_id") or item.get("id") or "").strip()
            resolved_course_id = str(item.get("course_id") or course_id or "").strip()
            if not node_id or not resolved_course_id:
                continue
            key = (resolved_course_id, node_id)
            if key in seen:
                continue
            seen.add(key)
            source = str(item.get("coverage_source") or "teacher_confirmed").strip() or "teacher_confirmed"
            recommended = bool(item.get("recommended_by_system"))
            confirmed = bool(item.get("confirmed_by_teacher", source == "teacher_confirmed"))
            confidence = item.get("confidence")
            try:
                confidence = None if confidence is None else max(0.0, min(float(confidence), 100.0))
            except (TypeError, ValueError):
                confidence = None
            result.append(
                {
                    "assignment_id": assignment_id,
                    "course_id": resolved_course_id,
                    "node_id": node_id,
                    "coverage_source": source,
                    "recommended_by_system": recommended,
                    "confirmed_by_teacher": confirmed,
                    "confidence": confidence,
                    "reason": str(item.get("reason") or "").strip(),
                    "teacher_username": teacher_username,
                    "payload": item,
                }
            )
        return result

    def list_assignment_coverage(self, assignment_id: str) -> List[Dict[str, Any]]:
        assignment_id = str(assignment_id or "").strip()
        if not assignment_id:
            return []
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, assignment_id, course_id, node_id, coverage_source,
                           recommended_by_system, confirmed_by_teacher, confidence,
                           reason, teacher_username, confirmed_at, payload_json,
                           created_at, updated_at
                    FROM homework_assignment_knowledge_points
                    WHERE assignment_id = %s
                    ORDER BY confirmed_by_teacher DESC, recommended_by_system DESC, node_id
                    """,
                    (assignment_id,),
                )
                rows = cursor.fetchall()
        return [item for item in (self._coverage_from_row(dict(row)) for row in rows) if item]

    def replace_assignment_coverage(
        self,
        assignment_id: str,
        raw_points: Any,
        *,
        course_id: str,
        teacher_username: str,
    ) -> List[Dict[str, Any]]:
        assignment_id = str(assignment_id or "").strip()
        course_id = str(course_id or "").strip()
        if not assignment_id:
            return []
        points = self._normalize_coverage_points(
            raw_points,
            assignment_id=assignment_id,
            course_id=course_id,
            teacher_username=teacher_username,
        )
        now = self._now()
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM homework_assignment_knowledge_points WHERE assignment_id = %s",
                    (assignment_id,),
                )
                for point in points:
                    cursor.execute(
                        """
                        INSERT INTO homework_assignment_knowledge_points
                        (assignment_id, course_id, node_id, coverage_source,
                         recommended_by_system, confirmed_by_teacher, confidence,
                         reason, teacher_username, confirmed_at, payload_json,
                         created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            coverage_source = VALUES(coverage_source),
                            recommended_by_system = VALUES(recommended_by_system),
                            confirmed_by_teacher = VALUES(confirmed_by_teacher),
                            confidence = VALUES(confidence),
                            reason = VALUES(reason),
                            teacher_username = VALUES(teacher_username),
                            confirmed_at = VALUES(confirmed_at),
                            payload_json = VALUES(payload_json),
                            updated_at = VALUES(updated_at)
                        """,
                        (
                            point["assignment_id"],
                            point["course_id"],
                            point["node_id"],
                            point["coverage_source"],
                            1 if point["recommended_by_system"] else 0,
                            1 if point["confirmed_by_teacher"] else 0,
                            point["confidence"],
                            point["reason"],
                            point["teacher_username"],
                            now if point["confirmed_by_teacher"] else None,
                            self._json(point["payload"]),
                            now,
                            now,
                        ),
                    )
        return self.list_assignment_coverage(assignment_id)

    def create_assignment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = {
            "id": uuid4().hex,
            "title": str(payload.get("title") or "").strip(),
            "description": str(payload.get("description") or "").strip(),
            "assignment_type": self._normalize_assignment_type(payload.get("assignment_type")),
            "class_name": str(payload.get("class_name") or "").strip(),
            "course_id": str(payload.get("course_id", "course_big_data") or "course_big_data").strip() or "course_big_data",
            "node_id": str(payload.get("node_id", "") or "").strip(),
            "node_name": str(payload.get("node_name", "") or "").strip(),
            "node_path": self._normalize_node_path(payload.get("node_path") or payload.get("node_path_json")),
            "chapter_context": str(payload.get("chapter_context") or "").strip(),
            "objective_result_mode": self._normalize_objective_result_mode(payload.get("objective_result_mode")),
            "due_at": self._normalize_datetime(payload.get("due_at")),
            "allow_late": 1 if payload.get("allow_late") else 0,
            "total_score": float(payload.get("total_score") or 100),
            "rubric": str(payload.get("rubric") or "").strip(),
            "questions": payload.get("questions") or [],
            "created_by": str(payload.get("created_by", "") or "").strip(),
            "created_at": now,
            "status": str(payload.get("status") or "draft"),
            "updated_at": now,
        }
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO homework_assignments
                    (id, title, description, assignment_type, class_name, course_id, node_id, node_name,
                     node_path_json, chapter_context, objective_result_mode, due_at, allow_late,
                     total_score, rubric, questions_json, created_by, created_at, status, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record["id"],
                        record["title"],
                        record["description"],
                        record["assignment_type"],
                        record["class_name"],
                        record["course_id"],
                        record["node_id"],
                        record["node_name"],
                        self._json_list(record["node_path"]),
                        record["chapter_context"],
                        record["objective_result_mode"],
                        record["due_at"],
                        record["allow_late"],
                        record["total_score"],
                        record["rubric"],
                        self._json_list(record["questions"]),
                        record["created_by"],
                        record["created_at"],
                        record["status"],
                        record["updated_at"],
                    ),
                )
        raw_coverage = payload.get("covered_knowledge_points") or payload.get("coverage_points")
        if raw_coverage:
            self.replace_assignment_coverage(
                record["id"],
                raw_coverage,
                course_id=record["course_id"],
                teacher_username=record["created_by"],
            )
        created = self.get_assignment(record["id"])
        return created or record

    def list_assignments(
        self,
        created_by: Optional[str] = None,
        status: Optional[str] = None,
        include_statuses: Optional[Iterable[str]] = None,
        course_id: Optional[str] = None,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if created_by:
            clauses.append("created_by = %s")
            params.append(created_by)
        statuses = [str(item) for item in include_statuses or [] if str(item)]
        if status:
            statuses.append(str(status).strip())
        statuses = list(dict.fromkeys(item for item in statuses if item))
        if statuses:
            clauses.append(f"status IN ({','.join(['%s'] * len(statuses))})")
            params.extend(statuses)
        if course_id:
            clauses.append("course_id = %s")
            params.append(str(course_id).strip())
        if node_id:
            clauses.append("node_id = %s")
            params.append(str(node_id).strip())
        if node_name:
            clauses.append("node_name = %s")
            params.append(str(node_name).strip())
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, title, description, assignment_type, class_name, course_id, node_id,
                           node_name, node_path_json, chapter_context, objective_result_mode, due_at,
                           allow_late, total_score, rubric, questions_json, created_by, created_at,
                           status, updated_at
                    FROM homework_assignments
                    {where_sql}
                    ORDER BY created_at DESC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        return [item for item in (self._assignment_from_row(dict(row)) for row in rows) if item]

    def get_assignment(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, title, description, assignment_type, class_name, course_id, node_id,
                           node_name, node_path_json, chapter_context, objective_result_mode, due_at,
                           allow_late, total_score, rubric, questions_json, created_by, created_at,
                           status, updated_at
                    FROM homework_assignments
                    WHERE id = %s
                    """,
                    (assignment_id,),
                )
                row = cursor.fetchone()
        return self._assignment_from_row(dict(row) if row else None)

    def update_assignment(self, assignment_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self.get_assignment(assignment_id)
        if not current:
            return None
        merged = {**current, **updates}
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE homework_assignments
                    SET title = %s,
                        description = %s,
                        assignment_type = %s,
                        class_name = %s,
                        course_id = %s,
                        node_id = %s,
                        node_name = %s,
                        node_path_json = %s,
                        chapter_context = %s,
                        objective_result_mode = %s,
                        due_at = %s,
                        allow_late = %s,
                        total_score = %s,
                        rubric = %s,
                        questions_json = %s,
                        status = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        str(merged.get("title") or "").strip(),
                        str(merged.get("description") or "").strip(),
                        self._normalize_assignment_type(merged.get("assignment_type")),
                        str(merged.get("class_name") or "").strip(),
                        str(merged.get("course_id", "course_big_data") or "course_big_data"),
                        str(merged.get("node_id") or "").strip(),
                        str(merged.get("node_name") or "").strip(),
                        self._json_list(self._normalize_node_path(merged.get("node_path") or merged.get("node_path_json"))),
                        str(merged.get("chapter_context") or "").strip(),
                        self._normalize_objective_result_mode(merged.get("objective_result_mode")),
                        self._normalize_datetime(merged.get("due_at")),
                        1 if merged.get("allow_late") else 0,
                        float(merged.get("total_score") or 100),
                        str(merged.get("rubric") or "").strip(),
                        self._json_list(merged.get("questions") or []),
                        str(merged.get("status") or "draft"),
                        self._now(),
                        assignment_id,
                    ),
                )
        raw_coverage = updates.get("covered_knowledge_points") or updates.get("coverage_points")
        if raw_coverage is not None:
            self.replace_assignment_coverage(
                assignment_id,
                raw_coverage,
                course_id=str(merged.get("course_id") or ""),
                teacher_username=str(merged.get("created_by") or ""),
            )
        return self.get_assignment(assignment_id)

    def create_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        now = self._now()
        record = {
            "id": uuid4().hex,
            "assignment_id": str(payload.get("assignment_id", "") or "").strip(),
            "student_username": str(payload.get("student_username", "") or "").strip(),
            "answers": payload.get("answers") or [],
            "submitted_at": now,
            "status": str(payload.get("status") or "submitted"),
            "updated_at": now,
        }
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO homework_submissions
                    (id, assignment_id, student_username, answers_json, submitted_at, status, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record["id"],
                        record["assignment_id"],
                        record["student_username"],
                        self._json_list(record["answers"]),
                        record["submitted_at"],
                        record["status"],
                        record["updated_at"],
                    ),
                )
        created = self.get_submission(record["id"])
        return created or record

    def list_submissions(
        self,
        assignment_id: Optional[str] = None,
        student_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        if assignment_id:
            clauses.append("assignment_id = %s")
            params.append(assignment_id)
        if student_username:
            clauses.append("student_username = %s")
            params.append(student_username)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, assignment_id, student_username, answers_json, submitted_at, status,
                           ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                           graded_at, grader_username, updated_at
                    FROM homework_submissions
                    {where_sql}
                    ORDER BY submitted_at DESC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        return [item for item in (self._submission_from_row(dict(row)) for row in rows) if item]

    def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, assignment_id, student_username, answers_json, submitted_at, status,
                           ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                           graded_at, grader_username, updated_at
                    FROM homework_submissions
                    WHERE id = %s
                    """,
                    (submission_id,),
                )
                row = cursor.fetchone()
        return self._submission_from_row(dict(row) if row else None)

    def update_submission(self, submission_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        current = self.get_submission(submission_id)
        if not current:
            return None
        merged = {**current, **updates}
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE homework_submissions
                    SET answers_json = %s,
                        status = %s,
                        ai_score = %s,
                        ai_feedback = %s,
                        ai_rationale = %s,
                        teacher_score = %s,
                        teacher_comment = %s,
                        graded_at = %s,
                        grader_username = %s,
                        updated_at = %s
                    WHERE id = %s
                    """,
                    (
                        self._json_list(merged.get("answers") or []),
                        str(merged.get("status") or "submitted"),
                        merged.get("ai_score"),
                        merged.get("ai_feedback"),
                        merged.get("ai_rationale"),
                        merged.get("teacher_score"),
                        merged.get("teacher_comment"),
                        self._normalize_datetime(merged.get("graded_at")),
                        merged.get("grader_username"),
                        self._now(),
                        submission_id,
                    ),
                )
        return self.get_submission(submission_id)

    def get_latest_submission(self, assignment_id: str, student_username: str) -> Optional[Dict[str, Any]]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, assignment_id, student_username, answers_json, submitted_at, status,
                           ai_score, ai_feedback, ai_rationale, teacher_score, teacher_comment,
                           graded_at, grader_username, updated_at
                    FROM homework_submissions
                    WHERE assignment_id = %s AND student_username = %s
                    ORDER BY submitted_at DESC
                    LIMIT 1
                    """,
                    (assignment_id, student_username),
                )
                row = cursor.fetchone()
        return self._submission_from_row(dict(row) if row else None)

    def get_stats(self) -> Dict[str, int]:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS c FROM homework_assignments")
                assignment_count = int(cursor.fetchone()["c"])
                cursor.execute("SELECT COUNT(*) AS c FROM homework_submissions")
                submission_count = int(cursor.fetchone()["c"])
        return {"assignments": assignment_count, "submissions": submission_count}
