from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from DatabaseModule.database_factory import DatabaseFactory


class HomeworkEvidenceService:
    """Aggregate homework evidence for student twin and diagnosis views."""

    PRACTICE_TYPES = {"subjective", "code", "coding"}
    CODE_WEIGHT = 1.5
    SUBJECTIVE_WEIGHT = 1.0
    COVERAGE_WEIGHT = 0.25

    def __init__(self) -> None:
        self.store = DatabaseFactory.get_store()

    def build_student_evidence(self, username: str, course_id: str | None = None) -> dict[str, Any]:
        rows = self._load_graded_homework_rows(username, course_id)
        chapters = self._build_chapter_practice(rows)
        coverage = self._build_coverage_evidence(rows)
        return {
            "student_username": username,
            "course_id": course_id,
            "chapter_practice": chapters,
            "knowledge_point_homework_evidence": coverage,
            "practice_summary": self._build_summary(chapters, coverage),
        }

    def _load_graded_homework_rows(self, username: str, course_id: str | None) -> list[dict[str, Any]]:
        params: list[Any] = [username]
        course_clause = ""
        if course_id:
            course_clause = " AND a.course_id = %s"
            params.append(course_id)
        with self.store.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        a.id AS assignment_id,
                        a.title,
                        a.assignment_type,
                        a.course_id,
                        a.node_id AS assignment_node_id,
                        a.node_name,
                        a.node_path_json,
                        a.chapter_context,
                        a.total_score,
                        s.id AS submission_id,
                        s.student_username,
                        COALESCE(s.teacher_score, s.ai_score) AS score,
                        s.teacher_score,
                        s.ai_score,
                        s.status,
                        COALESCE(s.graded_at, s.submitted_at, s.updated_at) AS evidence_at,
                        kp.node_id AS covered_node_id,
                        kp.confirmed_by_teacher,
                        kp.recommended_by_system,
                        kp.confidence,
                        kp.reason AS coverage_reason
                    FROM homework_submissions s
                    JOIN homework_assignments a ON a.id = s.assignment_id
                    LEFT JOIN homework_assignment_knowledge_points kp
                        ON kp.assignment_id = a.id AND COALESCE(kp.confirmed_by_teacher, 0) = 1
                    WHERE s.student_username = %s
                      AND COALESCE(a.status, '') = 'published'
                      AND s.status = 'graded'
                      AND COALESCE(s.teacher_score, s.ai_score) IS NOT NULL
                      {course_clause}
                    ORDER BY COALESCE(s.graded_at, s.submitted_at, s.updated_at) DESC
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def _build_chapter_practice(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        seen: set[tuple[str, str]] = set()
        for row in rows:
            assignment_type = self._normalize_assignment_type(row.get("assignment_type"))
            if assignment_type not in self.PRACTICE_TYPES:
                continue
            key = (str(row.get("assignment_id") or ""), str(row.get("submission_id") or ""))
            if key in seen:
                continue
            seen.add(key)
            percent = self._score_percent(row)
            if percent is None:
                continue
            chapter = self._chapter_key(row)
            weight = self.CODE_WEIGHT if assignment_type in {"code", "coding"} else self.SUBJECTIVE_WEIGHT
            grouped[chapter].append(
                {
                    "assignment_id": row.get("assignment_id"),
                    "submission_id": row.get("submission_id"),
                    "title": row.get("title"),
                    "assignment_type": assignment_type,
                    "score_percent": round(percent, 2),
                    "weight": weight,
                    "evidence_at": self._to_iso(row.get("evidence_at")),
                }
            )

        result = []
        for chapter, items in sorted(grouped.items()):
            weight_sum = sum(float(item["weight"]) for item in items)
            weighted = sum(float(item["score_percent"]) * float(item["weight"]) for item in items)
            score = round(weighted / weight_sum, 2) if weight_sum else 0.0
            result.append(
                {
                    "chapter": chapter,
                    "practice_score": score,
                    "practice_level": self._level(score),
                    "evidence_count": len(items),
                    "code_evidence_count": sum(1 for item in items if item["assignment_type"] in {"code", "coding"}),
                    "subjective_evidence_count": sum(1 for item in items if item["assignment_type"] == "subjective"),
                    "latest_evidence_at": self._latest(item.get("evidence_at") for item in items),
                    "evidence_items": items[:5],
                    "calculation_note": "章节实践能力只读取章节主观题和代码题；代码题权重 1.5，主观题权重 1.0。",
                }
            )
        return result

    def _build_coverage_evidence(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        seen: set[tuple[str, str, str]] = set()
        for row in rows:
            node_id = str(row.get("covered_node_id") or "").strip()
            if not node_id:
                continue
            key = (node_id, str(row.get("assignment_id") or ""), str(row.get("submission_id") or ""))
            if key in seen:
                continue
            seen.add(key)
            percent = self._score_percent(row)
            if percent is None:
                continue
            grouped[node_id].append(
                {
                    "assignment_id": row.get("assignment_id"),
                    "submission_id": row.get("submission_id"),
                    "title": row.get("title"),
                    "assignment_type": self._normalize_assignment_type(row.get("assignment_type")),
                    "score_percent": round(percent, 2),
                    "evidence_at": self._to_iso(row.get("evidence_at")),
                    "coverage_confidence": self._float_or_none(row.get("confidence")),
                    "coverage_reason": row.get("coverage_reason") or "",
                }
            )

        result = []
        for node_id, items in sorted(grouped.items()):
            avg_score = round(sum(float(item["score_percent"]) for item in items) / len(items), 2)
            result.append(
                {
                    "node_id": node_id,
                    "auxiliary_score": avg_score,
                    "weighted_mastery_delta": round((avg_score - 60.0) * self.COVERAGE_WEIGHT, 2),
                    "evidence_count": len(items),
                    "latest_evidence_at": self._latest(item.get("evidence_at") for item in items),
                    "evidence_items": items[:5],
                    "calculation_note": "只有教师确认覆盖知识点的作业才作为叶子知识点辅助证据，不替代测验证据。",
                }
            )
        return result

    def _build_summary(self, chapters: list[dict[str, Any]], coverage: list[dict[str, Any]]) -> dict[str, Any]:
        if chapters:
            average = round(sum(float(item["practice_score"]) for item in chapters) / len(chapters), 2)
        else:
            average = None
        return {
            "chapter_count": len(chapters),
            "average_practice_score": average,
            "practice_level": self._level(average) if average is not None else "依据不足",
            "coverage_node_count": len(coverage),
            "coverage_evidence_count": sum(int(item.get("evidence_count") or 0) for item in coverage),
        }

    def _score_percent(self, row: dict[str, Any]) -> float | None:
        score = self._float_or_none(row.get("score"))
        total = self._float_or_none(row.get("total_score"))
        if score is None:
            return None
        if total and total > 0:
            return max(0.0, min(score / total * 100.0, 100.0))
        return max(0.0, min(score, 100.0))

    def _chapter_key(self, row: dict[str, Any]) -> str:
        chapter = str(row.get("chapter_context") or "").strip()
        if chapter:
            return chapter
        path = self._loads_json(row.get("node_path_json"), [])
        if isinstance(path, list) and path:
            return str(path[0])
        return str(row.get("node_name") or row.get("assignment_node_id") or "未绑定章节")

    def _normalize_assignment_type(self, value: Any) -> str:
        raw = str(value or "subjective").strip().lower()
        if raw == "code_practice":
            return "code"
        if raw == "coding":
            return "code"
        return raw

    def _level(self, score: float | None) -> str:
        if score is None:
            return "依据不足"
        if score < 60:
            return "待提升"
        if score < 80:
            return "基本达成"
        return "较好达成"

    def _loads_json(self, value: Any, fallback: Any) -> Any:
        if value is None:
            return fallback
        if isinstance(value, (list, dict)):
            return value
        try:
            return json.loads(str(value))
        except Exception:
            return fallback

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_iso(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat(timespec="seconds")
        return str(value)

    def _latest(self, values: Any) -> str | None:
        parsed: list[datetime] = []
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
        text = str(value).strip().replace("T", " ").replace("Z", "")
        if not text:
            return None
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
