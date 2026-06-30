from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List


QUIZ_DEFINITION_STATE_PREFIX = "quiz_definitions::"


def clean_quiz_definition_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_quiz_question(raw: Dict[str, Any], index: int = 0) -> Dict[str, str]:
    """Normalize a stored quiz question to the shape used by /api/quiz/start."""
    if not isinstance(raw, dict):
        raise ValueError("question item must be an object")
    question = clean_quiz_definition_text(raw.get("question"))
    if not question:
        raise ValueError(f"question[{index}].question is required")
    topic = (
        clean_quiz_definition_text(raw.get("topic"))
        or clean_quiz_definition_text(raw.get("node_id"))
        or f"question-{index + 1}"
    )
    correct = clean_quiz_definition_text(raw.get("correct") or raw.get("answer")).lower()
    if not correct:
        correct = "?"
    return {
        "topic": topic,
        "question": question,
        "correct": correct,
    }


def published_definition_index_from_state_rows(
    rows: List[Dict[str, Any]],
    course_id: str,
) -> Dict[str, Dict[str, Any]]:
    """Build node_id -> latest published quiz definition from user_states rows."""
    target_course = clean_quiz_definition_text(course_id) or "course_big_data"
    prefix = f"{QUIZ_DEFINITION_STATE_PREFIX}{target_course}::"
    published: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = clean_quiz_definition_text(row.get("username") or row.get("state_key") or row.get("key"))
        payload = row.get("payload_json")
        if isinstance(payload, str):
            try:
                import json

                payload = json.loads(payload)
            except Exception:
                payload = None
        if not isinstance(payload, dict):
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else None
        if not key.startswith(prefix) or not isinstance(payload, dict):
            continue
        key_node_id = key[len(prefix):]
        definitions = payload.get("definitions")
        if not isinstance(definitions, list):
            continue
        for definition in definitions:
            if not isinstance(definition, dict) or definition.get("status") != "published":
                continue
            node_id = (
                clean_quiz_definition_text(definition.get("node_id"))
                or clean_quiz_definition_text(payload.get("node_id"))
                or key_node_id
            )
            if not node_id:
                continue
            current = published.get(node_id)
            current_time = str((current or {}).get("published_at") or (current or {}).get("updated_at") or "")
            next_time = str(definition.get("published_at") or definition.get("updated_at") or "")
            if current is None or next_time >= current_time:
                published[node_id] = deepcopy(definition)
    return published
