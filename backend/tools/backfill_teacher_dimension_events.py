from __future__ import annotations

import json
from pathlib import Path

from DatabaseModule.store import get_database_store
from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
from HomeworkModule.repository import HomeworkRepository


def main() -> None:
    store = get_database_store()
    repo = get_teacher_event_repository()
    homework_repo = HomeworkRepository()

    teacher_rows = store.list_users("teacher")
    teacher_usernames = {str(item.get("username") or "").strip() for item in teacher_rows if str(item.get("username") or "").strip()}

    assignments = homework_repo.list_assignments()
    submissions_by_assignment = {}
    for assignment in assignments:
        aid = str(assignment.get("id") or "")
        if not aid:
            continue
        submissions_by_assignment[aid] = homework_repo.list_submissions(assignment_id=aid)

    for assignment in assignments:
        teacher_username = str(assignment.get("created_by") or "").strip()
        if teacher_username not in teacher_usernames:
            continue
        created_at = assignment.get("created_at")
        repo.record_interaction_event(
            teacher_username=teacher_username,
            event_type="assignment_created",
            course_id=str(assignment.get("course_id") or ""),
            class_name=str(assignment.get("class_name") or ""),
            target_id=str(assignment.get("id") or ""),
            payload={
                "title": assignment.get("title"),
                "assignment_type": assignment.get("assignment_type"),
                "node_name": assignment.get("node_name"),
                "task_mode": "backfill",
                "task_type": "backfill",
                "source": "backfill",
                "published_on_time": True,
            },
            created_at=created_at,
        )
        if assignment.get("status") == "published":
            repo.record_interaction_event(
                teacher_username=teacher_username,
                event_type="assignment_published",
                course_id=str(assignment.get("course_id") or ""),
                class_name=str(assignment.get("class_name") or ""),
                target_id=str(assignment.get("id") or ""),
                payload={"title": assignment.get("title"), "source": "backfill", "published_on_time": True},
                created_at=created_at,
            )

        for submission in submissions_by_assignment.get(str(assignment.get("id") or ""), []):
            graded_at = submission.get("graded_at") or submission.get("submitted_at")
            repo.record_grading_event(
                assignment_id=str(assignment.get("id") or ""),
                submission_id=str(submission.get("id") or ""),
                teacher_username=teacher_username,
                student_username=str(submission.get("student_username") or ""),
                event_type="teacher_final_grade" if submission.get("teacher_score") is not None else "ai_recommendation_generated",
                grading_minutes=0.0,
                is_ai_recommended=submission.get("ai_score") is not None,
                is_ai_executed=submission.get("teacher_score") is not None,
                payload={
                    "assignment_type": assignment.get("assignment_type"),
                    "feedback_text": submission.get("teacher_comment") or submission.get("ai_feedback"),
                    "source": "backfill",
                },
                created_at=graded_at,
            )

    for teacher_username in teacher_usernames:
        try:
            identity = store.get_user_by_identifier("teacher", teacher_username)
            if not identity:
                continue
            teacher_identifier = str(identity.get("user_id") or teacher_username)
            logs = store.list_llm_logs_for_user(teacher_identifier, user_type="teacher", limit=4000)
        except Exception:
            continue
        for log in logs:
            metadata = log.get("metadata") or {}
            action = str(metadata.get("action") or "").strip()
            timestamp = log.get("timestamp")
            if action in {"announcement", "publish_announcement"}:
                repo.record_interaction_event(
                    teacher_username=teacher_username,
                    event_type="announcement_published",
                    payload={"source": "backfill", "raw_metadata": metadata},
                    created_at=timestamp,
                )
            elif action in {"discussion_topic", "start_discussion"}:
                repo.record_interaction_event(
                    teacher_username=teacher_username,
                    event_type="discussion_topic",
                    payload={"source": "backfill", "raw_metadata": metadata},
                    created_at=timestamp,
                )
            elif action in {"remediation_material", "remediation_announcement"}:
                repo.record_grading_event(
                    assignment_id=f"backfill::{teacher_username}",
                    teacher_username=teacher_username,
                    event_type=action,
                    grading_minutes=None,
                    is_ai_recommended=False,
                    is_ai_executed=True,
                    payload={"source": "backfill", "raw_metadata": metadata},
                    created_at=timestamp,
                )
            if metadata.get("feature") == "ai_assistant":
                repo.record_research_event(
                    teacher_username=teacher_username,
                    event_type="research_post",
                    payload={"source": "backfill", "raw_metadata": metadata},
                    created_at=timestamp,
                )

    print(json.dumps({"status": "ok", "teacher_count": len(teacher_usernames)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
