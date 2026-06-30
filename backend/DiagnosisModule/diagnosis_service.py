from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

from DatabaseModule.database_factory import DatabaseFactory


class StudentDiagnosisService:
    """Rule-based diagnosis service shared by student twin, path and teacher view."""

    MASTERY_WEAK_THRESHOLD = 60.0
    QUIZ_WEAK_THRESHOLD = 60.0
    HOMEWORK_WEAK_THRESHOLD = 60.0
    RECENT_DAYS = 30

    def __init__(self) -> None:
        self.store = DatabaseFactory.get_store()

    def generate_student_diagnosis(
        self,
        username: str,
        *,
        course_id: str | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        username = str(username or "").strip()
        if not username:
            raise ValueError("username is required")

        profile = self.store.get_twin_profile(username)
        if not profile:
            raise FileNotFoundError(f"TwinProfile for user '{username}' not found")

        self._require_published_course(course_id)
        node_rows = self._load_profile_nodes(username, course_id)
        if not node_rows:
            node_rows = self._profile_nodes_without_course(profile, course_id)

        resolved_course_id = course_id or self._dominant_course_id(node_rows) or "course_big_data"
        self._require_published_course(resolved_course_id)
        node_ids = [str(item.get("node_id") or "").strip() for item in node_rows if item.get("node_id")]
        quiz_stats = self._load_quiz_stats(username, resolved_course_id, node_ids)
        homework_stats = self._load_homework_stats(username, resolved_course_id, node_ids)
        timeline = self._load_evidence_timeline(username, resolved_course_id, limit=40)

        diagnosis_items: list[dict[str, Any]] = []
        weak_items: list[dict[str, Any]] = []
        for row in node_rows:
            item = self._diagnose_node(row, quiz_stats.get(row["node_id"], {}), homework_stats.get(row["node_id"], {}))
            diagnosis_items.append(item)
            if item["is_weak"] or item["evidence_level"] == "insufficient":
                weak_items.append(item)

        weak_items.sort(key=lambda item: (item["evidence_level"] == "insufficient", item["mastery_score"]))
        confidence = self._overall_confidence(diagnosis_items)
        evidence_level = self._overall_evidence_level(diagnosis_items)
        summary = self._build_summary(profile, weak_items, evidence_level, confidence)
        result = {
            "report_id": f"diag_{uuid4().hex}",
            "username": username,
            "user_id": profile.get("user_id"),
            "course_id": resolved_course_id,
            "report_date": date.today().isoformat(),
            "diagnosis_type": "student_learning",
            "evidence_level": evidence_level,
            "confidence": confidence,
            "persona_summary": summary,
            "student_view": self._build_student_view(weak_items, evidence_level),
            "teacher_view": {
                "weak_nodes": weak_items,
                "all_nodes": diagnosis_items,
                "evidence_timeline": timeline,
                "manual_correction_supported": True,
            },
            "weak_nodes": weak_items,
            "formulas": {
                "node_mastery_weak": "mastery_score < 60",
                "quiz_score_percent": "avg(score / total * 100) for published quiz-definition attempts; generated fallback quizzes are supplemental evidence",
                "homework_score_percent": "avg(coalesce(teacher_score, ai_score) / assignment.total_score * 100); includes assignment node and teacher-confirmed covered knowledge points",
                "confidence": "min(100, published_quiz_evidence*35 + homework_evidence*25 + profile_progress*15 + study_duration*10 + recent_evidence*15); generated quiz fallback and resource_learning_events are evidence timeline items",
            },
            "thresholds": {
                "weak_mastery": self.MASTERY_WEAK_THRESHOLD,
                "weak_quiz": self.QUIZ_WEAK_THRESHOLD,
                "weak_homework": self.HOMEWORK_WEAK_THRESHOLD,
                "recent_evidence_days": self.RECENT_DAYS,
            },
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        result["student_view"]["evidence_timeline"] = self._student_evidence_timeline(timeline)
        if persist:
            self._persist_report(result)
        return result

    def _require_published_course(self, course_id: str | None) -> None:
        normalized = str(course_id or "").strip()
        if not normalized:
            return
        try:
            summary = self.store.get_course_summary(normalized)
        except Exception:
            return
        if summary and str(summary.get("lifecycle_status") or "") != "published":
            raise PermissionError(f"Course '{normalized}' is not published")

    def _load_profile_nodes(self, username: str, course_id: str | None) -> list[dict[str, Any]]:
        params: list[Any] = [username]
        course_clause = ""
        if course_id:
            course_clause = " AND course_id = %s"
            params.append(course_id)
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT username, user_id, course_id, node_id, node_path_json, quiz_score,
                           progress, study_duration_minutes, llm_interaction_count, mastery_score, updated_at
                    FROM twin_profile_nodes
                    WHERE username = %s{course_clause}
                    ORDER BY course_id, node_id
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()

        result = []
        for row in rows:
            item = dict(row)
            item["node_path"] = self._loads_json(item.pop("node_path_json", None), [])
            for key in ("quiz_score", "progress", "study_duration_minutes", "mastery_score"):
                item[key] = float(item.get(key) or 0)
            item["llm_interaction_count"] = int(item.get("llm_interaction_count") or 0)
            item["updated_at"] = self._to_iso(item.get("updated_at"))
            result.append(item)
        return result

    def _profile_nodes_without_course(self, profile: dict[str, Any], course_id: str | None) -> list[dict[str, Any]]:
        result = []
        for item in profile.get("knowledge_nodes") or []:
            if not isinstance(item, dict) or not item.get("node_id"):
                continue
            result.append(
                {
                    "username": profile.get("username"),
                    "user_id": profile.get("user_id"),
                    "course_id": course_id or "course_big_data",
                    "node_id": str(item.get("node_id")),
                    "node_path": item.get("node_path") if isinstance(item.get("node_path"), list) else [],
                    "quiz_score": float(item.get("quiz_score") or 0),
                    "progress": float(item.get("progress") or 0),
                    "study_duration_minutes": float(item.get("study_duration_minutes") or 0),
                    "llm_interaction_count": int(item.get("llm_interaction_count") or 0),
                    "mastery_score": float(item.get("mastery_score") or 0),
                    "updated_at": profile.get("last_updated"),
                }
            )
        return result

    def _dominant_course_id(self, node_rows: list[dict[str, Any]]) -> str | None:
        counts: dict[str, int] = defaultdict(int)
        for item in node_rows:
            if item.get("course_id"):
                counts[str(item["course_id"])] += 1
        if not counts:
            return None
        return max(counts.items(), key=lambda pair: pair[1])[0]

    def _load_quiz_stats(self, username: str, course_id: str, node_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not node_ids:
            return {}
        placeholders = ",".join(["%s"] * len(node_ids))
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT node_id,
                           SUM(CASE
                               WHEN JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.evidence_policy')) = 'published_quiz_definition'
                                    OR JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.definition_status')) = 'published'
                               THEN 1 ELSE 0
                           END) AS attempt_count,
                           AVG(CASE
                               WHEN JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.evidence_policy')) = 'published_quiz_definition'
                                    OR JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.definition_status')) = 'published'
                               THEN CASE WHEN total > 0 THEN score / total * 100 ELSE score END
                               ELSE NULL
                           END) AS avg_score,
                           SUM(CASE
                               WHEN JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.evidence_policy')) = 'published_quiz_definition'
                                    OR JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.definition_status')) = 'published'
                               THEN 0 ELSE 1
                           END) AS supplemental_attempt_count,
                           COUNT(*) AS total_attempt_count,
                           MAX(CASE
                               WHEN JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.evidence_policy')) = 'published_quiz_definition'
                                    OR JSON_UNQUOTE(JSON_EXTRACT(payload_json, '$.extra.definition_status')) = 'published'
                               THEN created_at ELSE NULL
                           END) AS last_attempt_at,
                           MAX(created_at) AS last_any_attempt_at
                    FROM quiz_attempts
                    WHERE username = %s AND course_id = %s AND node_id IN ({placeholders})
                    GROUP BY node_id
                    """,
                    tuple([username, course_id, *node_ids]),
                )
                rows = cursor.fetchall()
        return {
            str(row["node_id"]): {
                "attempt_count": int(row.get("attempt_count") or 0),
                "avg_score": float(row.get("avg_score") or 0),
                "supplemental_attempt_count": int(row.get("supplemental_attempt_count") or 0),
                "total_attempt_count": int(row.get("total_attempt_count") or 0),
                "last_attempt_at": self._to_iso(row.get("last_attempt_at")),
                "last_any_attempt_at": self._to_iso(row.get("last_any_attempt_at")),
            }
            for row in rows
        }

    def _load_homework_stats(self, username: str, course_id: str, node_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not node_ids:
            return {}
        placeholders = ",".join(["%s"] * len(node_ids))
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT evidence_node_id AS node_id,
                           COUNT(DISTINCT assignment_id) AS assignment_count,
                           COUNT(DISTINCT submission_id) AS submission_count,
                           COUNT(DISTINCT CASE WHEN status = 'graded' THEN submission_id ELSE NULL END) AS graded_count,
                           AVG(CASE
                               WHEN submission_id IS NOT NULL AND total_score > 0
                               THEN score / total_score * 100
                               ELSE NULL
                           END) AS avg_score,
                           MAX(evidence_at) AS last_evidence_at
                    FROM (
                        SELECT a.id AS assignment_id,
                               a.node_id AS evidence_node_id,
                               a.total_score,
                               s.id AS submission_id,
                               s.status,
                               COALESCE(s.teacher_score, s.ai_score, 0) AS score,
                               COALESCE(s.graded_at, s.submitted_at, a.updated_at, a.created_at) AS evidence_at
                        FROM homework_assignments a
                        LEFT JOIN homework_submissions s
                            ON s.assignment_id = a.id AND s.student_username = %s
                        WHERE a.course_id = %s
                          AND a.node_id IN ({placeholders})
                          AND COALESCE(a.status, '') = 'published'
                        UNION
                        SELECT a.id AS assignment_id,
                               kp.node_id AS evidence_node_id,
                               a.total_score,
                               s.id AS submission_id,
                               s.status,
                               COALESCE(s.teacher_score, s.ai_score, 0) AS score,
                               COALESCE(s.graded_at, s.submitted_at, a.updated_at, a.created_at) AS evidence_at
                        FROM homework_assignments a
                        JOIN homework_assignment_knowledge_points kp
                            ON kp.assignment_id = a.id AND COALESCE(kp.confirmed_by_teacher, 0) = 1
                        LEFT JOIN homework_submissions s
                            ON s.assignment_id = a.id AND s.student_username = %s
                        WHERE a.course_id = %s
                          AND kp.node_id IN ({placeholders})
                          AND COALESCE(a.status, '') = 'published'
                    ) evidence
                    GROUP BY evidence_node_id
                    """,
                    tuple([username, course_id, *node_ids, username, course_id, *node_ids]),
                )
                rows = cursor.fetchall()
        return {
            str(row["node_id"]): {
                "assignment_count": int(row.get("assignment_count") or 0),
                "submission_count": int(row.get("submission_count") or 0),
                "graded_count": int(row.get("graded_count") or 0),
                "avg_score": float(row.get("avg_score") or 0),
                "last_evidence_at": self._to_iso(row.get("last_evidence_at")),
            }
            for row in rows
        }

    def _load_evidence_timeline(self, username: str, course_id: str, *, limit: int) -> list[dict[str, Any]]:
        quiz_items: list[dict[str, Any]] = []
        homework_items: list[dict[str, Any]] = []
        resource_items: list[dict[str, Any]] = []
        fivee_items: list[dict[str, Any]] = []
        intervention_items: list[dict[str, Any]] = []
        path_completion_items: list[dict[str, Any]] = []
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT node_id, score, total, passed, payload_json, created_at
                    FROM quiz_attempts
                    WHERE username = %s AND course_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (username, course_id, limit),
                )
                for row in cursor.fetchall():
                    payload = self._loads_json(row.get("payload_json"), {})
                    extra = self._quiz_payload_extra(payload)
                    evidence_policy = str(extra.get("evidence_policy") or "").strip()
                    definition_status = str(extra.get("definition_status") or "").strip()
                    definition_source = str(extra.get("definition_source") or "").strip()
                    quiz_items.append(
                        {
                            "type": "quiz",
                            "node_id": row.get("node_id"),
                            "score": float(row.get("score") or 0),
                            "total": float(row.get("total") or 0),
                            "passed": bool(row.get("passed")),
                            "definition_id": extra.get("definition_id"),
                            "definition_status": definition_status or None,
                            "definition_source": definition_source or None,
                            "evidence_policy": evidence_policy or "generated_quiz_is_supplemental_evidence",
                            "evidence_status": "formal_evidence"
                            if self._is_published_quiz_evidence(extra)
                            else "supplemental_evidence",
                            "occurred_at": self._to_iso(row.get("created_at")),
                        }
                    )
                cursor.execute(
                    """
                    SELECT a.node_id, a.title, a.assignment_type,
                           COALESCE(s.teacher_score, s.ai_score) AS score,
                           a.total_score, s.status, COALESCE(s.graded_at, s.submitted_at) AS occurred_at
                    FROM homework_submissions s
                    JOIN homework_assignments a ON a.id = s.assignment_id
                    WHERE s.student_username = %s AND a.course_id = %s
                    ORDER BY COALESCE(s.graded_at, s.submitted_at) DESC
                    LIMIT %s
                    """,
                    (username, course_id, limit),
                )
                for row in cursor.fetchall():
                    homework_items.append(
                        {
                            "type": "homework",
                            "node_id": row.get("node_id"),
                            "title": row.get("title"),
                            "assignment_type": row.get("assignment_type"),
                            "score": float(row.get("score") or 0),
                            "total": float(row.get("total_score") or 0),
                            "status": row.get("status"),
                            "occurred_at": self._to_iso(row.get("occurred_at")),
                        }
                    )
                cursor.execute(
                    """
                    SELECT node_id, resource_id, resource_path, event_type,
                           duration_seconds, progress_percent, is_completed, occurred_at
                    FROM resource_learning_events
                    WHERE username = %s AND course_id = %s
                    ORDER BY occurred_at DESC, event_id DESC
                    LIMIT %s
                    """,
                    (username, course_id, limit),
                )
                for row in cursor.fetchall():
                    resource_items.append(
                        {
                            "type": "resource_learning",
                            "node_id": row.get("node_id"),
                            "resource_id": row.get("resource_id"),
                            "resource_path": row.get("resource_path"),
                            "event_type": row.get("event_type"),
                            "duration_seconds": int(row.get("duration_seconds") or 0),
                            "progress_percent": float(row.get("progress_percent") or 0),
                            "is_completed": bool(row.get("is_completed")),
                            "occurred_at": self._to_iso(row.get("occurred_at")),
                        }
                    )
        if hasattr(self.store, "list_learning_path_node_status"):
            records = self.store.list_learning_path_node_status(
                username,
                status="completed",
            )
            for row in records or []:
                if str(row.get("course_id") or "") != str(course_id):
                    continue
                node_id = str(row.get("node_id") or "").strip()
                if not node_id:
                    continue
                payload = self._loads_json(row.get("payload") or row.get("payload_json"), {})
                path_completion_items.append(
                    {
                        "type": "path_node_completion",
                        "status_id": row.get("status_id"),
                        "plan_id": row.get("plan_id"),
                        "course_id": row.get("course_id"),
                        "node_id": node_id,
                        "item_type": row.get("item_type"),
                        "source_type": row.get("source_type"),
                        "status": row.get("status"),
                        "mastery_before": row.get("mastery_before"),
                        "mastery_after": row.get("mastery_after"),
                        "occurred_at": self._to_iso(row.get("completed_at") or row.get("updated_at") or row.get("created_at")),
                        "summary": "个性化学习路径节点已完成，作为后续诊断和路径调整的辅助过程证据。",
                        "mastery_update_policy": "path_completion_is_auxiliary_evidence",
                        "payload": payload if isinstance(payload, dict) else {},
                    }
                )
        if hasattr(self.store, "list_fivee_effectiveness_records"):
            records = self.store.list_fivee_effectiveness_records(
                course_id=course_id,
                student_username=username,
                limit=limit,
            )
            for row in records or []:
                payload = self._loads_json(row.get("payload") or row.get("payload_json"), {})
                fivee_items.append(
                    {
                        "type": "fivee_effectiveness",
                        "record_id": row.get("record_id"),
                        "node_id": row.get("node_id"),
                        "stage": row.get("stage"),
                        "effectiveness_score": row.get("effectiveness_score"),
                        "effectiveness_level": payload.get("effectiveness_level"),
                        "evidence_status": payload.get("evidence_status"),
                        "completion_rate": row.get("completion_rate"),
                        "interaction_count": row.get("interaction_count"),
                        "valid_interaction_count": row.get("valid_interaction_count"),
                        "occurred_at": self._to_iso(row.get("calculated_at") or row.get("created_at")),
                        "summary": payload.get("summary") or "5E 引导互动记录",
                        "mastery_update_policy": payload.get("mastery_update_policy"),
                    }
                )
        if hasattr(self.store, "list_intervention_completion_evidence"):
            records = self.store.list_intervention_completion_evidence(
                course_id=course_id,
                student_username=username,
                limit=limit,
            )
            for row in records or []:
                record_payload = self._loads_json(row.get("record_payload") or row.get("payload_json"), {})
                package_payload = self._loads_json(row.get("package_payload"), {})
                progress = record_payload.get("progress") if isinstance(record_payload.get("progress"), dict) else {}
                answers = record_payload.get("answers") if isinstance(record_payload.get("answers"), list) else []
                grades = record_payload.get("grades") if isinstance(record_payload.get("grades"), list) else []
                score_summary = record_payload.get("score_summary") if isinstance(record_payload.get("score_summary"), dict) else {}
                items = row.get("items") if isinstance(row.get("items"), list) else []
                node_candidates = [
                    str(item.get("node_id") or "").strip()
                    for item in items
                    if isinstance(item, dict) and str(item.get("node_id") or "").strip()
                ]
                diagnosis = package_payload.get("diagnosis") if isinstance(package_payload.get("diagnosis"), dict) else {}
                weak_nodes = diagnosis.get("weak_nodes") if isinstance(diagnosis.get("weak_nodes"), list) else []
                if not node_candidates and weak_nodes:
                    node_candidates = [
                        str(item.get("node_id") or "").strip()
                        for item in weak_nodes
                        if isinstance(item, dict) and str(item.get("node_id") or "").strip()
                    ]
                intervention_items.append(
                    {
                        "type": "intervention_completion",
                        "package_id": row.get("package_id"),
                        "record_id": row.get("record_id"),
                        "teacher_username": row.get("teacher_username"),
                        "course_id": row.get("course_id"),
                        "node_id": node_candidates[0] if node_candidates else None,
                        "node_ids": node_candidates,
                        "title": row.get("package_title") or "教师干预任务包",
                        "status": row.get("status"),
                        "score": row.get("score") if row.get("score") is not None else score_summary.get("average_final_score"),
                        "completion_rate": progress.get("completion_rate"),
                        "answered_questions": progress.get("answered_questions"),
                        "total_questions": progress.get("total_questions"),
                        "graded_questions": score_summary.get("graded_questions"),
                        "answer_count": len([item for item in answers if isinstance(item, dict) and str(item.get("answer") or "").strip()]),
                        "teacher_graded": any(
                            isinstance(item, dict) and item.get("teacher_score") is not None
                            for item in grades
                        ),
                        "item_count": len(items),
                        "items": items,
                        "mastery_update_policy": "intervention_completion_is_auxiliary_evidence",
                        "occurred_at": self._to_iso(row.get("completed_at") or row.get("updated_at") or row.get("created_at")),
                        "summary": "教师干预任务已完成，作为学习证据回流画像、诊断和教师看板。",
                    }
                )
        timeline = quiz_items + homework_items + resource_items + fivee_items + intervention_items + path_completion_items
        timeline.sort(key=lambda item: item.get("occurred_at") or "", reverse=True)
        return timeline[:limit]

    def _diagnose_node(self, node: dict[str, Any], quiz: dict[str, Any], homework: dict[str, Any]) -> dict[str, Any]:
        mastery = float(node.get("mastery_score") or 0)
        quiz_count = int(quiz.get("attempt_count") or 0)
        assignment_count = int(homework.get("assignment_count") or 0)
        submission_count = int(homework.get("submission_count") or 0)
        graded_count = int(homework.get("graded_count") or 0)
        latest = self._latest_iso(
            [
                node.get("updated_at"),
                quiz.get("last_attempt_at"),
                quiz.get("last_any_attempt_at"),
                homework.get("last_evidence_at"),
            ]
        )

        confidence = self._node_confidence(node, quiz, homework, latest)
        evidence_level, insufficiency_reason = self._evidence_level(
            quiz_count=quiz_count,
            supplemental_quiz_count=int(quiz.get("supplemental_attempt_count") or 0),
            assignment_count=assignment_count,
            submission_count=submission_count,
            graded_count=graded_count,
            progress=float(node.get("progress") or 0),
            study_duration=float(node.get("study_duration_minutes") or 0),
            latest=latest,
        )
        quiz_avg = float(quiz.get("avg_score") or node.get("quiz_score") or 0)
        homework_avg = float(homework.get("avg_score") or 0)
        is_weak = (
            mastery < self.MASTERY_WEAK_THRESHOLD
            or (quiz_count > 0 and quiz_avg < self.QUIZ_WEAK_THRESHOLD)
            or (graded_count > 0 and homework_avg < self.HOMEWORK_WEAK_THRESHOLD)
        )
        reason_type = self._reason_type(
            evidence_level=evidence_level,
            mastery=mastery,
            quiz_count=quiz_count,
            quiz_avg=quiz_avg,
            graded_count=graded_count,
            homework_avg=homework_avg,
        )
        return {
            "node_id": node.get("node_id"),
            "node_path": node.get("node_path") or [],
            "mastery_score": round(mastery, 2),
            "quiz": quiz,
            "homework": homework,
            "is_weak": is_weak,
            "reason_type": reason_type,
            "evidence_level": evidence_level,
            "evidence_insufficiency_reason": insufficiency_reason,
            "confidence": confidence,
            "student_level": self._student_level(mastery),
            "student_message": self._student_message(node.get("node_id"), mastery, evidence_level),
            "teacher_explanation": self._teacher_explanation(reason_type, evidence_level, insufficiency_reason),
            "suggested_actions": self._suggested_actions(reason_type, evidence_level, assignment_count, submission_count),
            "latest_evidence_at": latest,
        }

    def _evidence_level(
        self,
        *,
        quiz_count: int,
        supplemental_quiz_count: int,
        assignment_count: int,
        submission_count: int,
        graded_count: int,
        progress: float,
        study_duration: float,
        latest: str | None,
    ) -> tuple[str, str | None]:
        if latest and self._is_stale(latest):
            return "insufficient", "stale"
        if assignment_count > 0 and submission_count == 0 and quiz_count == 0:
            return "insufficient", "assigned_but_not_completed"
        if quiz_count >= 2 and (graded_count >= 1 or progress >= 50 or study_duration >= 10):
            return "sufficient", None
        if quiz_count >= 1 or graded_count >= 1 or progress > 0 or study_duration > 0:
            reason = "small_sample" if quiz_count + graded_count < 2 else None
            return "partial", reason
        if supplemental_quiz_count > 0:
            return "partial", "supplemental_quiz_only"
        return "insufficient", "not_assigned_or_not_collected"

    def _node_confidence(self, node: dict[str, Any], quiz: dict[str, Any], homework: dict[str, Any], latest: str | None) -> float:
        score = 0.0
        score += min(int(quiz.get("attempt_count") or 0), 2) / 2 * 35
        score += min(int(homework.get("graded_count") or 0), 1) * 25
        if float(node.get("progress") or 0) > 0:
            score += 15
        if float(node.get("study_duration_minutes") or 0) > 0:
            score += 10
        if latest and not self._is_stale(latest):
            score += 15
        return round(min(score, 100.0), 2)

    def _reason_type(
        self,
        *,
        evidence_level: str,
        mastery: float,
        quiz_count: int,
        quiz_avg: float,
        graded_count: int,
        homework_avg: float,
    ) -> str:
        if evidence_level == "insufficient":
            return "evidence_insufficient"
        if quiz_count > 0 and quiz_avg < self.QUIZ_WEAK_THRESHOLD:
            return "quiz_errors_concentrated"
        if graded_count > 0 and homework_avg < self.HOMEWORK_WEAK_THRESHOLD:
            return "homework_or_code_practice_weak"
        if mastery < self.MASTERY_WEAK_THRESHOLD:
            return "mastery_low"
        return "currently_stable"

    def _suggested_actions(self, reason_type: str, evidence_level: str, assignment_count: int, submission_count: int) -> list[str]:
        if evidence_level == "insufficient":
            if assignment_count > 0 and submission_count == 0:
                return ["complete_assigned_homework", "take_quiz"]
            return ["take_quiz", "collect_learning_evidence"]
        if reason_type == "quiz_errors_concentrated":
            return ["review_resource", "take_quiz", "path_review"]
        if reason_type == "homework_or_code_practice_weak":
            return ["practice_homework", "ask_teacher", "path_review"]
        if reason_type == "mastery_low":
            return ["review_resource", "path_review"]
        return ["keep_learning"]

    def _overall_confidence(self, items: list[dict[str, Any]]) -> float:
        if not items:
            return 0.0
        return round(sum(float(item.get("confidence") or 0) for item in items) / len(items), 2)

    def _overall_evidence_level(self, items: list[dict[str, Any]]) -> str:
        if not items:
            return "insufficient"
        levels = [item.get("evidence_level") for item in items]
        if levels and all(level == "sufficient" for level in levels):
            return "sufficient"
        if any(level in {"sufficient", "partial"} for level in levels):
            return "partial"
        return "insufficient"

    def _build_summary(self, profile: dict[str, Any], weak_items: list[dict[str, Any]], evidence_level: str, confidence: float) -> str:
        overall = float(profile.get("overall_mastery") or 0)
        evidence_text = self._evidence_level_text(evidence_level)
        if not weak_items:
            return f"\u5f53\u524d\u6574\u4f53\u638c\u63e1\u5ea6\u7ea6\u4e3a {overall:.1f}%\uff0c\u6682\u672a\u53d1\u73b0\u660e\u786e\u8584\u5f31\u77e5\u8bc6\u70b9\uff1b\u8bca\u65ad\u4f9d\u636e\u4e3a{evidence_text}\uff0c\u7f6e\u4fe1\u5ea6 {confidence:.1f}\u3002"
        names = "\u3001".join(str(item.get("node_id")) for item in weak_items[:3])
        return f"\u5f53\u524d\u6574\u4f53\u638c\u63e1\u5ea6\u7ea6\u4e3a {overall:.1f}%\uff0c\u9700\u8981\u4f18\u5148\u5173\u6ce8 {names}\uff1b\u8bca\u65ad\u4f9d\u636e\u4e3a{evidence_text}\uff0c\u7f6e\u4fe1\u5ea6 {confidence:.1f}\u3002"

    def _build_student_view(self, weak_items: list[dict[str, Any]], evidence_level: str) -> dict[str, Any]:
        if not weak_items:
            return {
                "summary": "\u76ee\u524d\u5b66\u4e60\u72b6\u6001\u6bd4\u8f83\u7a33\u5b9a\uff0c\u7ee7\u7eed\u6309\u5f53\u524d\u8282\u594f\u5b8c\u6210\u5b66\u4e60\u4efb\u52a1\u5373\u53ef\u3002",
                "evidence_level": evidence_level,
                "next_steps": ["\u4fdd\u6301\u590d\u4e60\u8282\u594f", "\u5b8c\u6210\u540e\u7eed\u6d4b\u9a8c\u548c\u4f5c\u4e1a"],
            }
        next_steps: list[str] = []
        for item in weak_items[:3]:
            node_id = item.get("node_id")
            if item.get("evidence_level") == "insufficient":
                next_steps.append(f"\u5148\u5b8c\u6210\u201c{node_id}\u201d\u7684\u5c0f\u6d4b\u6216\u76f8\u5173\u4efb\u52a1\uff0c\u8865\u9f50\u5224\u65ad\u4f9d\u636e")
            else:
                next_steps.append(f"\u590d\u4e60\u201c{node_id}\u201d\uff0c\u518d\u5b8c\u6210\u4e00\u6b21\u5de9\u56fa\u7ec3\u4e60")
        return {
            "summary": "\u7cfb\u7edf\u53d1\u73b0\u6709\u51e0\u4e2a\u77e5\u8bc6\u70b9\u8fd8\u53ef\u4ee5\u7ee7\u7eed\u52a0\u5f3a\uff0c\u5efa\u8bae\u5148\u4ece\u6700\u5f71\u54cd\u540e\u7eed\u5b66\u4e60\u7684\u90e8\u5206\u5f00\u59cb\u3002",
            "evidence_level": evidence_level,
            "next_steps": next_steps,
        }

    def _student_evidence_timeline(self, timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        safe_items: list[dict[str, Any]] = []
        type_names = {
            "quiz": "\u6d4b\u9a8c\u8bb0\u5f55",
            "homework": "\u4f5c\u4e1a\u8bb0\u5f55",
            "resource_learning": "\u8d44\u6e90\u5b66\u4e60",
            "fivee_effectiveness": "5E \u5f15\u5bfc",
            "intervention_completion": "\u6559\u5e08\u5e72\u9884\u4efb\u52a1",
            "path_node_completion": "\u4e2a\u6027\u5316\u8def\u5f84",
        }
        for item in timeline[:12]:
            item_type = str(item.get("type") or "")
            node_id = item.get("node_id")
            title = item.get("title") or type_names.get(item_type, "\u5b66\u4e60\u8bb0\u5f55")
            summary_parts: list[str] = []
            if node_id:
                summary_parts.append(f"\u77e5\u8bc6\u70b9\uff1a{node_id}")
            if item_type in {"quiz", "homework"} and item.get("total"):
                score = float(item.get("score") or 0)
                total = float(item.get("total") or 0)
                summary_parts.append(f"\u5f97\u5206\uff1a{score:.1f}/{total:.1f}")
                if item_type == "quiz":
                    if item.get("evidence_status") == "formal_evidence":
                        summary_parts.append("\u6559\u5e08\u5df2\u53d1\u5e03\u6d4b\u9a8c\uff0c\u53ef\u7528\u4e8e\u6b63\u5f0f\u8bca\u65ad")
                    elif item.get("evidence_status") == "supplemental_evidence":
                        summary_parts.append("\u5b66\u4e60\u8fc7\u7a0b\u5c0f\u6d4b\uff0c\u4ec5\u4f5c\u8f85\u52a9\u53c2\u8003")
            elif item_type == "resource_learning":
                progress = float(item.get("progress_percent") or 0)
                summary_parts.append(f"\u5b66\u4e60\u8fdb\u5ea6\uff1a{progress:.0f}%")
            elif item_type == "fivee_effectiveness":
                if item.get("stage"):
                    summary_parts.append(f"5E \u9636\u6bb5\uff1a{self._stage_text(item.get('stage'))}")
                if item.get("effectiveness_level"):
                    summary_parts.append(f"\u5f15\u5bfc\u53cd\u9988\uff1a{item.get('effectiveness_level')}")
                if item.get("evidence_status") == "process_only":
                    summary_parts.append("\u9700\u8981\u7ed3\u5408\u540e\u7eed\u6d4b\u9a8c\u6216\u8def\u5f84\u5b8c\u6210\u60c5\u51b5\u5224\u65ad\u6548\u679c")
                elif item.get("evidence_status") == "insufficient_evidence":
                    summary_parts.append("\u4f9d\u636e\u5f85\u8865\u5145")
                if item.get("mastery_update_policy") == "not_updated_by_5e_effectiveness":
                    summary_parts.append("\u8f85\u52a9\u8bc1\u636e\uff0c\u4e0d\u76f4\u63a5\u6539\u5199\u638c\u63e1\u5ea6")
            elif item_type == "intervention_completion":
                completion_rate = item.get("completion_rate")
                if completion_rate is not None:
                    summary_parts.append(f"\u5b8c\u6210\u5ea6\uff1a{float(completion_rate) * 100:.0f}%")
                if item.get("score") is not None:
                    summary_parts.append(f"\u4efb\u52a1\u5f97\u5206\uff1a{float(item.get('score') or 0):.1f}")
                if item.get("teacher_graded"):
                    summary_parts.append("\u6559\u5e08\u5df2\u8bc4\u5206")
                summary_parts.append("\u5e72\u9884\u7ed3\u679c\u4f5c\u4e3a\u8f85\u52a9\u8bc1\u636e\u56de\u6d41\uff0c\u4e0d\u76f4\u63a5\u66ff\u4ee3\u6d4b\u9a8c\u6216\u4f5c\u4e1a\u7ed3\u8bba")
            elif item_type == "path_node_completion":
                before = item.get("mastery_before")
                after = item.get("mastery_after")
                if before is not None:
                    summary_parts.append(f"\u5b8c\u6210\u524d\u638c\u63e1\u5ea6\uff1a{float(before):.1f}")
                if after is not None:
                    summary_parts.append(f"\u5b8c\u6210\u540e\u81ea\u8bc4\u8bb0\u5f55\u638c\u63e1\u5ea6\uff1a{float(after):.1f}")
                summary_parts.append("\u8def\u5f84\u5b8c\u6210\u8bb0\u5f55\u4f5c\u4e3a\u8f85\u52a9\u8fc7\u7a0b\u8bc1\u636e\u56de\u6d41\uff0c\u4e0d\u76f4\u63a5\u66ff\u4ee3\u6d4b\u9a8c\u6216\u4f5c\u4e1a\u7ed3\u8bba")
            safe_items.append(
                {
                    "type": item_type,
                    "type_label": type_names.get(item_type, "\u5b66\u4e60\u8bb0\u5f55"),
                    "node_id": node_id,
                    "occurred_at": item.get("occurred_at"),
                    "title": title,
                    "stage": item.get("stage"),
                    "effectiveness_level": item.get("effectiveness_level"),
                    "evidence_status": item.get("evidence_status"),
                    "completion_rate": item.get("completion_rate"),
                    "mastery_update_policy": item.get("mastery_update_policy"),
                    "summary": "\uff1b".join(summary_parts) if summary_parts else str(title),
                }
            )
        return safe_items

    def _evidence_level_text(self, level: str | None) -> str:
        mapping = {
            "sufficient": "\u5145\u5206",
            "partial": "\u90e8\u5206\u5145\u5206",
            "insufficient": "\u4e0d\u8db3",
        }
        return mapping.get(str(level or ""), str(level or "\u672a\u77e5"))

    def _stage_text(self, stage: Any) -> str:
        mapping = {
            "engagement": "\u5bfc\u5165\u53c2\u4e0e",
            "exploration": "\u63a2\u7d22\u8d44\u6e90",
            "explanation": "\u89e3\u91ca\u5efa\u6784",
            "elaboration": "\u8fc1\u79fb\u5e94\u7528",
            "evaluation": "\u6d4b\u8bc4\u53cd\u9988",
        }
        return mapping.get(str(stage or ""), str(stage or "\u5b66\u4e60\u4e92\u52a8"))

    def _teacher_explanation(self, reason_type: str, evidence_level: str, insufficiency_reason: str | None) -> str:
        if evidence_level == "insufficient":
            reason_map = {
                "not_assigned_or_not_collected": "当前未采集到足够测验、作业或学习行为证据。",
                "assigned_but_not_completed": "已有相关任务，但学生尚未完成，暂不宜给出强诊断。",
                "small_sample": "已有少量证据，但样本次数偏少，建议补充测验或练习。",
                "stale": "最近有效证据时间较旧，建议补充近期学习证据。",
            }
            return reason_map.get(insufficiency_reason or "", "当前证据不足，建议补充学习证据。")
        reason_map = {
            "quiz_errors_concentrated": "测验正确率偏低，优先检查概念理解和易错点。",
            "homework_or_code_practice_weak": "作业或代码题表现偏弱，优先安排实践练习和反馈。",
            "mastery_low": "画像掌握度偏低，建议复习资源并跟进后续测验。",
            "currently_stable": "当前知识点暂未出现明显风险。",
        }
        return reason_map.get(reason_type, "需要结合证据继续观察。")

    def _student_level(self, mastery: float) -> str:
        if mastery < 60:
            return "待提升"
        if mastery < 80:
            return "基本达成"
        return "较好达成"

    def _student_message(self, node_id: Any, mastery: float, evidence_level: str) -> str:
        if evidence_level == "insufficient":
            return f"“{node_id}”的学习记录还不够完整，先完成一次小测或练习，系统就能给出更准确建议。"
        if mastery < 60:
            return f"“{node_id}”还需要补一补，建议先看资源，再做一次练习巩固。"
        return f"“{node_id}”已经有一定基础，继续保持并完成后续任务。"

    def _persist_report(self, report: dict[str, Any]) -> None:
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO diagnosis_reports
                    (report_id, user_id, username, course_id, report_date, persona_summary,
                     evidence_level, confidence, payload_json, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report["report_id"],
                        report.get("user_id"),
                        report["username"],
                        report["course_id"],
                        report["report_date"],
                        report["persona_summary"],
                        report["evidence_level"],
                        report["confidence"],
                        json.dumps(report, ensure_ascii=False),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )

    def _loads_json(self, value: Any, fallback: Any) -> Any:
        if value is None:
            return fallback
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(str(value))
        except Exception:
            return fallback

    def _quiz_payload_extra(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        extra = payload.get("extra")
        if isinstance(extra, dict):
            return extra
        return {}

    def _is_published_quiz_evidence(self, payload_or_extra: Any) -> bool:
        extra = self._quiz_payload_extra(payload_or_extra)
        if not extra and isinstance(payload_or_extra, dict):
            extra = payload_or_extra
        evidence_policy = str(extra.get("evidence_policy") or "").strip()
        definition_status = str(extra.get("definition_status") or "").strip()
        return evidence_policy == "published_quiz_definition" or definition_status == "published"

    def _to_iso(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat(timespec="seconds")
        return str(value)

    def _latest_iso(self, values: list[Any]) -> str | None:
        parsed = []
        for value in values:
            dt = self._parse_datetime(value)
            if dt:
                parsed.append(dt)
        if not parsed:
            return None
        return max(parsed).isoformat(timespec="seconds")

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        if not text:
            return None
        text = text.replace("Z", "").replace("T", " ")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(text[: len(fmt)], fmt)
                except ValueError:
                    continue
        return None

    def _is_stale(self, value: str) -> bool:
        dt = self._parse_datetime(value)
        if not dt:
            return False
        return dt < datetime.now() - timedelta(days=self.RECENT_DAYS)
