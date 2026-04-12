from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from DatabaseModule.sqlite_store import get_sqlite_store


DEFAULT_TEACHER_USERNAME = "tea001"


def _detect_teacher_username(store) -> str | None:
    teachers = store.list_users("teacher")
    for teacher in teachers:
        username = teacher.get("username")
        if isinstance(username, str) and username:
            return username

    with store.connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT username FROM sessions WHERE user_type = 'teacher' ORDER BY last_accessed DESC"
        ).fetchall()
    for row in rows:
        username = row["username"]
        if isinstance(username, str) and username:
            return username

    return None


def _resolve_teacher_students(store, teacher_username: str) -> List[str]:
    teacher = store.get_user("teacher", teacher_username) or {}
    students = teacher.get("students") or []
    resolved = [item for item in students if isinstance(item, str) and item]

    if not resolved:
        for student in store.list_users("student"):
            username = student.get("username")
            if student.get("teacher") == teacher_username and username:
                resolved.append(username)

    if not resolved:
        with store.connection() as conn:
            rows = conn.execute(
                "SELECT student_username FROM teacher_student_links WHERE teacher_username = ?",
                (teacher_username,),
            ).fetchall()
        resolved.extend([row["student_username"] for row in rows if row["student_username"]])

    return sorted(set(resolved))


def _upsert_teacher(store, teacher_username: str, teacher_students: List[str]) -> None:
    now = datetime.now().isoformat()
    teacher = store.get_user("teacher", teacher_username) or {}
    if not teacher:
        # If teacher has active sessions but no users row, create a minimal teacher profile.
        with store.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE username = ? AND user_type = 'teacher' LIMIT 1",
                (teacher_username,),
            ).fetchone()
        if row is None:
            raise ValueError(f"Teacher '{teacher_username}' not found in current database")
        teacher = {
            "username": teacher_username,
            "name": teacher_username,
            "password": "123456",
            "students": teacher_students,
        }
    teacher_payload = {
        "username": teacher_username,
        "name": teacher.get("name") or "演示教师",
        "password": teacher.get("password") or "123456",
        "students": teacher_students,
    }

    payload_json = json.dumps(teacher_payload, ensure_ascii=False)

    # Keep this idempotent and non-destructive to existing users.
    with store.connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO users
            (user_type, username, password, display_name, teacher, email, payload_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "teacher",
                teacher_username,
                teacher_payload["password"],
                teacher_payload["name"],
                None,
                teacher.get("email") or f"{teacher_username}@example.com",
                payload_json,
                now,
            ),
        )

        for username in teacher_students:
            conn.execute(
                """
                INSERT OR REPLACE INTO teacher_student_links
                (teacher_username, student_username, updated_at)
                VALUES (?, ?, ?)
                """,
                (teacher_username, username, now),
            )


def _seed_student_twins(store, student_usernames: List[str], overwrite_existing: bool = False) -> Dict[str, int]:
    mastery_values = [62, 57, 71, 66, 53, 78, 60, 64, 69]
    written = 0
    skipped = 0
    for idx, username in enumerate(student_usernames):
        if not overwrite_existing and store.get_twin_profile(username):
            skipped += 1
            continue
        mastery = mastery_values[idx % len(mastery_values)]
        store.save_twin_profile(
            username,
            {
                "username": username,
                "last_updated": datetime.now().isoformat(),
                "overall_mastery": mastery,
                "knowledge_nodes": [
                    {
                        "node_id": "big_data_intro",
                        "node_path": ["大数据导论"],
                        "quiz_score": mastery,
                        "progress": min(mastery + 15, 100),
                        "study_duration_minutes": 120 + mastery,
                        "llm_interaction_count": 8,
                        "mastery_score": mastery,
                    }
                ],
            },
        )
        written += 1
    return {"written": written, "skipped": skipped}


def _seed_teacher_sessions(store, teacher_username: str) -> None:
    now = datetime.now()
    for i in range(12):
        end = now - timedelta(hours=i * 8)
        start = end - timedelta(minutes=70 + (i % 3) * 20)
        store.save_session(
            session_id=f"{teacher_username}-seed-session-{i}",
            payload={
                "session_id": f"{teacher_username}-seed-session-{i}",
                "username": teacher_username,
                "user_type": "teacher",
                "created_at": start.isoformat(),
                "last_accessed": end.isoformat(),
                "current_pdf_path": "data/course/big_data.json",
                "current_node": "big_data_intro",
            },
        )


def _build_log(teacher_username: str, timestamp: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "username": teacher_username,
        "module": "teacher_twin_seed",
        "request": {"model": "seed"},
        "metadata": metadata,
    }


def _seed_teacher_logs(store, teacher_username: str, student_usernames: List[str]) -> None:
    now = datetime.now()
    logs: List[Dict[str, Any]] = []

    for i in range(10):
        ts = (now - timedelta(days=i)).isoformat()
        logs.append(
            _build_log(
                teacher_username,
                ts,
                {
                    "feature": "learning_analytics" if i % 2 == 0 else "auto_grading",
                    "action": "publish_announcement" if i % 2 == 0 else "start_discussion",
                    "ai_recommendation": True,
                    "ai_executed": i % 3 != 0,
                },
            )
        )

    assess_types = ["objective", "subjective", "project", "oral"]
    for i, assess_type in enumerate(assess_types):
        ts = (now - timedelta(days=3 + i)).isoformat()
        logs.append(
            _build_log(
                teacher_username,
                ts,
                {
                    "assessment_type": assess_type,
                    "feedback_text": "本次反馈覆盖思路、易错点与下一步改进建议。",
                    "grading_minutes": 12 + i * 2,
                },
            )
        )

    for i, stu in enumerate(student_usernames):
        ts = (now - timedelta(days=2, hours=i)).isoformat()
        logs.append(
            _build_log(
                teacher_username,
                ts,
                {
                    "student_username": stu,
                    "initiated_by_student": i % 2 == 0,
                    "action": "student_question",
                },
            )
        )

    for i in range(8):
        ts = (now - timedelta(days=5, hours=i)).isoformat()
        logs.append(
            _build_log(
                teacher_username,
                ts,
                {
                    "task_mode": "digital",
                    "task_group_mode": "group" if i % 2 == 0 else "individual",
                    "task_type": "inquiry" if i < 4 else "exercise",
                },
            )
        )

    logs.append(
        _build_log(
            teacher_username,
            (now - timedelta(days=1)).isoformat(),
            {"action": "remediation_material", "feature": "difficulty_explanation"},
        )
    )
    logs.append(
        _build_log(
            teacher_username,
            (now - timedelta(days=1, hours=1)).isoformat(),
            {"action": "remediation_announcement", "feature": "auto_reminder"},
        )
    )

    for item in logs:
        store.append_llm_log(item)


def _seed_teacher_plans(store, teacher_username: str) -> None:
    plan_files = [
        "weekly_plan_01.pdf",
        "data_lab_case_01.mp4",
        "discussion_script_01.docx",
        "mindmap_overview_01.png",
        "assessment_design_01.xlsx",
        "project_rubric_01.md",
    ]

    for idx, filename in enumerate(plan_files, start=1):
        store.save_learning_plan(
            username=teacher_username,
            filename=filename,
            payload={
                "title": f"资源{idx}",
                "revision_count": 2 + idx,
                "type": filename.rsplit(".", 1)[-1],
            },
            plan_path=f"data/learning_plans/{filename}",
            category="teacher",
        )


def _seed_external_metrics(store, teacher_username: str, student_count: int) -> None:
    key = f"teacher_ext::{teacher_username}"
    store.save_user_state(
        key,
        {
            "research_posts": 4,
            "shared_courseware": 6,
            "co_preparation_count": 5,
            "subjective_grading_minutes": 15,
            "personalized_push_count": max(student_count, 1),
            "risk_intervention_count": 3,
            "total_tasks": 20,
            "digital_tasks": 15,
            "collaborative_tasks": 9,
            "inquiry_learning_hours": 9,
            "total_teaching_hours": 24,
            "teacher_reply_rate": 0.86,
            "avg_response_minutes": 32,
            "on_time_release_ratio": 0.91,
            "resource_referenced_by_others": 7,
        },
    )


def seed_teacher_twin_dataset(teacher_username: str, overwrite_student_twins: bool = False) -> Dict[str, Any]:
    store = get_sqlite_store()
    students = _resolve_teacher_students(store, teacher_username)
    _upsert_teacher(store, teacher_username, students)
    twin_stats = {"written": 0, "skipped": 0}
    if students:
        twin_stats = _seed_student_twins(store, students, overwrite_existing=overwrite_student_twins)
    _seed_teacher_sessions(store, teacher_username)
    _seed_teacher_logs(store, teacher_username, students)
    _seed_teacher_plans(store, teacher_username)
    _seed_external_metrics(store, teacher_username, len(students))
    return {
        "teacher_username": teacher_username,
        "student_count": len(students),
        "students": students,
        "twin_profiles_written": twin_stats["written"],
        "twin_profiles_skipped": twin_stats["skipped"],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed radar data for existing teacher account only.")
    parser.add_argument("--teacher", default=None, help="Teacher username to seed; default auto-detect")
    parser.add_argument(
        "--overwrite-student-twins",
        action="store_true",
        help="Overwrite existing student twin_profiles (default: preserve existing profiles)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    store = get_sqlite_store()
    teacher_username = args.teacher or _detect_teacher_username(store) or DEFAULT_TEACHER_USERNAME
    result = seed_teacher_twin_dataset(
        teacher_username=teacher_username,
        overwrite_student_twins=args.overwrite_student_twins,
    )
    print(
        "Teacher twin seed data ready:",
        result["teacher_username"],
        "students=",
        result["student_count"],
        "twin_written=",
        result["twin_profiles_written"],
        "twin_skipped=",
        result["twin_profiles_skipped"],
    )


if __name__ == "__main__":
    main()
