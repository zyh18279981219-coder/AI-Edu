from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .definition_utils import (
    QUIZ_DEFINITION_STATE_PREFIX,
    clean_quiz_definition_text as _clean_text,
    normalize_quiz_question,
    published_definition_index_from_state_rows,
)


from copy import deepcopy
QUIZ_DEFINITION_STATUSES = {"draft", "published"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class QuizDefinitionService:
    """Small lifecycle service for teacher-authored quiz definitions.

    The project does not yet have a dedicated quiz definition table. This service
    stores compatible payloads in user_states under a deterministic system key so
    the publish boundary can be implemented without an uncontrolled migration.
    """

    def __init__(self, store: Any):
        self.store = store

    @staticmethod
    def state_key(course_id: str, node_id: str) -> str:
        course = _clean_text(course_id) or "course_big_data"
        node = _clean_text(node_id)
        if not node:
            raise ValueError("node_id is required")
        return f"{QUIZ_DEFINITION_STATE_PREFIX}{course}::{node}"

    def list_definitions(
        self,
        course_id: str,
        node_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        status_filter = _clean_text(status).lower()
        if status_filter and status_filter not in QUIZ_DEFINITION_STATUSES:
            raise ValueError("status must be draft or published")

        if node_id:
            payload = self._load_bucket(course_id, node_id)
            definitions = payload.get("definitions", [])
        else:
            return []

        result: List[Dict[str, Any]] = []
        for definition in definitions:
            if not isinstance(definition, dict):
                continue
            if status_filter and definition.get("status") != status_filter:
                continue
            result.append(deepcopy(definition))
        return result

    def save_definition(
        self,
        payload: Dict[str, Any],
        teacher_username: Optional[str] = None,
    ) -> Dict[str, Any]:
        course_id = _clean_text(payload.get("course_id")) or "course_big_data"
        node_id = _clean_text(payload.get("node_id") or payload.get("subject"))
        title = _clean_text(payload.get("title")) or f"{node_id} 在线测验"
        status = _clean_text(payload.get("status")).lower() or "draft"
        if status not in QUIZ_DEFINITION_STATUSES:
            raise ValueError("status must be draft or published")
        raw_questions = payload.get("questions")
        if not isinstance(raw_questions, list) or not raw_questions:
            raise ValueError("questions must be a non-empty list")
        questions = [
            normalize_quiz_question(item, index)
            for index, item in enumerate(raw_questions)
        ]

        bucket = self._load_bucket(course_id, node_id)
        definitions = [
            item for item in bucket.get("definitions", []) if isinstance(item, dict)
        ]
        definition_id = _clean_text(payload.get("definition_id")) or f"quizdef_{uuid4().hex[:12]}"
        existing = next(
            (item for item in definitions if item.get("definition_id") == definition_id),
            None,
        )
        now = _now_iso()
        version_no = int((existing or {}).get("version_no") or 0) + 1
        record = {
            "definition_id": definition_id,
            "course_id": course_id,
            "node_id": node_id,
            "title": title,
            "status": status,
            "questions": questions,
            "created_by": (existing or {}).get("created_by") or _clean_text(teacher_username) or "system",
            "created_at": (existing or {}).get("created_at") or now,
            "updated_by": _clean_text(teacher_username) or "system",
            "updated_at": now,
            "published_at": (existing or {}).get("published_at"),
            "version_no": version_no,
        }
        if status == "published":
            record["published_at"] = now
            definitions = self._unpublish_others(definitions, definition_id)

        if existing:
            definitions = [
                record if item.get("definition_id") == definition_id else item
                for item in definitions
            ]
        else:
            definitions.append(record)

        bucket["definitions"] = definitions
        self._save_bucket(course_id, node_id, bucket)
        return deepcopy(record)

    def publish_definition(
        self,
        definition_id: str,
        course_id: str,
        node_id: str,
        teacher_username: Optional[str] = None,
    ) -> Dict[str, Any]:
        target_id = _clean_text(definition_id)
        if not target_id:
            raise ValueError("definition_id is required")
        bucket = self._load_bucket(course_id, node_id)
        definitions = [
            item for item in bucket.get("definitions", []) if isinstance(item, dict)
        ]
        now = _now_iso()
        updated: Optional[Dict[str, Any]] = None
        new_definitions: List[Dict[str, Any]] = []
        for item in definitions:
            if item.get("definition_id") == target_id:
                item = deepcopy(item)
                item["status"] = "published"
                item["published_at"] = now
                item["updated_at"] = now
                item["updated_by"] = _clean_text(teacher_username) or "system"
                item["version_no"] = int(item.get("version_no") or 0) + 1
                updated = item
            elif item.get("status") == "published":
                item = deepcopy(item)
                item["status"] = "draft"
                item["updated_at"] = now
            new_definitions.append(item)
        if not updated:
            raise KeyError("quiz definition not found")
        bucket["definitions"] = new_definitions
        self._save_bucket(course_id, node_id, bucket)
        return deepcopy(updated)

    def get_published_definition(self, course_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        definitions = self.list_definitions(course_id=course_id, node_id=node_id, status="published")
        if not definitions:
            return None
        return max(definitions, key=lambda item: str(item.get("published_at") or item.get("updated_at") or ""))

    def _load_bucket(self, course_id: str, node_id: str) -> Dict[str, Any]:
        key = self.state_key(course_id, node_id)
        payload = self.store.get_user_state(key)
        if isinstance(payload, dict):
            definitions = payload.get("definitions")
            if isinstance(definitions, list):
                return deepcopy(payload)
        return {"course_id": _clean_text(course_id) or "course_big_data", "node_id": _clean_text(node_id), "definitions": []}

    def _save_bucket(self, course_id: str, node_id: str, bucket: Dict[str, Any]) -> None:
        key = self.state_key(course_id, node_id)
        self.store.save_user_state(key, bucket)

    @staticmethod
    def _unpublish_others(
        definitions: List[Dict[str, Any]],
        keep_definition_id: str,
    ) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        now = _now_iso()
        for item in definitions:
            if item.get("definition_id") != keep_definition_id and item.get("status") == "published":
                item = deepcopy(item)
                item["status"] = "draft"
                item["updated_at"] = now
            result.append(item)
        return result
