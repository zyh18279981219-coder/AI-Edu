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

        node_rows = self._load_profile_nodes(username, course_id)
        if not node_rows:
            node_rows = self._profile_nodes_without_course(profile, course_id)

        resolved_course_id = course_id or self._dominant_course_id(node_rows) or "course_big_data"
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
                "quiz_score_percent": "avg(score / total * 100) for valid quiz attempts",
                "homework_score_percent": "avg(coalesce(teacher_score, ai_score) / assignment.total_score * 100)",
                "confidence": "min(100, quiz_evidence*35 + homework_evidence*25 + profile_progress*15 + study_duration*10 + recent_evidence*15); resource_learning_events are used as evidence timeline items",
            },
            "thresholds": {
                "weak_mastery": self.MASTERY_WEAK_THRESHOLD,
                "weak_quiz": self.QUIZ_WEAK_THRESHOLD,
                "weak_homework": self.HOMEWORK_WEAK_THRESHOLD,
                "recent_evidence_days": self.RECENT_DAYS,
            },
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        if persist:
            self._persist_report(result)
        return result

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
                           COUNT(*) AS attempt_count,
                           AVG(CASE WHEN total > 0 THEN score / total * 100 ELSE score END) AS avg_score,
                           MAX(created_at) AS last_attempt_at
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
                "last_attempt_at": self._to_iso(row.get("last_attempt_at")),
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
                    SELECT a.node_id,
                           COUNT(DISTINCT a.id) AS assignment_count,
                           COUNT(s.id) AS submission_count,
                           SUM(CASE WHEN s.status = 'graded' THEN 1 ELSE 0 END) AS graded_count,
                           AVG(CASE
                               WHEN s.id IS NOT NULL AND a.total_score > 0
                               THEN COALESCE(s.teacher_score, s.ai_score, 0) / a.total_score * 100
                               ELSE NULL
                           END) AS avg_score,
                           MAX(COALESCE(s.graded_at, s.submitted_at, a.updated_at, a.created_at)) AS last_evidence_at
                    FROM homework_assignments a
                    LEFT JOIN homework_submissions s
                        ON s.assignment_id = a.id AND s.student_username = %s
                    WHERE a.course_id = %s AND a.node_id IN ({placeholders})
                          AND COALESCE(a.status, '') = 'published'
                    GROUP BY a.node_id
                    """,
                    tuple([username, course_id, *node_ids]),
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
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT node_id, score, total, passed, created_at
                    FROM quiz_attempts
                    WHERE username = %s AND course_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (username, course_id, limit),
                )
                for row in cursor.fetchall():
                    quiz_items.append(
                        {
                            "type": "quiz",
                            "node_id": row.get("node_id"),
                            "score": float(row.get("score") or 0),
                            "total": float(row.get("total") or 0),
                            "passed": bool(row.get("passed")),
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
        timeline = quiz_items + homework_items + resource_items
        timeline.sort(key=lambda item: item.get("occurred_at") or "", reverse=True)
        return timeline[:limit]

    def _diagnose_node(self, node: dict[str, Any], quiz: dict[str, Any], homework: dict[str, Any]) -> dict[str, Any]:
        mastery = float(node.get("mastery_score") or 0)
        quiz_count = int(quiz.get("attempt_count") or 0)
        assignment_count = int(homework.get("assignment_count") or 0)
        submission_count = int(homework.get("submission_count") or 0)
        graded_count = int(homework.get("graded_count") or 0)
        latest = self._latest_iso([node.get("updated_at"), quiz.get("last_attempt_at"), homework.get("last_evidence_at")])

        confidence = self._node_confidence(node, quiz, homework, latest)
        evidence_level, insufficiency_reason = self._evidence_level(
            quiz_count=quiz_count,
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
        if not weak_items:
            return f"当前整体掌握度约为 {overall:.1f}，暂未发现明确薄弱知识点；诊断依据为{evidence_level}，置信度 {confidence:.1f}。"
        names = "、".join(str(item.get("node_id")) for item in weak_items[:3])
        return f"当前整体掌握度约为 {overall:.1f}，需要优先关注 {names}；诊断依据为{evidence_level}，置信度 {confidence:.1f}。"

    def _build_student_view(self, weak_items: list[dict[str, Any]], evidence_level: str) -> dict[str, Any]:
        if not weak_items:
            return {
                "summary": "目前学习状态比较稳定，继续按当前节奏完成学习任务即可。",
                "next_steps": ["保持复习节奏", "完成后续测验和作业"],
            }
        next_steps: list[str] = []
        for item in weak_items[:3]:
            if item.get("evidence_level") == "insufficient":
                next_steps.append(f"先完成“{item.get('node_id')}”的小测或相关任务，补齐判断依据")
            else:
                next_steps.append(f"复习“{item.get('node_id')}”，再完成一次巩固练习")
        return {
            "summary": "系统发现有几个知识点还可以继续加强，先从最影响后续学习的部分开始。",
            "evidence_level": evidence_level,
            "next_steps": next_steps,
        }

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
