from __future__ import annotations

from typing import Optional

from sqlalchemy import insert, text

from ..models.user_interaction import UserInteraction
from ..session import SessionLocal1


async def _resolve_student(db, identifier: str) -> tuple[Optional[int], Optional[str]]:
    if not identifier:
        return None, None
    if identifier.isdigit():
        result = await db.execute(
            text("SELECT user_id, username FROM users WHERE user_id = :user_id AND user_type = 'student'"),
            {"user_id": int(identifier)},
        )
    else:
        result = await db.execute(
            text("SELECT user_id, username FROM users WHERE username = :username AND user_type = 'student'"),
            {"username": identifier},
        )
    row = result.first()
    if not row:
        return None, None
    return int(row[0]), str(row[1])


async def _resolve_course(db, course_or_session_id: str) -> tuple[Optional[str], Optional[str]]:
    value = str(course_or_session_id or "").strip()
    if not value:
        value = "course_big_data"
    result = await db.execute(
        text("SELECT course_id FROM courses WHERE course_id = :course_id"),
        {"course_id": value},
    )
    row = result.first()
    if row:
        return str(row[0]), None
    return None, value


async def collect_student_interaction(
    user_id: str,
    course_id: str = "course_big_data",
    stage: str = "",
    question_type: Optional[str] = None,
    question_count: int = 0,
    error: Optional[str] = None,
) -> dict:
    """Collect one 5E student interaction event."""
    user_identifier = str(user_id or "").strip()
    stage_value = str(stage or "").strip() or "unknown"

    async with SessionLocal1() as db:
        async with db.begin():
            student_user_id, student_username = await _resolve_student(db, user_identifier)
            resolved_course_id, session_id = await _resolve_course(db, str(course_id or "").strip())
            stmt = insert(UserInteraction).values(
                user_identifier=user_identifier or "unknown",
                student_user_id=student_user_id,
                student_username=student_username,
                course_id=resolved_course_id,
                session_id=session_id,
                stage=stage_value,
                question_type=question_type,
                question_count=max(0, int(question_count or 0)),
                error=error,
                payload_json={
                    "source": "fiveE",
                    "raw_user_id": user_id,
                    "raw_course_id": course_id,
                },
            )
            result = await db.execute(stmt)
            interaction_id = result.inserted_primary_key[0] if result.inserted_primary_key else None

    return {
        "ok": True,
        "interaction_id": interaction_id,
        "user_identifier": user_identifier,
        "student_user_id": student_user_id,
        "course_id": resolved_course_id,
        "session_id": session_id,
        "stage": stage_value,
    }
