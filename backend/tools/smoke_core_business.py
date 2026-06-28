from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
for item in (PROJECT_ROOT, BACKEND_ROOT):
    value = str(item)
    if value not in sys.path:
        sys.path.insert(0, value)

from DatabaseModule.database_factory import DatabaseFactory
from DiagnosisModule.diagnosis_service import StudentDiagnosisService
from DigitalTwinModule.homework_evidence_service import HomeworkEvidenceService
from HomeworkModule.repository import HomeworkRepository
from PathPlannerModule.path_planner_agent import PathPlannerAgent
from TeacherInterventionModule.service import TeacherInterventionService


COURSE_ID = "smoke_course_twin"
TEACHER = "smoke_teacher"
STUDENT = "smoke_student"
LEAF_NODE_ID = "Flume 基础"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fetch_one(cursor: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
    cursor.execute(sql, params)
    return cursor.fetchone()


def _ensure_smoke_users(store: Any) -> tuple[int, int]:
    now = _now()
    with store.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users
                (login_id, user_type, username, password, display_name, created_at, updated_at)
                VALUES (%s, 'teacher', %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    updated_at = VALUES(updated_at)
                """,
                ("tea_smoke", TEACHER, "smoke", "Smoke Teacher", now, now),
            )
            cursor.execute(
                """
                INSERT INTO users
                (login_id, user_type, username, password, display_name, created_at, updated_at)
                VALUES (%s, 'student', %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    updated_at = VALUES(updated_at)
                """,
                ("stu_smoke", STUDENT, "smoke", "Smoke Student", now, now),
            )
            teacher = _fetch_one(cursor, "SELECT user_id FROM users WHERE username=%s AND user_type='teacher'", (TEACHER,))
            student = _fetch_one(cursor, "SELECT user_id FROM users WHERE username=%s AND user_type='student'", (STUDENT,))
            teacher_id = int(teacher["user_id"])
            student_id = int(student["user_id"])
            cursor.execute(
                """
                INSERT INTO teacher_student_links
                (teacher_username, student_username, teacher_user_id, student_user_id, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    teacher_user_id = VALUES(teacher_user_id),
                    student_user_id = VALUES(student_user_id),
                    updated_at = VALUES(updated_at)
                """,
                (TEACHER, STUDENT, teacher_id, student_id, now),
            )
    return teacher_id, student_id


def smoke_course_graph(store: Any) -> dict[str, Any]:
    graph = {
        "name": "Smoke 大数据课程",
        "children": [
            {
                "name": "第1章 数据采集",
                "children": [
                    {
                        "name": "1.1 数据采集概述",
                        "children": [
                            {
                                "name": "Flume 基础",
                                "resource_path": [
                                    "https://www.bilibili.com/video/BV-smoke-flume",
                                    "https://www.youtube.com/watch?v=smoke-flume",
                                    "https://blog.csdn.net/smoke_flume",
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    result = store.sync_course_from_graph(
        COURSE_ID,
        graph,
        course_name="Smoke 大数据课程",
        lifecycle_status="draft",
        updated_by=TEACHER,
    )
    resources = store.list_resources_for_node_name(COURSE_ID, LEAF_NODE_ID)
    if result.get("nodes", 0) < 3:
        raise AssertionError(f"course graph nodes not synced: {result}")
    if len(resources) < 3:
        raise AssertionError(f"course resources not synced: {resources}")
    review_list = store.list_course_resources(COURSE_ID)
    if not review_list:
        raise AssertionError("course resource review list is empty")
    target = review_list[0]
    disabled = store.set_resource_review_status(
        COURSE_ID,
        target["node_id"],
        target["resource_path"],
        is_enabled=False,
        review_status="disabled",
        quality_status="passed",
    )
    if not disabled:
        raise AssertionError("failed to disable smoke resource")
    visible_after_disable = store.list_resources_for_node_name(COURSE_ID, target["node_name"])
    if target["resource_path"] in visible_after_disable:
        raise AssertionError("disabled resource is still visible to learning resource query")
    store.set_resource_review_status(
        COURSE_ID,
        target["node_id"],
        target["resource_path"],
        is_enabled=True,
        review_status="enabled",
        quality_status="passed",
    )
    published = store.publish_course(COURSE_ID, published_by=TEACHER)
    if not published:
        raise AssertionError("failed to publish smoke course")
    summary = store.get_course_summary(COURSE_ID)
    if not summary or summary.get("lifecycle_status") != "published":
        raise AssertionError(f"course not published: {summary}")
    return {
        "sync_result": result,
        "resource_count": len(resources),
        "review_resource_count": len(review_list),
        "published_status": summary["lifecycle_status"],
        "leaf_node_id": LEAF_NODE_ID,
    }


def smoke_ability_mapping(store: Any, teacher_id: int) -> dict[str, Any]:
    position = store.upsert_career_position(
        COURSE_ID,
        "Data Engineer",
        position_type="primary",
        target_rank=1,
        source_keyword="data engineer",
        created_by=teacher_id,
    )
    if not position or position.get("position_type") != "primary":
        raise AssertionError(f"career position not persisted: {position}")
    ability_result = store.upsert_career_abilities(
        position["position_id"],
        [
            {
                "ability_name": "Data ingestion pipeline",
                "ability_category": "engineering",
                "demand_level": 8,
                "support_level": "high",
                "evidence": {"source": "smoke_core_business"},
            }
        ],
    )
    ability_ids = ability_result.get("ability_ids") or []
    if not ability_ids:
        raise AssertionError(f"career ability not persisted: {ability_result}")
    mapping_result = store.upsert_course_ability_mappings(
        COURSE_ID,
        [
            {
                "ability_id": ability_ids[0],
                "node_id": LEAF_NODE_ID,
                "support_level": "high",
                "match_reason": "Smoke verifies ability is bound only to a leaf knowledge point.",
                "evidence": {"source": "smoke_core_business"},
            }
        ],
        updated_by=teacher_id,
    )
    if mapping_result.get("saved") != 1 or mapping_result.get("rejected"):
        raise AssertionError(f"ability mapping not persisted: {mapping_result}")
    mappings = store.list_course_ability_mappings(COURSE_ID)
    target = next((item for item in mappings if item.get("ability_id") == ability_ids[0]), None)
    if not target:
        raise AssertionError(f"ability mapping not listed: {mappings}")
    reviewed = store.review_course_ability_mapping(
        target["mapping_id"],
        review_status="confirmed",
        support_level="high",
        reviewed_by=teacher_id,
    )
    if not reviewed:
        raise AssertionError("ability mapping review failed")
    reviewed_mappings = store.list_course_ability_mappings(COURSE_ID)
    confirmed = next((item for item in reviewed_mappings if item.get("mapping_id") == target["mapping_id"]), None)
    if not confirmed or confirmed.get("review_status") != "confirmed":
        raise AssertionError(f"ability mapping not confirmed: {confirmed}")
    return {
        "position_id": position["position_id"],
        "ability_id": ability_ids[0],
        "mapping_id": target["mapping_id"],
        "review_status": confirmed["review_status"],
        "support_level": confirmed["support_level"],
    }


def smoke_homework() -> dict[str, Any]:
    repo = HomeworkRepository()
    assignment = repo.create_assignment(
        {
            "title": "Smoke 章节代码题",
            "description": "用于验证作业创建与提交链路。",
            "assignment_type": "coding",
            "course_id": COURSE_ID,
            "node_id": "Flume 基础",
            "node_name": "Flume 基础",
            "node_path": ["第1章 数据采集", "1.1 数据采集概述", "Flume 基础"],
            "chapter_context": "第1章 数据采集",
            "questions": [{"type": "coding", "content": "print('hello smoke')"}],
            "covered_knowledge_points": [
                {
                    "course_id": COURSE_ID,
                    "node_id": LEAF_NODE_ID,
                    "coverage_source": "teacher_confirmed",
                    "recommended_by_system": True,
                    "confirmed_by_teacher": True,
                    "confidence": 92,
                    "reason": "Smoke verifies chapter homework can optionally cover a leaf knowledge point.",
                }
            ],
            "created_by": TEACHER,
            "status": "published",
        }
    )
    coverage = repo.list_assignment_coverage(assignment["id"])
    if not coverage or coverage[0].get("node_id") != LEAF_NODE_ID or not coverage[0].get("confirmed_by_teacher"):
        raise AssertionError(f"homework knowledge coverage not persisted: {coverage}")
    submission = repo.create_submission(
        {
            "assignment_id": assignment["id"],
            "student_username": STUDENT,
            "answers": [{"question_index": 0, "answer": "print('hello smoke')"}],
        }
    )
    repo.update_submission(
        submission["id"],
        {
            "status": "graded",
            "ai_score": 92,
            "ai_feedback": "Smoke 自动评分通过。",
            "teacher_score": 95,
            "teacher_comment": "Smoke 教师评分通过。",
            "graded_at": _now(),
            "grader_username": TEACHER,
        },
    )
    latest = repo.get_latest_submission(assignment["id"], STUDENT)
    if not latest or latest.get("status") != "graded":
        raise AssertionError(f"homework submission not graded: {latest}")
    return {
        "assignment_id": assignment["id"],
        "submission_id": submission["id"],
        "status": latest["status"],
        "coverage_count": len(coverage),
    }


def smoke_twin_profile(store: Any, student_id: int) -> dict[str, Any]:
    payload = {
        "username": STUDENT,
        "user_id": student_id,
        "course_id": COURSE_ID,
        "last_updated": _now(),
        "overall_mastery": 58.5,
        "knowledge_nodes": [
            {
                "node_id": "Flume 基础",
                "node_path": ["第1章 数据采集", "1.1 数据采集概述", "Flume 基础"],
                "course_id": COURSE_ID,
                "quiz_score": 55,
                "progress": 70,
                "study_duration_minutes": 35,
                "llm_interaction_count": 2,
                "mastery_score": 58,
            }
        ],
    }
    store.save_twin_profile(STUDENT, payload)
    loaded = store.get_twin_profile(STUDENT)
    if not loaded or not loaded.get("knowledge_nodes"):
        raise AssertionError(f"twin profile not loaded: {loaded}")
    homework_evidence = HomeworkEvidenceService().build_student_evidence(STUDENT, COURSE_ID)
    practice_summary = homework_evidence.get("practice_summary") or {}
    coverage_nodes = homework_evidence.get("knowledge_point_homework_evidence") or []
    if practice_summary.get("chapter_count", 0) < 1 or practice_summary.get("average_practice_score") is None:
        raise AssertionError(f"chapter practice evidence not aggregated: {homework_evidence}")
    if not any(item.get("node_id") == LEAF_NODE_ID for item in coverage_nodes):
        raise AssertionError(f"homework coverage evidence not aggregated for leaf node: {homework_evidence}")
    return {
        "username": loaded["username"],
        "node_count": len(loaded["knowledge_nodes"]),
        "chapter_practice_score": practice_summary.get("average_practice_score"),
        "coverage_node_count": practice_summary.get("coverage_node_count"),
    }


def smoke_quiz_attempt(store: Any, student_id: int) -> dict[str, Any]:
    attempt_id = store.record_quiz_attempt(
        username=STUDENT,
        user_id=student_id,
        course_id=COURSE_ID,
        node_id="Flume 基础",
        score=8,
        total=10,
        passed=True,
        extra_payload={"source": "smoke_core_business"},
    )
    with store.connection() as conn:
        with conn.cursor() as cursor:
            row = _fetch_one(cursor, "SELECT score,total,passed FROM quiz_attempts WHERE attempt_id=%s", (attempt_id,))
    if not row or int(row["passed"]) != 1:
        raise AssertionError(f"quiz attempt not persisted: {attempt_id}, {row}")
    return {"attempt_id": attempt_id, "score": float(row["score"]), "total": float(row["total"])}


def smoke_resource_learning_events(store: Any, student_id: int) -> dict[str, Any]:
    with store.connection() as conn:
        with conn.cursor() as cursor:
            row = _fetch_one(
                cursor,
                """
                SELECT resource_id, resource_path
                FROM resources
                WHERE course_id=%s AND node_id=%s
                  AND COALESCE(is_enabled, 1)=1
                  AND COALESCE(is_deleted, 0)=0
                ORDER BY resource_id
                LIMIT 1
                """,
                (COURSE_ID, LEAF_NODE_ID),
            )
    if not row:
        raise AssertionError("no smoke resource available for learning event")
    event_ids = [
        store.record_resource_learning_event(
            username=STUDENT,
            user_id=student_id,
            course_id=COURSE_ID,
            node_id=LEAF_NODE_ID,
            resource_id=int(row["resource_id"]),
            resource_path=str(row.get("resource_path") or ""),
            event_type="click",
            duration_seconds=15,
            progress_percent=10,
            payload={"source": "smoke_core_business"},
        ),
        store.record_resource_learning_event(
            username=STUDENT,
            user_id=student_id,
            course_id=COURSE_ID,
            node_id=LEAF_NODE_ID,
            resource_id=int(row["resource_id"]),
            resource_path=str(row.get("resource_path") or ""),
            event_type="complete",
            duration_seconds=420,
            progress_percent=100,
            payload={"source": "smoke_core_business"},
        ),
    ]
    summary = store.summarize_resource_learning_events(course_id=COURSE_ID, node_id=LEAF_NODE_ID)
    if summary.get("event_count", 0) < 2:
        raise AssertionError(f"resource learning events not summarized: {summary}")
    node_summary = (summary.get("node_summaries") or [{}])[0]
    if int(node_summary.get("completed_count") or 0) <= 0:
        raise AssertionError(f"resource completion not summarized: {summary}")
    return {
        "event_ids": event_ids,
        "event_count": summary.get("event_count"),
        "completed_count": node_summary.get("completed_count"),
    }


def smoke_diagnosis_and_path(store: Any) -> dict[str, Any]:
    diagnosis = StudentDiagnosisService().generate_student_diagnosis(
        STUDENT,
        course_id=COURSE_ID,
        persist=True,
    )
    weak_nodes = diagnosis.get("weak_nodes") or []
    if not weak_nodes:
        raise AssertionError(f"diagnosis should contain weak nodes: {diagnosis}")
    if "confidence" not in diagnosis or diagnosis.get("evidence_level") not in {"sufficient", "partial", "insufficient"}:
        raise AssertionError(f"diagnosis missing confidence/evidence level: {diagnosis}")
    evidence_timeline = ((diagnosis.get("teacher_view") or {}).get("evidence_timeline") or [])
    resource_evidence = [item for item in evidence_timeline if item.get("type") == "resource_learning"]
    if not resource_evidence:
        raise AssertionError(f"diagnosis missing resource learning evidence timeline: {evidence_timeline}")
    target_node = next((item for item in diagnosis_items(diagnosis) if item.get("node_id") == LEAF_NODE_ID), None)
    if not target_node:
        raise AssertionError(f"diagnosis missing leaf node item: {diagnosis}")
    homework = target_node.get("homework") or {}
    if int(homework.get("graded_count") or 0) < 1:
        raise AssertionError(f"diagnosis did not use homework coverage evidence: {target_node}")
    with store.connection() as conn:
        with conn.cursor() as cursor:
            row = _fetch_one(
                cursor,
                "SELECT report_id FROM diagnosis_reports WHERE report_id=%s",
                (diagnosis["report_id"],),
            )
    if not row:
        raise AssertionError("diagnosis report was not persisted")
    correction_id = store.record_diagnosis_correction(
        report_id=diagnosis["report_id"],
        username=STUDENT,
        course_id=COURSE_ID,
        teacher_username=TEACHER,
        node_id=LEAF_NODE_ID,
        original_reason_type="mastery_low",
        corrected_reason_type="practice_evidence_needed",
        original_evidence_level=diagnosis.get("evidence_level"),
        corrected_evidence_level="partial",
        correction_note="Smoke verifies teacher diagnosis correction persistence.",
        payload={"source": "smoke_core_business"},
    )
    corrections = store.list_diagnosis_corrections(report_id=diagnosis["report_id"])
    if not any(int(item.get("correction_id") or 0) == int(correction_id) for item in corrections):
        raise AssertionError(f"diagnosis correction not persisted: {corrections}")

    os.environ["PATH_PLANNER_LLM_ENABLED"] = "0"
    path = PathPlannerAgent().plan(STUDENT)
    if not path.get("formal_path_nodes"):
        raise AssertionError(f"path should contain formal path nodes: {path}")
    path_diagnosis = path.get("diagnosis") or {}
    if not path_diagnosis.get("report_id"):
        raise AssertionError(f"path should include diagnosis summary: {path}")
    statuses = store.list_learning_path_node_status(STUDENT)
    current_statuses = [
        item for item in statuses
        if item.get("node_id") == LEAF_NODE_ID and item.get("course_id") == COURSE_ID
    ]
    if not current_statuses:
        raise AssertionError(f"path node status not persisted: {statuses}")
    active_status = current_statuses[0]
    updated_status = store.update_learning_path_node_status(
        STUDENT,
        LEAF_NODE_ID,
        plan_id=active_status.get("plan_id"),
        status="in_progress",
        payload={"source": "smoke_core_business"},
    )
    if not updated_status or updated_status.get("status") != "in_progress" or not updated_status.get("started_at"):
        raise AssertionError(f"path node status not moved to in_progress: {updated_status}")
    completed_status = store.update_learning_path_node_status(
        STUDENT,
        LEAF_NODE_ID,
        plan_id=active_status.get("plan_id"),
        status="completed",
        mastery_after=72.0,
        payload={"source": "smoke_core_business"},
    )
    if (
        not completed_status
        or completed_status.get("status") != "completed"
        or not completed_status.get("completed_at")
        or float(completed_status.get("mastery_after") or 0) < 72.0
    ):
        raise AssertionError(f"path node status not completed: {completed_status}")
    return {
        "diagnosis_report_id": diagnosis["report_id"],
        "evidence_level": diagnosis.get("evidence_level"),
        "confidence": diagnosis.get("confidence"),
        "weak_node_count": len(weak_nodes),
        "resource_evidence_count": len(resource_evidence),
        "homework_coverage_graded_count": int(homework.get("graded_count") or 0),
        "path_node_count": len(path.get("formal_path_nodes") or []),
        "path_status_count": len(current_statuses),
        "path_status": completed_status.get("status"),
        "correction_id": correction_id,
    }


def diagnosis_items(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    return ((diagnosis.get("teacher_view") or {}).get("all_nodes") or [])


def smoke_teacher_intervention_package(store: Any) -> dict[str, Any]:
    service = TeacherInterventionService()
    teacher_session = {
        "username": TEACHER,
        "user_type": "teacher",
        "user_id": None,
        "login_id": "tea_smoke",
    }
    package = service.generate_intervention_draft(
        teacher_session=teacher_session,
        student_username=STUDENT,
        question_count=2,
        difficulty="medium",
    )
    package_id = str(package.get("id") or "")
    if not package_id:
        raise AssertionError(f"intervention package missing id: {package}")
    intervention_timeline = ((package.get("diagnosis") or {}).get("evidence_timeline") or [])
    if not any(item.get("type") == "resource_learning" for item in intervention_timeline):
        raise AssertionError(f"intervention diagnosis missing resource evidence timeline: {intervention_timeline}")
    pushed = service.push_package_to_student(teacher_username=TEACHER, package_id=package_id)
    student_package = service.student_decide_package(
        student_username=STUDENT,
        package_id=package_id,
        decision="accepted",
        note="Smoke accepts intervention package.",
    )
    question_id = str(((student_package.get("questions") or [{}])[0] or {}).get("id") or "")
    if question_id:
        student_package = service.student_save_answer(
            student_username=STUDENT,
            package_id=package_id,
            question_id=question_id,
            answer="Smoke answer for intervention package.",
            note="Smoke answer.",
        )
    service.student_update_progress(
        student_username=STUDENT,
        package_id=package_id,
        status="completed",
        completion_rate=1.0,
        note="Smoke completed intervention package.",
    )
    with store.connection() as conn:
        with conn.cursor() as cursor:
            row = _fetch_one(
                cursor,
                "SELECT status, payload_json FROM intervention_packages WHERE package_id=%s",
                (package_id,),
            )
            item_count_row = _fetch_one(
                cursor,
                "SELECT COUNT(*) AS item_count FROM intervention_package_items WHERE package_id=%s",
                (package_id,),
            )
            record_row = _fetch_one(
                cursor,
                """
                SELECT status, score
                FROM intervention_package_student_records
                WHERE package_id=%s AND student_username=%s
                ORDER BY record_id DESC
                LIMIT 1
                """,
                (package_id, STUDENT),
            )
    if not row:
        raise AssertionError("intervention package was not persisted")
    if int((item_count_row or {}).get("item_count") or 0) <= 0:
        raise AssertionError("intervention package items were not persisted")
    if not record_row:
        raise AssertionError("intervention package student record was not persisted")
    return {
        "package_id": package_id,
        "db_status": row.get("status"),
        "item_count": int(item_count_row.get("item_count") or 0),
        "resource_evidence_count": len([item for item in intervention_timeline if item.get("type") == "resource_learning"]),
        "student_record_status": record_row.get("status"),
    }


def smoke_course_runtime_evaluation(store: Any) -> dict[str, Any]:
    evaluation = store.evaluate_course_runtime(COURSE_ID, window_days=30, min_quiz_attempts=1)
    if not evaluation:
        raise AssertionError("course runtime evaluation returned empty result")
    metrics = evaluation.get("metrics") or {}
    if metrics.get("total_leaf_nodes", 0) < 1:
        raise AssertionError(f"runtime evaluation missing leaf nodes: {metrics}")
    if metrics.get("resource_coverage_rate", 0) <= 0:
        raise AssertionError(f"runtime evaluation missing resource coverage: {metrics}")
    if metrics.get("assessment_coverage_rate", 0) <= 0:
        raise AssertionError(f"runtime evaluation missing assessment evidence: {metrics}")
    if metrics.get("total_abilities", 0) <= 0 or "ability_support_rate" not in metrics:
        raise AssertionError(f"runtime evaluation missing ability support metrics: {metrics}")
    if "course_health_score" not in metrics:
        raise AssertionError(f"runtime evaluation missing health score: {metrics}")
    if metrics.get("resource_click_rate", 0) <= 0 or metrics.get("resource_completion_rate", 0) <= 0:
        raise AssertionError(f"runtime evaluation did not use resource learning events: {metrics}")
    required_sections = {
        "structure_quality",
        "resource_coverage_and_effectiveness",
        "assessment_evidence_and_learning_effect",
        "runtime_weak_points",
        "career_ability_support",
    }
    sections = set((evaluation.get("sections") or {}).keys())
    missing_sections = required_sections - sections
    if missing_sections:
        raise AssertionError(f"runtime evaluation missing requirement sections: {missing_sections}")
    formulas = evaluation.get("formulas") or {}
    for key in ("k_risk", "a_sup", "course_health_score"):
        if key not in formulas:
            raise AssertionError(f"runtime evaluation missing formula {key}: {formulas}")
    if not evaluation.get("unavailable_metrics"):
        raise AssertionError("runtime evaluation should explain unavailable requirement metrics")
    return {
        "formula_version": evaluation.get("formula_version"),
        "course_health_score": metrics.get("course_health_score"),
        "resource_coverage_rate": metrics.get("resource_coverage_rate"),
        "resource_click_rate": metrics.get("resource_click_rate"),
        "resource_completion_rate": metrics.get("resource_completion_rate"),
        "assessment_coverage_rate": metrics.get("assessment_coverage_rate"),
        "ability_support_rate": metrics.get("ability_support_rate"),
        "section_count": len(sections),
        "unavailable_metric_count": len(evaluation.get("unavailable_metrics") or []),
        "action_item_count": len(evaluation.get("action_items") or []),
    }


def main() -> None:
    os.environ["RESOURCE_RECOMMENDER_ONLINE"] = "0"
    os.environ["PATH_PLANNER_LLM_ENABLED"] = "0"
    DatabaseFactory.reset_instance()
    store = DatabaseFactory.get_store()
    teacher_id, student_id = _ensure_smoke_users(store)
    result = {
        "users": {"teacher_id": teacher_id, "student_id": student_id},
        "course_graph": smoke_course_graph(store),
        "ability_mapping": smoke_ability_mapping(store, teacher_id),
        "homework": smoke_homework(),
        "twin_profile": smoke_twin_profile(store, student_id),
        "quiz_attempt": smoke_quiz_attempt(store, student_id),
        "resource_learning_events": smoke_resource_learning_events(store, student_id),
        "diagnosis_and_path": smoke_diagnosis_and_path(store),
        "teacher_intervention_package": smoke_teacher_intervention_package(store),
        "course_runtime_evaluation": smoke_course_runtime_evaluation(store),
    }
    print(json.dumps({"status": "ok", "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
