from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_openai import ChatOpenAI

from DatabaseModule.database_factory import DatabaseFactory
from DiagnosisModule.diagnosis_service import StudentDiagnosisService
from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
from HomeworkModule.service import HomeworkService
from PathPlannerModule.path_planner_agent import PathPlannerAgent
from QuizModule.definition_utils import QUIZ_DEFINITION_STATE_PREFIX, published_definition_index_from_state_rows
from tools.llm_logger import get_llm_logger
from tools.session_manager import get_session_manager


NAMESPACE_KEY = "teacher_intervention_module_v1"


class TeacherInterventionService:
    def __init__(self) -> None:
        self.store = DatabaseFactory.get_store()
        self.teacher_event_repo = get_teacher_event_repository()
        self.session_manager = get_session_manager()
        self.homework_service = HomeworkService()
        self.llm_logger = get_llm_logger()
        self.model_name = str(os.environ.get("model_name") or "").strip()
        self.base_url = str(os.environ.get("base_url") or "").strip()
        self.api_key = str(os.environ.get("api_key") or "").strip()

    def _now(self) -> str:
        return datetime.now().isoformat()

    def _extract_json_object(self, raw_text: str) -> dict:
        text = str(raw_text or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            left = text.find("{")
            right = text.rfind("}")
            if left >= 0 and right > left:
                try:
                    return json.loads(text[left : right + 1])
                except json.JSONDecodeError:
                    return {}
        return {}

    def _get_draft_file_path(self, username: str) -> str:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "intervention_drafts")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, f"{username}.json")

    def _get_user_module_state(self, username: str) -> Dict[str, Any]:
        filepath = self._get_draft_file_path(username)
        if os.path.exists(filepath):
            try:
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    if isinstance(state, dict):
                        return state
            except Exception:
                pass
        return {}

    def _set_user_module_state(self, username: str, module_state: Dict[str, Any]) -> None:
        payload = dict(module_state)
        payload["updated_at"] = self._now()
        filepath = self._get_draft_file_path(username)
        try:
            import json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if hasattr(self, 'llm_logger') and hasattr(self.llm_logger, 'logger'):
                self.llm_logger.logger.error(f"Failed to save module state: {e}")

    def _record_intervention_event(
        self,
        package: Dict[str, Any],
        event_type: str,
        *,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        teacher_username = str(package.get("teacher_username") or "").strip()
        if not teacher_username:
            return
        diagnosis = package.get("diagnosis") if isinstance(package.get("diagnosis"), dict) else {}
        weak_nodes = diagnosis.get("weak_nodes") if isinstance(diagnosis.get("weak_nodes"), list) else []
        completion_rate = float(((package.get("progress") or {}).get("completion_rate") or 0.0))
        self.teacher_event_repo.record_intervention_event(
            package_id=str(package.get("id") or ""),
            teacher_username=teacher_username,
            student_username=str(package.get("student_username") or ""),
            event_type=event_type,
            weak_node_count=len([item for item in weak_nodes if isinstance(item, dict)]),
            completion_rate=completion_rate,
            payload={
                "stage": package.get("stage"),
                "student_status": package.get("student_status"),
                "question_count": len(package.get("questions", []) if isinstance(package.get("questions"), list) else []),
                "score_summary": package.get("score_summary"),
                **(payload or {}),
            },
            created_at=str(package.get("updated_at") or self._now()),
        )

    def _build_intervention_path_refresh(self, package: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "triggered": False,
            "trigger_type": "intervention_completed",
            "path": None,
            "reason": "teacher_intervention_records_evidence_only",
        }

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _package_status(self, package: Dict[str, Any]) -> str:
        stage = str(package.get("stage") or "draft").strip() or "draft"
        student_status = str(package.get("student_status") or "").strip()
        progress = package.get("progress") if isinstance(package.get("progress"), dict) else {}
        if student_status == "declined":
            return "declined"
        if str(progress.get("status") or "") == "completed" or student_status == "completed":
            return "completed"
        if stage == "pushed":
            return "pushed"
        return "draft"

    def _package_title(self, package: Dict[str, Any]) -> str:
        weak_nodes = ((package.get("diagnosis") or {}).get("weak_nodes") or []) if isinstance(package.get("diagnosis"), dict) else []
        if isinstance(weak_nodes, list) and weak_nodes:
            first = weak_nodes[0] if isinstance(weak_nodes[0], dict) else {}
            node_id = str(first.get("node_id") or "").strip()
            if node_id:
                return f"{node_id} intervention package"
        summary = str(package.get("strategy_summary") or "").strip()
        return (summary[:60] if summary else "student weak-node intervention package")

    def _load_json_payload(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                payload = json.loads(value)
                return payload if isinstance(payload, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _load_course_node_candidates(self, course_id: Optional[str]) -> List[Dict[str, Any]]:
        clean_course_id = str(course_id or "").strip()
        if not clean_course_id or not hasattr(self.store, "list_course_node_binding_candidates"):
            return []
        try:
            rows = self.store.list_course_node_binding_candidates(clean_course_id)
        except Exception:
            return []
        return [item for item in rows or [] if isinstance(item, dict) and str(item.get("node_id") or "").strip()]

    def _load_published_quiz_definitions(self, course_id: str) -> List[Dict[str, Any]]:
        clean_course_id = str(course_id or "").strip() or "course_big_data"
        rows: List[Dict[str, Any]] = []
        try:
            with self.store.connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT username, payload_json, updated_at
                        FROM user_states
                        WHERE username LIKE %s
                        """,
                        (f"{QUIZ_DEFINITION_STATE_PREFIX}{clean_course_id}::%",),
                    )
                    rows = [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

        indexed = published_definition_index_from_state_rows(rows, clean_course_id)
        result: List[Dict[str, Any]] = []
        for node_id, definition in indexed.items():
            if not isinstance(definition, dict):
                continue
            result.append(
                {
                    "definition_id": str(definition.get("definition_id") or "").strip(),
                    "quiz_id": str(definition.get("definition_id") or "").strip(),
                    "course_id": clean_course_id,
                    "node_id": str(definition.get("node_id") or node_id or "").strip(),
                    "title": str(definition.get("title") or f"{node_id} 在线测验").strip(),
                    "status": str(definition.get("status") or ""),
                    "question_count": len(definition.get("questions") or []),
                    "published_at": definition.get("published_at"),
                    "updated_at": definition.get("updated_at"),
                }
            )
        return [item for item in result if item["definition_id"] and item["status"] == "published"]

    def get_task_reference_options(self, course_id: str = "course_big_data") -> Dict[str, Any]:
        clean_course_id = str(course_id or "").strip() or "course_big_data"
        resources = []
        try:
            raw_resources = self.store.list_course_resources(clean_course_id) if hasattr(self.store, "list_course_resources") else []
        except Exception:
            raw_resources = []
        for item in raw_resources or []:
            if not isinstance(item, dict):
                continue
            if item.get("is_deleted") or not item.get("is_enabled") or str(item.get("review_status") or "") == "rejected":
                continue
            resources.append(
                {
                    "resource_id": item.get("resource_id"),
                    "course_id": item.get("course_id") or clean_course_id,
                    "node_id": item.get("node_id") or "",
                    "node_name": item.get("node_name"),
                    "title": item.get("title") or item.get("resource_path"),
                    "resource_path": item.get("resource_path") or "",
                    "resource_type": item.get("resource_type") or item.get("resource_source") or "resource",
                }
            )

        try:
            assignments = self.homework_service.repository.list_assignments(status="published", course_id=clean_course_id)
        except Exception:
            assignments = []
        assignment_options = []
        code_options = []
        for item in assignments or []:
            if not isinstance(item, dict):
                continue
            payload = {
                "assignment_id": str(item.get("id") or "").strip(),
                "task_id": str(item.get("id") or "").strip(),
                "title": item.get("title") or item.get("id"),
                "course_id": item.get("course_id") or clean_course_id,
                "node_id": item.get("node_id") or "",
                "node_name": item.get("node_name") or "",
                "assignment_type": item.get("assignment_type") or "",
                "status": item.get("status") or "",
            }
            if not payload["assignment_id"]:
                continue
            assignment_options.append(payload)
            if str(item.get("assignment_type") or "").lower() in {"code", "coding", "code_practice"}:
                code_options.append(payload)

        return {
            "course_id": clean_course_id,
            "resources": resources,
            "assignments": assignment_options,
            "quizzes": self._load_published_quiz_definitions(clean_course_id),
            "code_tasks": code_options,
        }

    def _normalize_node_text(self, value: Any) -> str:
        return re.sub(r"\s+", "", str(value or "").strip()).lower()

    def _resolve_course_node_id(
        self,
        raw_node_id: Any,
        *,
        course_id: Optional[str],
        candidates: Optional[List[Dict[str, Any]]] = None,
        texts: Optional[List[Any]] = None,
        leaf_only: bool = True,
    ) -> Optional[str]:
        clean_node_id = str(raw_node_id or "").strip()
        node_candidates = candidates if candidates is not None else self._load_course_node_candidates(course_id)
        if not node_candidates:
            return clean_node_id or None

        def allowed(item: Dict[str, Any]) -> bool:
            return bool(item.get("is_leaf")) or not leaf_only

        for item in node_candidates:
            if allowed(item) and clean_node_id and str(item.get("node_id") or "").strip() == clean_node_id:
                return str(item.get("node_id") or "").strip()

        search_values = [clean_node_id, *(texts or [])]
        normalized_texts = [self._normalize_node_text(value) for value in search_values if self._normalize_node_text(value)]
        if not normalized_texts:
            return None

        for item in node_candidates:
            if not allowed(item):
                continue
            aliases = [
                str(item.get("node_id") or "").strip(),
                str(item.get("node_name") or "").strip(),
                *[str(part).strip() for part in item.get("node_path") or []],
            ]
            normalized_aliases = [self._normalize_node_text(alias) for alias in aliases if self._normalize_node_text(alias)]
            if any(text == alias for text in normalized_texts for alias in normalized_aliases):
                return str(item.get("node_id") or "").strip()

        for item in node_candidates:
            if not allowed(item):
                continue
            aliases = [
                str(item.get("node_name") or "").strip(),
                *[str(part).strip() for part in item.get("node_path") or []],
            ]
            normalized_aliases = [self._normalize_node_text(alias) for alias in aliases if self._normalize_node_text(alias)]
            if any(alias and alias in text for text in normalized_texts for alias in normalized_aliases):
                return str(item.get("node_id") or "").strip()
        return None

    def _persist_package_to_db(self, package: Dict[str, Any]) -> None:
        package_id = str(package.get("id") or "").strip()
        teacher_username = str(package.get("teacher_username") or "").strip()
        student_username = str(package.get("student_username") or "").strip()
        if not package_id or not teacher_username or not student_username:
            return

        teacher = self.store.get_user("teacher", teacher_username)
        student = self.store.get_user("student", student_username)
        teacher_user_id = int(teacher["user_id"]) if teacher and teacher.get("user_id") else None
        student_user_id = int(student["user_id"]) if student and student.get("user_id") else None
        diagnosis = package.get("diagnosis") if isinstance(package.get("diagnosis"), dict) else {}
        report_id = str(diagnosis.get("report_id") or "").strip() or None
        course_id = str(diagnosis.get("course_id") or "").strip() or None
        status = self._package_status(package)
        pushed_at = self._parse_datetime(package.get("pushed_at"))
        completed_at = self._parse_datetime(package.get("updated_at")) if status == "completed" else None
        now = self._parse_datetime(package.get("updated_at")) or datetime.now()
        node_candidates = self._load_course_node_candidates(course_id)

        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                if report_id:
                    cursor.execute("SELECT report_id FROM diagnosis_reports WHERE report_id=%s", (report_id,))
                    if not cursor.fetchone():
                        report_id = None
                cursor.execute(
                    """
                    INSERT INTO intervention_packages
                    (package_id, teacher_username, teacher_user_id, student_username, student_user_id,
                     course_id, diagnosis_report_id, package_title, status, risk_level,
                     pushed_at, completed_at, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        teacher_username = VALUES(teacher_username),
                        teacher_user_id = VALUES(teacher_user_id),
                        student_username = VALUES(student_username),
                        student_user_id = VALUES(student_user_id),
                        course_id = VALUES(course_id),
                        diagnosis_report_id = VALUES(diagnosis_report_id),
                        package_title = VALUES(package_title),
                        status = VALUES(status),
                        risk_level = VALUES(risk_level),
                        pushed_at = COALESCE(VALUES(pushed_at), pushed_at),
                        completed_at = VALUES(completed_at),
                        payload_json = VALUES(payload_json),
                        updated_at = VALUES(updated_at)
                    """,
                    (
                        package_id,
                        teacher_username,
                        teacher_user_id,
                        student_username,
                        student_user_id,
                        course_id,
                        report_id,
                        self._package_title(package),
                        status,
                        str(diagnosis.get("risk_level") or "").strip() or None,
                        pushed_at,
                        completed_at,
                        json.dumps(package, ensure_ascii=False),
                        self._parse_datetime(package.get("created_at")) or now,
                        now,
                    ),
                )
                cursor.execute("DELETE FROM intervention_package_items WHERE package_id=%s", (package_id,))
                sequence = 0
                concepts = package.get("recommended_concepts") if isinstance(package.get("recommended_concepts"), list) else []
                for concept in concepts:
                    sequence += 1
                    resolved_node_id = self._resolve_course_node_id(
                        concept,
                        course_id=course_id,
                        candidates=node_candidates,
                        texts=[concept],
                    )
                    cursor.execute(
                        """
                        INSERT INTO intervention_package_items
                        (package_id, item_type, course_id, node_id, sequence_order, required, payload_json, created_at, updated_at)
                        VALUES (%s, 'concept_review', %s, %s, %s, 1, %s, %s, %s)
                        """,
                        (
                            package_id,
                            course_id,
                            resolved_node_id,
                            sequence,
                            json.dumps({"concept": concept, "resolved_node_id": resolved_node_id}, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                videos = package.get("recommended_videos") if isinstance(package.get("recommended_videos"), list) else []
                for video in videos:
                    sequence += 1
                    cursor.execute(
                        """
                        INSERT INTO intervention_package_items
                        (package_id, item_type, course_id, reminder_text, sequence_order, required, payload_json, created_at, updated_at)
                        VALUES (%s, 'resource_review', %s, %s, %s, 1, %s, %s, %s)
                        """,
                        (
                            package_id,
                            course_id,
                            str(video or "").strip() or None,
                            sequence,
                            json.dumps({"resource_hint": video}, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                resource_tasks = package.get("resource_tasks") if isinstance(package.get("resource_tasks"), list) else []
                for resource in resource_tasks:
                    if not isinstance(resource, dict):
                        continue
                    sequence += 1
                    resolved_node_id = self._resolve_course_node_id(
                        resource.get("node_id"),
                        course_id=course_id,
                        candidates=node_candidates,
                        texts=[
                            resource.get("title"),
                            resource.get("resource_path"),
                        ],
                    )
                    cursor.execute(
                        """
                        INSERT INTO intervention_package_items
                        (package_id, item_type, course_id, node_id, resource_id, reminder_text, sequence_order, required, payload_json, created_at, updated_at)
                        VALUES (%s, 'resource_review', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            package_id,
                            course_id,
                            resolved_node_id,
                            resource.get("resource_id"),
                            str(resource.get("title") or resource.get("resource_path") or "").strip() or None,
                            sequence,
                            1 if resource.get("required", True) else 0,
                            json.dumps({"resource_task": {**resource, "node_id": resolved_node_id or ""}}, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                assignment_tasks = package.get("assignment_tasks") if isinstance(package.get("assignment_tasks"), list) else []
                for assignment in assignment_tasks:
                    if not isinstance(assignment, dict):
                        continue
                    sequence += 1
                    assignment_course_id = str(assignment.get("course_id") or course_id or "").strip() or None
                    assignment_candidates = node_candidates if assignment_course_id == course_id else self._load_course_node_candidates(assignment_course_id)
                    resolved_node_id = self._resolve_course_node_id(
                        assignment.get("node_id"),
                        course_id=assignment_course_id,
                        candidates=assignment_candidates,
                        texts=[
                            assignment.get("title"),
                            assignment.get("assignment_id"),
                        ],
                    )
                    cursor.execute(
                        """
                        INSERT INTO intervention_package_items
                        (package_id, item_type, course_id, node_id, homework_assignment_id, reminder_text, sequence_order, required, payload_json, created_at, updated_at)
                        VALUES (%s, 'homework_assignment', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            package_id,
                            assignment_course_id,
                            resolved_node_id,
                            str(assignment.get("assignment_id") or "").strip() or None,
                            str(assignment.get("title") or assignment.get("assignment_id") or "").strip() or None,
                            sequence,
                            1 if assignment.get("required", True) else 0,
                            json.dumps({"assignment_task": {**assignment, "node_id": resolved_node_id or ""}}, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                quiz_tasks = package.get("quiz_tasks") if isinstance(package.get("quiz_tasks"), list) else []
                for quiz in quiz_tasks:
                    if not isinstance(quiz, dict):
                        continue
                    sequence += 1
                    quiz_course_id = str(quiz.get("course_id") or course_id or "").strip() or None
                    quiz_candidates = node_candidates if quiz_course_id == course_id else self._load_course_node_candidates(quiz_course_id)
                    resolved_node_id = self._resolve_course_node_id(
                        quiz.get("node_id"),
                        course_id=quiz_course_id,
                        candidates=quiz_candidates,
                        texts=[
                            quiz.get("title"),
                            quiz.get("quiz_id"),
                        ],
                    )
                    cursor.execute(
                        """
                        INSERT INTO intervention_package_items
                        (package_id, item_type, course_id, node_id, reminder_text, quiz_payload_json, sequence_order, required, payload_json, created_at, updated_at)
                        VALUES (%s, 'quiz_task', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            package_id,
                            quiz_course_id,
                            resolved_node_id,
                            str(quiz.get("title") or quiz.get("quiz_id") or "").strip() or None,
                            json.dumps(quiz, ensure_ascii=False),
                            sequence,
                            1 if quiz.get("required", True) else 0,
                            json.dumps({"quiz_task": {**quiz, "node_id": resolved_node_id or ""}}, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                code_tasks = package.get("code_tasks") if isinstance(package.get("code_tasks"), list) else []
                for code_task in code_tasks:
                    if not isinstance(code_task, dict):
                        continue
                    sequence += 1
                    code_course_id = str(code_task.get("course_id") or course_id or "").strip() or None
                    code_candidates = node_candidates if code_course_id == course_id else self._load_course_node_candidates(code_course_id)
                    resolved_node_id = self._resolve_course_node_id(
                        code_task.get("node_id"),
                        course_id=code_course_id,
                        candidates=code_candidates,
                        texts=[
                            code_task.get("title"),
                            code_task.get("task_id"),
                        ],
                    )
                    cursor.execute(
                        """
                        INSERT INTO intervention_package_items
                        (package_id, item_type, course_id, node_id, reminder_text, quiz_payload_json, sequence_order, required, payload_json, created_at, updated_at)
                        VALUES (%s, 'code_practice', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            package_id,
                            code_course_id,
                            resolved_node_id,
                            str(code_task.get("title") or code_task.get("task_id") or "").strip() or None,
                            json.dumps(code_task, ensure_ascii=False),
                            sequence,
                            1 if code_task.get("required", True) else 0,
                            json.dumps({"code_task": {**code_task, "node_id": resolved_node_id or ""}}, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                questions = package.get("questions") if isinstance(package.get("questions"), list) else []
                for question in questions:
                    if not isinstance(question, dict):
                        continue
                    sequence += 1
                    cursor.execute(
                        """
                        INSERT INTO intervention_package_items
                        (package_id, item_type, course_id, quiz_payload_json, sequence_order, required, payload_json, created_at, updated_at)
                        VALUES (%s, 'practice_question', %s, %s, %s, 1, %s, %s, %s)
                        """,
                        (
                            package_id,
                            course_id,
                            json.dumps(question, ensure_ascii=False),
                            sequence,
                            json.dumps({"question_id": question.get("id"), "question_type": question.get("question_type")}, ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                cursor.execute(
                    "DELETE FROM intervention_package_student_records WHERE package_id=%s AND student_username=%s",
                    (package_id, student_username),
                )
                progress = package.get("progress") if isinstance(package.get("progress"), dict) else {}
                score_summary = package.get("score_summary") if isinstance(package.get("score_summary"), dict) else {}
                cursor.execute(
                    """
                    INSERT INTO intervention_package_student_records
                    (package_id, student_username, student_user_id, status, score, feedback,
                     started_at, completed_at, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        package_id,
                        student_username,
                        student_user_id,
                        str(progress.get("status") or package.get("student_status") or "pending"),
                        score_summary.get("average_final_score"),
                        str(package.get("student_note") or "").strip() or None,
                        pushed_at,
                        completed_at,
                        json.dumps(
                            {
                                "progress": progress,
                                "answers": package.get("answers", []),
                                "grades": package.get("grades", []),
                                "score_summary": score_summary,
                            },
                            ensure_ascii=False,
                        ),
                        self._parse_datetime(package.get("created_at")) or now,
                        now,
                    ),
                )

    def _load_packages_from_db(
        self,
        *,
        teacher_username: Optional[str] = None,
        student_username: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []
        if teacher_username:
            clauses.append("teacher_username = %s")
            params.append(teacher_username)
        if student_username:
            clauses.append("student_username = %s")
            params.append(student_username)
        if not clauses:
            return []
        where = " AND ".join(clauses)
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT package_id, status, payload_json, created_at, updated_at, pushed_at, completed_at
                    FROM intervention_packages
                    WHERE {where}
                    ORDER BY updated_at DESC
                    LIMIT 200
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        packages: List[Dict[str, Any]] = []
        for row in rows:
            payload = self._load_json_payload(row.get("payload_json"))
            if not payload:
                payload = {}
            payload.setdefault("id", row.get("package_id"))
            payload.setdefault("stage", "pushed" if row.get("status") in {"pushed", "completed"} else "draft")
            payload["db_status"] = row.get("status")
            payload["db_created_at"] = str(row.get("created_at") or "")
            payload["db_updated_at"] = str(row.get("updated_at") or "")
            payload["db_pushed_at"] = str(row.get("pushed_at") or "")
            payload["db_completed_at"] = str(row.get("completed_at") or "")
            packages.append(payload)
        return packages

    def _merge_packages(self, session_packages: List[Dict[str, Any]], db_packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        for item in db_packages:
            if isinstance(item, dict) and item.get("id"):
                merged[str(item["id"])] = item
        for item in session_packages:
            if isinstance(item, dict) and item.get("id"):
                merged[str(item["id"])] = item
        rows = list(merged.values())
        rows.sort(key=lambda x: str(x.get("updated_at") or x.get("db_updated_at") or ""), reverse=True)
        return rows

    def _normalize_question_type(self, value: str) -> str:
        raw = str(value or "subjective").strip().lower()
        alias_map = {
            "blank": "fill_blank",
            "fillblank": "fill_blank",
            "single": "single_choice",
            "choice": "single_choice",
            "multiple": "multiple_choice",
            "multi_choice": "multiple_choice",
            "programming": "code",
        }
        normalized = alias_map.get(raw, raw)
        if normalized not in {"fill_blank", "single_choice", "multiple_choice", "code", "subjective"}:
            return "subjective"
        return normalized

    def _normalize_question(self, raw: Dict[str, Any], index: int, default_difficulty: str) -> Dict[str, Any]:
        question_type = self._normalize_question_type(str(raw.get("question_type") or "subjective"))
        options = raw.get("options")
        if not isinstance(options, list):
            options = []
        safe_options = [str(item).strip() for item in options if str(item).strip()]
        test_cases = raw.get("test_cases")
        if not isinstance(test_cases, list):
            test_cases = []
        safe_cases = []
        for case in test_cases:
            if not isinstance(case, dict):
                continue
            input_text = str(case.get("input") or "").strip()
            expected_text = str(case.get("expected") or "").strip()
            if not input_text and not expected_text:
                continue
            safe_cases.append({"input": input_text, "expected": expected_text})

        return {
            "id": str(raw.get("id") or f"q-{index + 1}"),
            "title": str(raw.get("title") or f"题目 {index + 1}"),
            "prompt": str(raw.get("prompt") or ""),
            "question_type": question_type,
            "options": safe_options,
            "correct_answer": str(raw.get("correct_answer") or ""),
            "reference_answer": str(raw.get("reference_answer") or ""),
            "rubric": str(raw.get("rubric") or ""),
            "test_cases": safe_cases,
            "difficulty": str(raw.get("difficulty") or default_difficulty or "中等"),
        }

    def _normalize_resource_task(self, raw: Dict[str, Any], index: int) -> Dict[str, Any]:
        return {
            "id": str(raw.get("id") or f"resource-{index + 1}"),
            "resource_id": raw.get("resource_id"),
            "title": str(raw.get("title") or raw.get("resource_path") or f"资源任务 {index + 1}").strip(),
            "resource_path": str(raw.get("resource_path") or "").strip(),
            "resource_type": str(raw.get("resource_type") or "").strip(),
            "node_id": str(raw.get("node_id") or "").strip(),
            "required": bool(raw.get("required", True)),
            "status": str(raw.get("status") or ("completed" if raw.get("completed") else "pending")).strip() or "pending",
            "completed_at": str(raw.get("completed_at") or "").strip(),
            "note": str(raw.get("note") or "").strip(),
        }

    def _normalize_assignment_task(self, raw: Dict[str, Any], index: int) -> Dict[str, Any]:
        assignment_id = str(raw.get("assignment_id") or raw.get("id") or "").strip()
        return {
            "id": assignment_id or f"assignment-{index + 1}",
            "assignment_id": assignment_id,
            "title": str(raw.get("title") or f"作业任务 {index + 1}").strip(),
            "course_id": str(raw.get("course_id") or "").strip(),
            "node_id": str(raw.get("node_id") or "").strip(),
            "required": bool(raw.get("required", True)),
            "status": str(raw.get("status") or ("completed" if raw.get("completed") else "pending")).strip() or "pending",
            "completed_at": str(raw.get("completed_at") or "").strip(),
            "note": str(raw.get("note") or "").strip(),
        }

    def _normalize_quiz_task(self, raw: Dict[str, Any], index: int) -> Dict[str, Any]:
        quiz_id = str(raw.get("quiz_id") or raw.get("definition_id") or raw.get("id") or "").strip()
        return {
            "id": quiz_id or f"quiz-{index + 1}",
            "quiz_id": quiz_id,
            "title": str(raw.get("title") or raw.get("quiz_title") or f"测验任务 {index + 1}").strip(),
            "course_id": str(raw.get("course_id") or "").strip(),
            "node_id": str(raw.get("node_id") or "").strip(),
            "required": bool(raw.get("required", True)),
            "status": str(raw.get("status") or ("completed" if raw.get("completed") else "pending")).strip() or "pending",
            "completed_at": str(raw.get("completed_at") or "").strip(),
            "note": str(raw.get("note") or "").strip(),
        }

    def _normalize_code_task(self, raw: Dict[str, Any], index: int) -> Dict[str, Any]:
        task_id = str(raw.get("task_id") or raw.get("assignment_id") or raw.get("id") or "").strip()
        return {
            "id": task_id or f"code-{index + 1}",
            "task_id": task_id,
            "title": str(raw.get("title") or f"代码练习 {index + 1}").strip(),
            "course_id": str(raw.get("course_id") or "").strip(),
            "node_id": str(raw.get("node_id") or "").strip(),
            "required": bool(raw.get("required", True)),
            "status": str(raw.get("status") or ("completed" if raw.get("completed") else "pending")).strip() or "pending",
            "completed_at": str(raw.get("completed_at") or "").strip(),
            "note": str(raw.get("note") or "").strip(),
        }

    def _build_default_resource_tasks(self, ai_payload: Dict[str, Any], diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_tasks = ai_payload.get("resource_tasks")
        if isinstance(raw_tasks, list):
            return [
                self._normalize_resource_task(item, index)
                for index, item in enumerate(raw_tasks)
                if isinstance(item, dict)
            ]
        videos = ai_payload.get("recommended_videos") if isinstance(ai_payload.get("recommended_videos"), list) else []
        weak_nodes = diagnosis.get("weak_nodes") if isinstance(diagnosis.get("weak_nodes"), list) else []
        fallback_node = ""
        if weak_nodes and isinstance(weak_nodes[0], dict):
            fallback_node = str(weak_nodes[0].get("node_id") or "").strip()
        tasks = []
        for index, video in enumerate(videos):
            title = str(video or "").strip()
            if not title:
                continue
            tasks.append(
                self._normalize_resource_task(
                    {
                        "title": title,
                        "resource_path": title if title.startswith(("http://", "https://")) else "",
                        "resource_type": "video",
                        "node_id": fallback_node,
                        "required": True,
                    },
                    index,
                )
            )
        return tasks

    def _build_default_assignment_tasks(self, ai_payload: Dict[str, Any], diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_tasks = ai_payload.get("assignment_tasks")
        if isinstance(raw_tasks, list):
            return [
                self._normalize_assignment_task(item, index)
                for index, item in enumerate(raw_tasks)
                if isinstance(item, dict)
            ]
        return []

    def _build_default_quiz_tasks(self, ai_payload: Dict[str, Any], diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_tasks = ai_payload.get("quiz_tasks")
        if isinstance(raw_tasks, list):
            return [
                self._normalize_quiz_task(item, index)
                for index, item in enumerate(raw_tasks)
                if isinstance(item, dict)
            ]
        return []

    def _build_default_code_tasks(self, ai_payload: Dict[str, Any], diagnosis: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_tasks = ai_payload.get("code_tasks")
        if isinstance(raw_tasks, list):
            return [
                self._normalize_code_task(item, index)
                for index, item in enumerate(raw_tasks)
                if isinstance(item, dict)
            ]
        return []

    def _build_student_answer_entries(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = self._now()
        entries = []
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            qid = str(question.get("id") or f"q-{index + 1}")
            entries.append(
                {
                    "question_id": qid,
                    "question_title": str(question.get("title") or f"题目 {index + 1}"),
                    "question_type": self._normalize_question_type(str(question.get("question_type") or "subjective")),
                    "answer": "",
                    "note": "",
                    "status": "pending",
                    "updated_at": now,
                }
            )
        return entries

    def _build_grade_entries(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = self._now()
        grades = []
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            qid = str(question.get("id") or f"q-{index + 1}")
            grades.append(
                {
                    "question_id": qid,
                    "question_title": str(question.get("title") or f"题目 {index + 1}"),
                    "question_type": self._normalize_question_type(str(question.get("question_type") or "subjective")),
                    "ai_score": None,
                    "ai_feedback": "",
                    "ai_detail": {},
                    "teacher_score": None,
                    "teacher_comment": "",
                    "final_score": None,
                    "status": "pending",
                    "ai_graded_at": None,
                    "teacher_graded_at": None,
                    "updated_at": now,
                }
            )
        return grades

    def _split_tokens(self, text: str) -> List[str]:
        raw = re.split(r"[\s,锛屻€傦紱;銆?锛歕n\r\t]+", str(text or ""))
        return [token.strip() for token in raw if token.strip()]

    def _normalize_choice_answer(self, answer: str) -> str:
        items = [token.upper() for token in self._split_tokens(answer)]
        return ",".join(sorted(set(items)))

    def _grade_textual(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        clean_answer = str(answer or "").strip()
        reference = str(question.get("reference_answer") or "").strip()
        rubric = str(question.get("rubric") or "").strip()

        length_part = min(len(clean_answer) / 220.0, 1.0)
        structure_part = 1.0 if any(flag in clean_answer.lower() for flag in ["step", "first", "then", "finally", "summary", "1.", "2."]) else 0.0
        ref_tokens = [token for token in self._split_tokens(reference) if len(token) >= 2][:12]
        hit_count = sum(1 for token in ref_tokens if token in clean_answer) if ref_tokens else 0
        keyword_part = (hit_count / len(ref_tokens)) if ref_tokens else 0.0

        criteria = [
            {
                "name": "content completeness",
                "score": round(length_part * 40, 2),
                "full_score": 40,
                "reason": f"answer length and elaboration, length={len(clean_answer)}",
            },
            {
                "name": "key point match",
                "score": round(keyword_part * 40, 2),
                "full_score": 40,
                "reason": f"matched reference tokens {hit_count}/{len(ref_tokens) if ref_tokens else 0}",
            },
            {
                "name": "expression structure",
                "score": 20.0 if structure_part > 0 else 8.0,
                "full_score": 20,
                "reason": "stepwise expression detected" if structure_part > 0 else "stepwise expression not obvious",
            },
        ]
        total = round(sum(item["score"] for item in criteria), 2)
        feedback = f"text question auto score {total}/100."
        if rubric:
            feedback += " Teacher rubric was considered."
        return {"score": total, "feedback": feedback, "detail": {"total_score": total, "criteria": criteria}}

    def _grade_fill_blank(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        expected = str(question.get("correct_answer") or question.get("reference_answer") or "").strip()
        normalized_expected = " ".join(expected.lower().split())
        normalized_answer = " ".join(str(answer or "").lower().split())
        is_correct = normalized_expected != "" and normalized_answer == normalized_expected
        score = 100.0 if is_correct else 0.0
        criteria = [{"name": "answer match", "score": score, "full_score": 100, "reason": "exact match" if is_correct else "not matched"}]
        feedback = "fill blank correct" if is_correct else f"fill blank mismatch, expected: {expected or '-'}"
        return {"score": score, "feedback": feedback, "detail": {"total_score": score, "criteria": criteria, "match": {"normalized_answer": normalized_answer, "expected": normalized_expected, "is_correct": is_correct}}}

    def _grade_choice(self, question: Dict[str, Any], answer: str, multiple: bool) -> Dict[str, Any]:
        expected = str(question.get("correct_answer") or "").strip()
        normalized_expected = self._normalize_choice_answer(expected)
        normalized_answer = self._normalize_choice_answer(answer)
        if not normalized_expected:
            return self._grade_textual(question, answer)
        if multiple:
            expected_set = set(normalized_expected.split(",")) if normalized_expected else set()
            answer_set = set(normalized_answer.split(",")) if normalized_answer else set()
            hit = len(expected_set & answer_set)
            wrong = len(answer_set - expected_set)
            miss = len(expected_set - answer_set)
            raw = max(0.0, (hit / len(expected_set)) - (wrong * 0.25)) if expected_set else 0.0
            score = round(min(100.0, raw * 100.0), 2)
            reason = f"hit={hit}, miss={miss}, wrong={wrong}"
            is_correct = miss == 0 and wrong == 0 and len(expected_set) > 0
        else:
            is_correct = normalized_expected == normalized_answer and normalized_expected != ""
            score = 100.0 if is_correct else 0.0
            reason = "single choice matched" if is_correct else f"expected {normalized_expected}, got {normalized_answer or '-'}"
        criteria = [{"name": "choice match", "score": score, "full_score": 100, "reason": reason}]
        feedback = "choice correct" if is_correct else "choice not fully matched"
        return {"score": score, "feedback": feedback, "detail": {"total_score": score, "criteria": criteria, "match": {"normalized_answer": normalized_answer, "expected": normalized_expected, "is_correct": is_correct}}}

    def _grade_code(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        test_cases = question.get("test_cases")
        if not isinstance(test_cases, list) or not test_cases:
            return self._grade_textual(question, answer)
        code_text = str(answer or "").strip()
        case_details: List[Dict[str, Any]] = []
        passed = 0
        for index, case in enumerate(test_cases):
            if not isinstance(case, dict):
                continue
            expected = str(case.get("expected") or "").strip()
            ok = expected != "" and expected in code_text
            if ok:
                passed += 1
            case_details.append({"index": index + 1, "ok": ok, "input": str(case.get("input") or ""), "expected": expected, "actual": code_text[:120], "reason": "expected fragment found" if ok else "expected fragment missing"})
        total_cases = len(case_details)
        score = round((passed / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
        criteria = [{"name": "test pass rate", "score": score, "full_score": 100, "reason": f"passed {passed}/{total_cases}"}]
        feedback = f"code question auto score {score}/100, passed {passed}/{total_cases}."
        return {"score": score, "feedback": feedback, "detail": {"total_score": score, "criteria": criteria, "code": {"case_passed": passed, "case_total": total_cases, "case_details": case_details}}}

    def _compute_ai_score_feedback(self, question: Dict[str, Any], answer: str) -> Dict[str, Any]:
        clean_answer = str(answer or "").strip()
        if not clean_answer:
            return {
                "score": 0.0,
                "feedback": "not answered",
                "detail": {
                    "total_score": 0.0,
                    "criteria": [{"name": "answer status", "score": 0.0, "full_score": 100, "reason": "no answer submitted"}],
                },
            }
        question_type = self._normalize_question_type(str(question.get("question_type") or "subjective"))
        if question_type == "fill_blank":
            return self._grade_fill_blank(question, clean_answer)
        if question_type == "single_choice":
            return self._grade_choice(question, clean_answer, multiple=False)
        if question_type == "multiple_choice":
            return self._grade_choice(question, clean_answer, multiple=True)
        if question_type == "code":
            return self._grade_code(question, clean_answer)
        return self._grade_textual(question, clean_answer)


    def _ensure_package_struct(self, package: Dict[str, Any]) -> None:
        package["resource_tasks"] = [
            self._normalize_resource_task(item, index)
            for index, item in enumerate(package.get("resource_tasks") if isinstance(package.get("resource_tasks"), list) else [])
            if isinstance(item, dict)
        ]
        package["assignment_tasks"] = [
            self._normalize_assignment_task(item, index)
            for index, item in enumerate(package.get("assignment_tasks") if isinstance(package.get("assignment_tasks"), list) else [])
            if isinstance(item, dict)
        ]
        package["quiz_tasks"] = [
            self._normalize_quiz_task(item, index)
            for index, item in enumerate(package.get("quiz_tasks") if isinstance(package.get("quiz_tasks"), list) else [])
            if isinstance(item, dict)
        ]
        package["code_tasks"] = [
            self._normalize_code_task(item, index)
            for index, item in enumerate(package.get("code_tasks") if isinstance(package.get("code_tasks"), list) else [])
            if isinstance(item, dict)
        ]
        questions = package.get("questions") if isinstance(package.get("questions"), list) else []
        answers = package.get("answers")
        grades = package.get("grades")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(questions)
            package["answers"] = answers
        if not isinstance(grades, list):
            grades = self._build_grade_entries(questions)
            package["grades"] = grades

        answer_map = {str(item.get("question_id") or ""): item for item in answers if isinstance(item, dict)}
        grade_map = {str(item.get("question_id") or ""): item for item in grades if isinstance(item, dict)}
        now = self._now()
        for index, question in enumerate(questions):
            if not isinstance(question, dict):
                continue
            qid = str(question.get("id") or f"q-{index + 1}")
            normalized_type = self._normalize_question_type(str(question.get("question_type") or "subjective"))
            if qid not in answer_map:
                answers.append(
                    {
                        "question_id": qid,
                        "question_title": str(question.get("title") or f"题目 {index + 1}"),
                        "question_type": normalized_type,
                        "answer": "",
                        "note": "",
                        "status": "pending",
                        "updated_at": now,
                    }
                )
            else:
                answer_map[qid]["question_title"] = str(question.get("title") or answer_map[qid].get("question_title") or f"题目 {index + 1}")
                answer_map[qid]["question_type"] = normalized_type
            if qid not in grade_map:
                grades.append(
                    {
                        "question_id": qid,
                        "question_title": str(question.get("title") or f"题目 {index + 1}"),
                        "question_type": normalized_type,
                        "ai_score": None,
                        "ai_feedback": "",
                        "ai_detail": {},
                        "teacher_score": None,
                        "teacher_comment": "",
                        "final_score": None,
                        "status": "pending",
                        "ai_graded_at": None,
                        "teacher_graded_at": None,
                        "updated_at": now,
                    }
                )
            else:
                grade_map[qid]["question_title"] = str(question.get("title") or grade_map[qid].get("question_title") or f"题目 {index + 1}")
                grade_map[qid]["question_type"] = normalized_type
                if not isinstance(grade_map[qid].get("ai_detail"), dict):
                    grade_map[qid]["ai_detail"] = {}
        package["answers"] = answers
        package["grades"] = grades

    def _structured_task_counts(self, package: Dict[str, Any]) -> Dict[str, int]:
        self._ensure_package_struct(package)
        total = 0
        completed = 0
        for group_name in ("resource_tasks", "assignment_tasks", "quiz_tasks", "code_tasks"):
            group = package.get(group_name) if isinstance(package.get(group_name), list) else []
            for item in group:
                if not isinstance(item, dict) or item.get("required") is False:
                    continue
                total += 1
                if str(item.get("status") or "").strip() == "completed":
                    completed += 1
        return {"total": total, "completed": completed}

    def _auto_grade_single_question(self, package: Dict[str, Any], question_id: str, *, now: Optional[str] = None) -> None:
        self._ensure_package_struct(package)
        now_text = now or self._now()
        question_map = {
            str(item.get("id") or ""): item
            for item in (package.get("questions") if isinstance(package.get("questions"), list) else [])
            if isinstance(item, dict)
        }
        answer_rows = package.get("answers") if isinstance(package.get("answers"), list) else []
        grade_rows = package.get("grades") if isinstance(package.get("grades"), list) else []
        answer_row = next((item for item in answer_rows if isinstance(item, dict) and str(item.get("question_id") or "") == question_id), None)
        grade_row = next((item for item in grade_rows if isinstance(item, dict) and str(item.get("question_id") or "") == question_id), None)
        question = question_map.get(question_id)
        if not isinstance(answer_row, dict) or not isinstance(grade_row, dict) or not isinstance(question, dict):
            return

        answer_text = str(answer_row.get("answer") or "").strip()
        if not answer_text:
            grade_row["ai_score"] = None
            grade_row["ai_feedback"] = ""
            grade_row["ai_detail"] = {}
            grade_row["status"] = "pending"
            grade_row["final_score"] = grade_row.get("teacher_score")
            grade_row["updated_at"] = now_text
            return

        judged = self._compute_ai_score_feedback(question, answer_text)
        grade_row["question_type"] = self._normalize_question_type(str(question.get("question_type") or "subjective"))
        grade_row["ai_score"] = judged["score"]
        grade_row["ai_feedback"] = judged["feedback"]
        grade_row["ai_detail"] = judged.get("detail") or {}
        grade_row["ai_graded_at"] = now_text
        grade_row["status"] = "ai_graded" if grade_row.get("teacher_score") is None else "teacher_graded"
        grade_row["final_score"] = grade_row.get("teacher_score")
        if grade_row.get("final_score") is None:
            grade_row["final_score"] = grade_row.get("ai_score")
        grade_row["updated_at"] = now_text

    def _recompute_score_summary(self, package: Dict[str, Any], *, now: Optional[str] = None) -> Dict[str, Any]:
        self._ensure_package_struct(package)
        now_text = now or self._now()
        grade_rows = package.get("grades") if isinstance(package.get("grades"), list) else []
        final_scores: List[float] = []
        ai_scores: List[float] = []
        teacher_scores: List[float] = []
        graded_questions = 0
        for row in grade_rows:
            if not isinstance(row, dict):
                continue
            ai_score = row.get("ai_score")
            teacher_score = row.get("teacher_score")
            final_score = row.get("final_score")
            if isinstance(ai_score, (int, float)):
                ai_scores.append(float(ai_score))
            if isinstance(teacher_score, (int, float)):
                teacher_scores.append(float(teacher_score))
            if isinstance(final_score, (int, float)):
                final_scores.append(float(final_score))
                graded_questions += 1
        question_count = len([x for x in grade_rows if isinstance(x, dict)])
        summary = {
            "question_count": question_count,
            "graded_questions": graded_questions,
            "average_final_score": round(sum(final_scores) / len(final_scores), 2) if final_scores else None,
            "average_ai_score": round(sum(ai_scores) / len(ai_scores), 2) if ai_scores else None,
            "average_teacher_score": round(sum(teacher_scores) / len(teacher_scores), 2) if teacher_scores else None,
            "updated_at": now_text,
        }
        package["score_summary"] = summary
        return summary

    def _recompute_progress(self, package: Dict[str, Any], *, now: Optional[str] = None) -> Dict[str, Any]:
        now_text = now or self._now()
        self._ensure_package_struct(package)
        answers = package.get("answers")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(
                package.get("questions") if isinstance(package.get("questions"), list) else []
            )
            package["answers"] = answers

        normalized_answers = []
        for item in answers:
            if not isinstance(item, dict):
                continue
            answer_text = str(item.get("answer") or "").strip()
            normalized_answers.append(
                {
                    "question_id": str(item.get("question_id") or ""),
                    "question_title": str(item.get("question_title") or ""),
                    "question_type": self._normalize_question_type(str(item.get("question_type") or "subjective")),
                    "answer": answer_text,
                    "note": str(item.get("note") or ""),
                    "status": "completed" if answer_text else "pending",
                    "updated_at": str(item.get("updated_at") or now_text),
                }
            )
        package["answers"] = normalized_answers

        total_questions = len(normalized_answers)
        answered_questions = sum(1 for item in normalized_answers if str(item.get("answer") or "").strip())
        structured_counts = self._structured_task_counts(package)
        total_structured_tasks = int(structured_counts.get("total") or 0)
        completed_structured_tasks = int(structured_counts.get("completed") or 0)
        total_items = total_questions + total_structured_tasks
        completed_items = answered_questions + completed_structured_tasks
        completion_rate = round((completed_items / total_items), 4) if total_items > 0 else 0.0

        current_status = str(package.get("student_status") or "pending")
        if current_status == "declined":
            derived_status = "declined"
        elif completion_rate >= 1 and total_items > 0:
            derived_status = "completed"
        elif completion_rate > 0:
            derived_status = "in_progress"
        elif current_status in {"accepted", "in_progress", "completed"}:
            derived_status = "accepted"
        else:
            derived_status = current_status

        package["student_status"] = derived_status
        progress = {
            "completion_rate": completion_rate,
            "answered_questions": answered_questions,
            "total_questions": total_questions,
            "completed_structured_tasks": completed_structured_tasks,
            "total_structured_tasks": total_structured_tasks,
            "completed_items": completed_items,
            "total_items": total_items,
            "status": derived_status,
            "updated_at": now_text,
        }
        package["progress"] = progress
        self._recompute_score_summary(package, now=now_text)
        return progress

    def _resolve_teacher_students(self, teacher_session: Dict[str, Any]) -> List[Dict[str, Any]]:
        teacher_identifier = (
            str(teacher_session.get("user_id") or "").strip()
            or str(teacher_session.get("login_id") or "").strip()
            or str(teacher_session.get("username") or "").strip()
        )
        linked = self.store.list_teacher_students(teacher_identifier)
        if linked:
            return linked
        teacher_username = str(teacher_session.get("username") or "").strip()
        fallback = []
        for student in self.store.list_users("student"):
            if str(student.get("teacher") or "").strip() == teacher_username:
                fallback.append(
                    {
                        "student_username": str(student.get("username") or ""),
                        "student_user_id": student.get("user_id"),
                        "student_payload": student,
                    }
                )
        return fallback

    def _calc_weak_nodes(self, twin_profile: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not twin_profile:
            return []
        weak_nodes: List[Dict[str, Any]] = []
        nodes = twin_profile.get("knowledge_nodes") if isinstance(twin_profile, dict) else []
        if not isinstance(nodes, list):
            nodes = []
        for item in nodes:
            if not isinstance(item, dict):
                continue
            mastery = float(item.get("mastery_score") or 0)
            progress = float(item.get("progress") or 0)
            quiz_score_raw = item.get("quiz_score")
            quiz_score = float(quiz_score_raw) if isinstance(quiz_score_raw, (int, float)) else None
            weak_reason: List[str] = []
            if mastery < 60:
                weak_reason.append("low mastery")
            if progress < 60:
                weak_reason.append("slow progress")
            if quiz_score is not None and quiz_score < 60:
                weak_reason.append("low quiz score")
            if not weak_reason:
                continue
            weak_nodes.append(
                {
                    "node_id": str(item.get("node_id") or ""),
                    "mastery_score": round(mastery, 2),
                    "progress": round(progress, 2),
                    "quiz_score": round(quiz_score, 2) if quiz_score is not None else None,
                    "reason": "; ".join(weak_reason),
                }
            )
        weak_nodes.sort(key=lambda x: (x.get("mastery_score", 0), x.get("progress", 0)))
        return weak_nodes[:6]

    def get_students_overview(self, teacher_session: Dict[str, Any]) -> Dict[str, Any]:
        teacher_username = str(teacher_session.get("username") or "")
        linked = self._resolve_teacher_students(teacher_session)
        items: List[Dict[str, Any]] = []
        for row in linked:
            student_username = str(row.get("student_username") or "").strip()
            if not student_username:
                continue
            twin = self.store.get_twin_profile(student_username)
            weak_nodes = self._calc_weak_nodes(twin)
            homework = self.homework_service.get_student_twin_homework_snapshot(
                student_username=student_username,
                assignment_id=None,
                teacher_owner=teacher_username,
            )
            items.append(
                {
                    "student_username": student_username,
                    "student_user_id": row.get("student_user_id"),
                    "overall_mastery": round(float((twin or {}).get("overall_mastery") or 0), 2),
                    "weak_node_count": len(weak_nodes),
                    "weak_nodes_preview": weak_nodes[:3],
                    "homework_submission_count": int(homework.get("submission_count") or 0),
                    "homework_average_score": homework.get("average_score"),
                }
            )
        return {
            "teacher_username": teacher_username,
            "students": items,
        }

    def diagnose_students(self, teacher_session: Dict[str, Any], student_usernames: Optional[List[str]] = None) -> Dict[str, Any]:
        teacher_username = str(teacher_session.get("username") or "")
        linked = self._resolve_teacher_students(teacher_session)
        allowed = {str(item.get("student_username") or "").strip() for item in linked}
        requested = [str(item or "").strip() for item in (student_usernames or []) if str(item or "").strip()]
        target_students = requested if requested else sorted([name for name in allowed if name])

        diagnosis_service = StudentDiagnosisService()
        diagnosis: List[Dict[str, Any]] = []
        for student_username in target_students:
            if student_username not in allowed:
                continue
            twin = self.store.get_twin_profile(student_username)
            weak_nodes = self._calc_weak_nodes(twin)
            formal_diagnosis: Dict[str, Any] = {}
            try:
                formal_diagnosis = diagnosis_service.generate_student_diagnosis(
                    student_username,
                    course_id=None,
                    persist=False,
                )
            except Exception:
                formal_diagnosis = {}
            teacher_view = formal_diagnosis.get("teacher_view") if isinstance(formal_diagnosis.get("teacher_view"), dict) else {}
            homework = self.homework_service.get_student_twin_homework_snapshot(
                student_username=student_username,
                assignment_id=None,
                teacher_owner=teacher_username,
            )
            diagnosis.append(
                {
                    "student_username": student_username,
                    "overall_mastery": round(float((twin or {}).get("overall_mastery") or 0), 2),
                    "weak_nodes": weak_nodes,
                    "diagnosis_report_id": formal_diagnosis.get("report_id"),
                    "course_id": formal_diagnosis.get("course_id"),
                    "evidence_level": formal_diagnosis.get("evidence_level"),
                    "confidence": formal_diagnosis.get("confidence"),
                    "evidence_timeline": teacher_view.get("evidence_timeline") or [],
                    "homework_snapshot": {
                        "submission_count": int(homework.get("submission_count") or 0),
                        "graded_count": int(homework.get("graded_count") or 0),
                        "average_score": homework.get("average_score"),
                    },
                }
            )
        return {"teacher_username": teacher_username, "diagnosis": diagnosis}

    def _generate_with_ai(
        self,
        *,
        teacher_username: str,
        student_username: str,
        diagnosis: Dict[str, Any],
        question_count: int,
        difficulty: str,
    ) -> Dict[str, Any]:
        if not (self.model_name and self.api_key):
            return {}
        prompt = (
            "You are a teaching intervention design assistant. Return a strict JSON object only.\n"
            "Fields: strategy_summary, recommended_concepts, recommended_videos, resource_tasks, assignment_tasks, quiz_tasks, code_tasks, questions.\n"
            "Task arrays should reference student-online tasks when possible and include title, course_id, node_id, required.\n"
            f"Generate {question_count} practice questions with fields title,prompt,question_type,options,correct_answer,reference_answer,rubric,test_cases,difficulty.\n"
            "question_type must be one of fill_blank,single_choice,multiple_choice,code,subjective.\n"
            f"teacher={teacher_username}\n"
            f"student={student_username}\n"
            f"difficulty={difficulty}\n"
            f"diagnosis={json.dumps(diagnosis, ensure_ascii=False)}"
        )
        try:
            import httpx

            llm = ChatOpenAI(
                model=self.model_name,
                temperature=0.2,
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=20,
                max_retries=0,
                http_client=httpx.Client(verify=False, timeout=20),
            )
            response = llm.invoke(prompt)
        except Exception:
            return {}
        payload = self._extract_json_object(getattr(response, "content", ""))
        try:
            self.llm_logger.log_llm_call(
                messages=[{"role": "user", "content": prompt}],
                response=response,
                model=self.model_name,
                module="TeacherInterventionModule.service",
                metadata={"function": "generate_intervention_draft"},
                username=teacher_username,
            )
        except Exception:
            pass
        return payload if isinstance(payload, dict) else {}

    def _build_heuristic_draft(
        self,
        *,
        diagnosis: Dict[str, Any],
        question_count: int,
        difficulty: str,
    ) -> Dict[str, Any]:
        weak_nodes = diagnosis.get("weak_nodes") if isinstance(diagnosis, dict) else []
        if not isinstance(weak_nodes, list):
            weak_nodes = []
        weak_node_ids = [str(item.get("node_id") or "") for item in weak_nodes if isinstance(item, dict) and item.get("node_id")]
        concepts = weak_node_ids[:4] or ["核心概念回顾", "关键题型巩固"]
        course_id = str(diagnosis.get("course_id") or "course_big_data") if isinstance(diagnosis, dict) else "course_big_data"
        videos = [f"{name} 短视频复习" for name in concepts[:3]]
        questions = []
        type_cycle = ["fill_blank", "single_choice", "code", "subjective"]
        for idx in range(question_count):
            focus = concepts[idx % len(concepts)] if concepts else "basic review"
            q_type = type_cycle[idx % len(type_cycle)]
            base_question = {
                "title": f"{focus} 练习 {idx + 1}",
                "difficulty": difficulty,
                "reference_answer": f"答案应说明 {focus} 的定义、关键步骤和常见错误。",
                "rubric": "按正确性、完整性和表达清晰度评分。",
                "options": [],
                "correct_answer": "",
                "test_cases": [],
            }
            if q_type == "fill_blank":
                base_question.update({"question_type": "fill_blank", "prompt": f"填空：{focus} 的核心要点是 ____。", "correct_answer": f"{focus}"})
            elif q_type == "single_choice":
                base_question.update({"question_type": "single_choice", "prompt": f"以下哪一项最能描述 {focus}？", "options": ["A. 正确定义", "B. 常见误解", "C. 无关内容", "D. 都不正确"], "correct_answer": "A"})
            elif q_type == "code":
                base_question.update({"question_type": "code", "prompt": f"围绕 {focus} 编写一个小函数，并给出预期输出。", "test_cases": [{"input": "sample", "expected": "ok"}], "correct_answer": "ok"})
            else:
                base_question.update({"question_type": "subjective", "prompt": f"请分步骤说明 {focus}，并列出一个常见错误。"})
            questions.append(base_question)
        return {
            "strategy_summary": "先补齐薄弱概念，再完成在线任务和短练习，最后根据完成情况复盘。",
            "recommended_concepts": concepts,
            "recommended_videos": videos,
            "quiz_tasks": [
                {"quiz_id": f"quiz-{concepts[0]}", "title": f"{concepts[0]} 快速测验", "course_id": course_id, "node_id": concepts[0], "required": True}
            ] if concepts else [],
            "code_tasks": [
                {"task_id": f"code-{concepts[0]}", "title": f"{concepts[0]} 代码练习", "course_id": course_id, "node_id": concepts[0], "required": True}
            ] if concepts else [],
            "questions": questions,
        }

    def generate_intervention_draft(
        self,
        *,
        teacher_session: Dict[str, Any],
        student_username: str,
        question_count: int,
        difficulty: str,
    ) -> Dict[str, Any]:
        teacher_username = str(teacher_session.get("username") or "").strip()
        allowed_students = {
            str(item.get("student_username") or "").strip()
            for item in self._resolve_teacher_students(teacher_session)
        }
        if student_username not in allowed_students:
            raise PermissionError("该学生不在当前教师管理范围内")

        diagnosis_result = self.diagnose_students(teacher_session, [student_username])
        diagnosis = (diagnosis_result.get("diagnosis") or [{}])[0]
        ai_payload = self._generate_with_ai(
            teacher_username=teacher_username,
            student_username=student_username,
            diagnosis=diagnosis,
            question_count=question_count,
            difficulty=difficulty,
        )
        if not ai_payload:
            ai_payload = self._build_heuristic_draft(
                diagnosis=diagnosis,
                question_count=question_count,
                difficulty=difficulty,
            )

        questions = ai_payload.get("questions")
        if not isinstance(questions, list):
            questions = []
        safe_questions = []
        for index, item in enumerate(questions):
            if not isinstance(item, dict):
                continue
            safe_questions.append(self._normalize_question(item, index, difficulty))

        package_id = uuid4().hex
        now = self._now()
        package = {
            "id": package_id,
            "teacher_username": teacher_username,
            "student_username": student_username,
            "stage": "draft",
            "strategy_summary": str(ai_payload.get("strategy_summary") or ""),
            "recommended_concepts": [str(x) for x in ai_payload.get("recommended_concepts", []) if str(x).strip()],
            "recommended_videos": [str(x) for x in ai_payload.get("recommended_videos", []) if str(x).strip()],
            "resource_tasks": self._build_default_resource_tasks(ai_payload, diagnosis),
            "assignment_tasks": self._build_default_assignment_tasks(ai_payload, diagnosis),
            "quiz_tasks": self._build_default_quiz_tasks(ai_payload, diagnosis),
            "code_tasks": self._build_default_code_tasks(ai_payload, diagnosis),
            "questions": safe_questions,
            "answers": self._build_student_answer_entries(safe_questions),
            "grades": self._build_grade_entries(safe_questions),
            "diagnosis": diagnosis,
            "student_status": "pending",
            "student_note": "",
            "progress": {
                "completion_rate": 0,
                "answered_questions": 0,
                "total_questions": len(safe_questions),
                "status": "pending",
                "updated_at": now,
            },
            "created_at": now,
            "updated_at": now,
            "pushed_at": None,
        }
        self._recompute_progress(package, now=now)
        self._recompute_score_summary(package, now=now)
        teacher_state = self._get_user_module_state(teacher_username)
        packages = teacher_state.get("packages")
        if not isinstance(packages, list):
            packages = []
        packages.insert(0, package)
        teacher_state["packages"] = packages
        self._set_user_module_state(teacher_username, teacher_state)
        self._persist_package_to_db(package)
        self._record_intervention_event(
            package,
            "draft_generated",
            payload={"difficulty": difficulty, "question_count": len(safe_questions)},
        )
        return package

    def list_teacher_packages(self, teacher_username: str) -> List[Dict[str, Any]]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        rows = self._merge_packages(
            [item for item in packages if isinstance(item, dict)],
            self._load_packages_from_db(teacher_username=teacher_username),
        )
        for item in rows:
            self._recompute_progress(item)
        return rows

    def get_teacher_package(self, teacher_username: str, package_id: str) -> Dict[str, Any]:
        packages = self.list_teacher_packages(teacher_username)
        for item in packages:
            if str(item.get("id")) == package_id:
                return item
        raise ValueError("任务包不存在")

    def update_teacher_package(
        self,
        *,
        teacher_username: str,
        package_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")
        if str(target.get("stage") or "") != "draft":
            raise ValueError("仅草稿状态可编辑")

        target["strategy_summary"] = str(updates.get("strategy_summary") or "")
        target["recommended_concepts"] = [str(x) for x in updates.get("recommended_concepts", []) if str(x).strip()]
        target["recommended_videos"] = [str(x) for x in updates.get("recommended_videos", []) if str(x).strip()]
        target["resource_tasks"] = [
            self._normalize_resource_task(item, idx)
            for idx, item in enumerate(updates.get("resource_tasks", []))
            if isinstance(item, dict)
        ]
        target["assignment_tasks"] = [
            self._normalize_assignment_task(item, idx)
            for idx, item in enumerate(updates.get("assignment_tasks", []))
            if isinstance(item, dict)
        ]
        target["quiz_tasks"] = [
            self._normalize_quiz_task(item, idx)
            for idx, item in enumerate(updates.get("quiz_tasks", []))
            if isinstance(item, dict)
        ]
        target["code_tasks"] = [
            self._normalize_code_task(item, idx)
            for idx, item in enumerate(updates.get("code_tasks", []))
            if isinstance(item, dict)
        ]
        target["questions"] = [
            self._normalize_question(q, idx, str(q.get("difficulty") or "中等"))
            for idx, q in enumerate(updates.get("questions", []))
            if isinstance(q, dict)
        ]
        target["answers"] = self._build_student_answer_entries(target["questions"])
        target["grades"] = self._build_grade_entries(target["questions"])
        self._recompute_progress(target)
        target["updated_at"] = self._now()
        self._set_user_module_state(teacher_username, state)
        self._persist_package_to_db(target)
        return target

    def push_package_to_student(self, *, teacher_username: str, package_id: str) -> Dict[str, Any]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        student_username = str(target.get("student_username") or "").strip()
        if not student_username:
            raise ValueError("package missing student username")

        now = self._now()
        target["stage"] = "pushed"
        target["student_status"] = "pending"
        target["answers"] = self._build_student_answer_entries(target.get("questions", []))
        target["grades"] = self._build_grade_entries(target.get("questions", []))
        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        target["pushed_at"] = now
        self._set_user_module_state(teacher_username, state)
        self._persist_package_to_db(target)

        student_state = self._get_user_module_state(student_username)
        student_packages = student_state.get("packages")
        if not isinstance(student_packages, list):
            student_packages = []
        student_copy = {
            "id": target.get("id"),
            "teacher_username": target.get("teacher_username"),
            "student_username": student_username,
            "strategy_summary": target.get("strategy_summary", ""),
            "recommended_concepts": target.get("recommended_concepts", []),
            "recommended_videos": target.get("recommended_videos", []),
            "resource_tasks": target.get("resource_tasks", []),
            "assignment_tasks": target.get("assignment_tasks", []),
            "quiz_tasks": target.get("quiz_tasks", []),
            "code_tasks": target.get("code_tasks", []),
            "questions": target.get("questions", []),
            "answers": target.get("answers", []),
            "grades": target.get("grades", []),
            "diagnosis": target.get("diagnosis", {}),
            "student_status": "pending",
            "student_note": "",
            "progress": {
                "completion_rate": 0,
                "answered_questions": 0,
                "total_questions": len(target.get("questions", []) if isinstance(target.get("questions"), list) else []),
                "status": "pending",
                "updated_at": now,
            },
            "created_at": target.get("created_at"),
            "updated_at": now,
            "pushed_at": now,
        }
        self._recompute_progress(student_copy, now=now)
        replaced = False
        for idx, item in enumerate(student_packages):
            if isinstance(item, dict) and str(item.get("id")) == str(target.get("id")):
                student_packages[idx] = student_copy
                replaced = True
                break
        if not replaced:
            student_packages.insert(0, student_copy)
        student_state["packages"] = student_packages
        self._set_user_module_state(student_username, student_state)
        self._persist_package_to_db(student_copy)
        self._record_intervention_event(target, "package_pushed")
        return target

    def get_teacher_progress(self, teacher_username: str) -> List[Dict[str, Any]]:
        packages = self.list_teacher_packages(teacher_username)
        rows = []
        for item in packages:
            if str(item.get("stage") or "") != "pushed":
                continue
            rows.append(
                {
                    "package_id": item.get("id"),
                    "student_username": item.get("student_username"),
                    "student_status": item.get("student_status", "pending"),
                    "completion_rate": float(((item.get("progress") or {}).get("completion_rate") or 0)),
                    "answered_questions": int(((item.get("progress") or {}).get("answered_questions") or 0)),
                    "total_questions": int(((item.get("progress") or {}).get("total_questions") or 0)),
                    "student_note": item.get("student_note", ""),
                    "average_final_score": ((item.get("score_summary") or {}).get("average_final_score")),
                    "average_ai_score": ((item.get("score_summary") or {}).get("average_ai_score")),
                    "average_teacher_score": ((item.get("score_summary") or {}).get("average_teacher_score")),
                    "updated_at": ((item.get("progress") or {}).get("updated_at") or item.get("updated_at")),
                    "pushed_at": item.get("pushed_at"),
                }
            )
        return rows

    def grade_teacher_question(
        self,
        *,
        teacher_username: str,
        package_id: str,
        question_id: str,
        teacher_score: float,
        teacher_comment: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(teacher_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            raise ValueError("任务包不存在")
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        self._ensure_package_struct(target)
        grades = target.get("grades")
        grade_row = None
        if isinstance(grades, list):
            for item in grades:
                if isinstance(item, dict) and str(item.get("question_id") or "") == question_id:
                    grade_row = item
                    break
        if grade_row is None:
            raise ValueError("题目不存在")

        now = self._now()
        clamped_score = round(max(0.0, min(100.0, float(teacher_score))), 2)
        grade_row["teacher_score"] = clamped_score
        grade_row["teacher_comment"] = str(teacher_comment or "").strip()
        grade_row["teacher_graded_at"] = now
        grade_row["final_score"] = clamped_score
        grade_row["status"] = "teacher_graded"
        grade_row["updated_at"] = now
        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        self._set_user_module_state(teacher_username, state)
        self._persist_package_to_db(target)
        self._record_intervention_event(
            target,
            "teacher_reviewed",
            payload={
                "question_id": question_id,
                "teacher_score": clamped_score,
                "teacher_comment": str(teacher_comment or "").strip(),
            },
        )

        student_username = str(target.get("student_username") or "").strip()
        if student_username:
            student_state = self._get_user_module_state(student_username)
            student_packages = student_state.get("packages")
            if isinstance(student_packages, list):
                for package in student_packages:
                    if not isinstance(package, dict):
                        continue
                    if str(package.get("id")) != package_id:
                        continue
                    package["grades"] = target.get("grades", [])
                    package["score_summary"] = target.get("score_summary", {})
                    package["updated_at"] = now
                    self._set_user_module_state(student_username, student_state)
                    self._persist_package_to_db(package)
                    break
        return target

    def list_student_packages(self, student_username: str) -> List[Dict[str, Any]]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        rows = self._merge_packages(
            [item for item in packages if isinstance(item, dict)],
            self._load_packages_from_db(student_username=student_username),
        )
        for item in rows:
            self._recompute_progress(item)
        return rows

    def get_student_package(self, student_username: str, package_id: str) -> Dict[str, Any]:
        packages = self.list_student_packages(student_username)
        for item in packages:
            if str(item.get("id")) == package_id:
                return item
        raise ValueError("任务包不存在")

    def _sync_back_to_teacher(self, package: Dict[str, Any]) -> None:
        teacher_username = str(package.get("teacher_username") or "").strip()
        package_id = str(package.get("id") or "").strip()
        if not teacher_username or not package_id:
            return
        teacher_state = self._get_user_module_state(teacher_username)
        teacher_packages = teacher_state.get("packages")
        if not isinstance(teacher_packages, list):
            return
        for item in teacher_packages:
            if not isinstance(item, dict):
                continue
            if str(item.get("id")) != package_id:
                continue
            item["student_status"] = package.get("student_status", item.get("student_status"))
            item["student_note"] = package.get("student_note", item.get("student_note"))
            item["progress"] = package.get("progress", item.get("progress"))
            item["answers"] = package.get("answers", item.get("answers", []))
            item["grades"] = package.get("grades", item.get("grades", []))
            item["score_summary"] = package.get("score_summary", item.get("score_summary", {}))
            item["updated_at"] = self._now()
            self._set_user_module_state(teacher_username, teacher_state)
            self._persist_package_to_db(item)
            return

    def student_decide_package(
        self,
        *,
        student_username: str,
        package_id: str,
        decision: str,
        note: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        now = self._now()
        target["student_status"] = decision
        target["student_note"] = note
        target["updated_at"] = now
        if decision == "declined":
            target["progress"] = {
                "completion_rate": 0,
                "answered_questions": 0,
                "total_questions": len(target.get("questions", []) if isinstance(target.get("questions"), list) else []),
                "status": "declined",
                "updated_at": now,
            }
        elif decision == "accepted":
            self._recompute_progress(target, now=now)
        self._set_user_module_state(student_username, state)
        self._sync_back_to_teacher(target)
        self._persist_package_to_db(target)
        self._record_intervention_event(
            target,
            "package_declined" if decision == "declined" else "package_accepted",
            payload={"student_note": note},
        )
        return target

    def student_save_answer(
        self,
        *,
        student_username: str,
        package_id: str,
        question_id: str,
        answer: str,
        note: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        current_status = str(target.get("student_status") or "pending")
        if current_status == "declined":
            raise ValueError("该任务包已被标记为暂不执行")
        if current_status == "pending":
            raise ValueError("请先接受任务包再作答")

        answers = target.get("answers")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(target.get("questions", []))
        found = False
        now = self._now()
        normalized_question_id = str(question_id).strip()
        if not normalized_question_id:
            raise ValueError("题目 ID 不能为空")

        for item in answers:
            if not isinstance(item, dict):
                continue
            if str(item.get("question_id") or "") != normalized_question_id:
                continue
            clean_answer = str(answer or "").strip()
            item["answer"] = clean_answer
            item["note"] = str(note or "").strip()
            item["status"] = "completed" if clean_answer else "pending"
            item["updated_at"] = now
            found = True
            break
        if not found:
            raise ValueError("题目不存在")

        target["answers"] = answers
        self._auto_grade_single_question(target, normalized_question_id, now=now)
        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        self._set_user_module_state(student_username, state)
        self._sync_back_to_teacher(target)
        self._persist_package_to_db(target)
        self._record_intervention_event(
            target,
            "answer_saved",
            payload={"question_id": normalized_question_id, "has_answer": bool(str(answer or "").strip())},
        )
        return target

    def student_update_structured_task(
        self,
        *,
        student_username: str,
        package_id: str,
        task_type: str,
        task_id: str,
        completed: bool,
        note: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("package not found")

        current_status = str(target.get("student_status") or "pending")
        if current_status == "declined":
            raise ValueError("该任务包已被标记为暂不执行")
        if current_status == "pending":
            raise ValueError("请先接受任务包再更新任务")

        group_map = {
            "resource": "resource_tasks",
            "assignment": "assignment_tasks",
            "quiz": "quiz_tasks",
            "code": "code_tasks",
        }
        group_name = group_map.get(str(task_type or "").strip())
        if not group_name:
            raise ValueError("unsupported task type")
        self._ensure_package_struct(target)
        tasks = target.get(group_name) if isinstance(target.get(group_name), list) else []
        normalized_task_id = str(task_id or "").strip()
        found = False
        now = self._now()
        for item in tasks:
            if not isinstance(item, dict):
                continue
            candidates = [
                str(item.get("id") or "").strip(),
                str(item.get("resource_id") or "").strip(),
                str(item.get("assignment_id") or "").strip(),
                str(item.get("quiz_id") or "").strip(),
                str(item.get("task_id") or "").strip(),
            ]
            if normalized_task_id not in {candidate for candidate in candidates if candidate}:
                continue
            item["status"] = "completed" if completed else "pending"
            item["completed_at"] = now if completed else ""
            item["note"] = str(note or "").strip()
            found = True
            break
        if not found:
            raise ValueError("task item not found")

        self._recompute_progress(target, now=now)
        target["updated_at"] = now
        self._set_user_module_state(student_username, state)
        self._sync_back_to_teacher(target)
        self._persist_package_to_db(target)
        self._record_intervention_event(
            target,
            "structured_task_completed" if completed else "structured_task_reopened",
            payload={"task_type": task_type, "task_id": normalized_task_id, "note": note},
        )
        return target

    def student_update_progress(
        self,
        *,
        student_username: str,
        package_id: str,
        status: str,
        completion_rate: float,
        note: str,
    ) -> Dict[str, Any]:
        state = self._get_user_module_state(student_username)
        packages = state.get("packages")
        if not isinstance(packages, list):
            packages = []
        target = None
        for item in packages:
            if isinstance(item, dict) and str(item.get("id")) == package_id:
                target = item
                break
        if target is None:
            raise ValueError("任务包不存在")

        now = self._now()
        if str(target.get("student_status") or "") == "declined":
            raise ValueError("该任务包已被标记为暂不执行")
        if note.strip():
            target["student_note"] = note.strip()
        answers = target.get("answers")
        if not isinstance(answers, list):
            answers = self._build_student_answer_entries(target.get("questions", []))
            target["answers"] = answers
        self._recompute_progress(target, now=now)
        if status == "completed" and float((target.get("progress") or {}).get("completion_rate") or 0) < 1.0:
            raise ValueError("complete all required tasks before marking package completed")
        target["updated_at"] = now
        self._set_user_module_state(student_username, state)
        self._sync_back_to_teacher(target)
        self._persist_package_to_db(target)
        self._record_intervention_event(
            target,
            "package_completed" if status == "completed" else "progress_updated",
            payload={"requested_status": status, "student_note": note},
        )
        if status == "completed":
            target["path_refresh"] = self._build_intervention_path_refresh(target)
        return target
