from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, List, Optional

from DatabaseModule.sqlite_store import get_sqlite_store


@dataclass
class MetricSource:
    field: str
    source: str
    status: str
    note: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "field": self.field,
            "source": self.source,
            "status": self.status,
            "note": self.note,
        }


class TeacherTwinService:
    """Build teacher digital twin summary using existing platform data."""

    def __init__(self) -> None:
        self.store = get_sqlite_store()

    def build_summary(self, teacher_username: str) -> Dict[str, Any]:
        now = datetime.now()
        teacher = self.store.get_user("teacher", teacher_username)
        if not teacher:
            raise ValueError(f"Teacher '{teacher_username}' not found")

        students = self._resolve_teacher_students(teacher)
        student_twins = [
            self.store.get_twin_profile(student_username)
            for student_username in students
        ]
        student_twins = [item for item in student_twins if item]

        sessions = [
            item
            for item in self.store.list_sessions()
            if item.get("username") == teacher_username and item.get("user_type") == "teacher"
        ]
        logs = [
            item for item in self.store.list_llm_logs(limit=4000)
            if item.get("username") == teacher_username
        ]
        plans = [
            item for item in self.store.list_learning_plans(username=teacher_username)
        ]

        external = self._load_external_metrics(teacher_username)

        dim1 = self._dimension_professional_engagement(now, sessions, logs, external)
        dim2 = self._dimension_digital_resources(now, plans, external)
        dim3 = self._dimension_teaching_learning(now, logs, plans, sessions, external)
        dim4 = self._dimension_assessment(now, logs, external)
        dim5 = self._dimension_empowering_learners(now, students, student_twins, logs, external)
        dim6 = self._dimension_facilitating_digital_competence(now, plans, logs, external)

        dimensions = [dim1, dim2, dim3, dim4, dim5, dim6]
        overall = round(mean([item["score"] for item in dimensions]), 2)
        radar = [{"name": item["name"], "value": item["score"]} for item in dimensions]
        weakest = sorted(dimensions, key=lambda item: item["score"])[:2]

        return {
            "teacher_username": teacher_username,
            "teacher_name": teacher.get("name", teacher_username),
            "last_updated": now.isoformat(),
            "overall_score": overall,
            "radar": radar,
            "dimensions": dimensions,
            "teaching_strategy_suggestions": self._build_teaching_suggestions(weakest),
            "intervention_suggestions": self._build_intervention_suggestions(weakest),
            "student_scope": {
                "student_count": len(students),
                "students_with_twin": len(student_twins),
                "students": students,
            },
            "missing_data_hooks": self._build_missing_data_hooks(),
            "data_sources": self._build_data_sources(),
        }

    def _resolve_teacher_students(self, teacher: Dict[str, Any]) -> List[str]:
        raw = teacher.get("students") or []
        students = [item for item in raw if isinstance(item, str) and item]
        if students:
            return sorted(set(students))

        linked = []
        for student in self.store.list_users("student"):
            if student.get("teacher") == teacher.get("username"):
                username = student.get("username")
                if username:
                    linked.append(username)
        return sorted(set(linked))

    def _dimension_professional_engagement(
        self,
        now: datetime,
        sessions: List[Dict[str, Any]],
        logs: List[Dict[str, Any]],
        external: Dict[str, Any],
    ) -> Dict[str, Any]:
        last_7 = now - timedelta(days=7)
        active_sessions = [s for s in sessions if self._parse_time(s.get("last_accessed")) and self._parse_time(s.get("last_accessed")) >= last_7]
        weekly_hours = round(sum(self._session_minutes(item) for item in active_sessions) / 60.0, 2)
        login_frequency = len(active_sessions)

        collab_posts = self._safe_float(external.get("research_posts"))
        shared_courseware = self._safe_float(external.get("shared_courseware"))
        co_preparation = self._safe_float(external.get("co_preparation_count"))

        advanced_features = self._count_advanced_feature_usage(logs)
        collaboration_score = self._bounded((collab_posts * 8) + (shared_courseware * 6) + (co_preparation * 7), 100)
        score = round(
            (self._bounded(weekly_hours * 10, 100) * 0.35)
            + (self._bounded(login_frequency * 8, 100) * 0.25)
            + (collaboration_score * 0.2)
            + (self._bounded(advanced_features * 5, 100) * 0.2),
            2,
        )

        return {
            "code": "professional_engagement",
            "name": "专业投入",
            "score": score,
            "sub_items": {
                "platform_activity": {
                    "weekly_online_hours": weekly_hours,
                    "weekly_login_frequency": login_frequency,
                },
                "teaching_research_collaboration": {
                    "posts": collab_posts,
                    "shared_courseware": shared_courseware,
                    "co_preparation_frequency": co_preparation,
                },
                "feature_exploration": {
                    "advanced_feature_usage_count": advanced_features,
                },
            },
        }

    def _dimension_digital_resources(
        self,
        now: datetime,
        plans: List[Dict[str, Any]],
        external: Dict[str, Any],
    ) -> Dict[str, Any]:
        del now
        formats = set()
        iterations = 0
        shared_reuse = self._safe_float(external.get("resource_referenced_by_others"))

        for plan in plans:
            filename = str(plan.get("filename", ""))
            suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
            if suffix:
                formats.add(suffix)
            updates = self._safe_float((plan.get("data") or {}).get("revision_count"))
            if updates > 0:
                iterations += int(updates)

        if iterations == 0:
            iterations = len(plans)

        score = round(
            (self._bounded(len(formats) * 18, 100) * 0.4)
            + (self._bounded(iterations * 6, 100) * 0.35)
            + (self._bounded(shared_reuse * 8, 100) * 0.25),
            2,
        )

        return {
            "code": "digital_resources",
            "name": "数字资源",
            "score": score,
            "sub_items": {
                "resource_diversity_index": {
                    "format_count": len(formats),
                    "formats": sorted(list(formats)),
                },
                "resource_iteration_frequency": {
                    "revision_count": iterations,
                    "resource_count": len(plans),
                },
                "resource_reuse_and_sharing": {
                    "referenced_by_other_teachers": shared_reuse,
                },
            },
        }

    def _dimension_teaching_learning(
        self,
        now: datetime,
        logs: List[Dict[str, Any]],
        plans: List[Dict[str, Any]],
        sessions: List[Dict[str, Any]],
        external: Dict[str, Any],
    ) -> Dict[str, Any]:
        last_30 = now - timedelta(days=30)
        recent_logs = [item for item in logs if self._is_in_days(item.get("timestamp"), last_30)]

        announcements = self._count_by_meta_key(recent_logs, "action", {"announcement", "publish_announcement"})
        discussion_topics = self._count_by_meta_key(recent_logs, "action", {"discussion_topic", "start_discussion"})
        teacher_reply_rate = self._safe_float(external.get("teacher_reply_rate"))
        avg_response_minutes = self._safe_float(external.get("avg_response_minutes"), default=120.0)

        on_time_release_ratio = self._safe_float(external.get("on_time_release_ratio"), default=0.7)
        ai_recommended_actions = self._count_ai_recommended_actions(recent_logs)
        ai_executed_actions = self._count_ai_executed_actions(recent_logs)
        ai_execution_rate = 0.0
        if ai_recommended_actions > 0:
            ai_execution_rate = ai_executed_actions / ai_recommended_actions

        interactive_score = self._bounded((announcements * 4) + (discussion_topics * 5) + (teacher_reply_rate * 100 * 0.6), 100)
        rhythm_score = self._bounded(on_time_release_ratio * 100, 100)
        ai_score = self._bounded(ai_execution_rate * 100, 100)

        score = round((interactive_score * 0.45) + (rhythm_score * 0.3) + (ai_score * 0.25), 2)

        return {
            "code": "teaching_learning",
            "name": "教学与学习",
            "score": score,
            "sub_items": {
                "online_interaction_frequency": {
                    "announcements": announcements,
                    "discussion_topics": discussion_topics,
                    "teacher_reply_rate": round(teacher_reply_rate, 4),
                    "avg_response_minutes": round(avg_response_minutes, 2),
                },
                "teaching_rhythm_control": {
                    "on_time_release_ratio": round(on_time_release_ratio, 4),
                    "session_count": len(sessions),
                },
                "human_ai_collaboration": {
                    "ai_recommended_actions": ai_recommended_actions,
                    "ai_executed_actions": ai_executed_actions,
                    "ai_execution_rate": round(ai_execution_rate, 4),
                },
            },
        }

    def _dimension_assessment(
        self,
        now: datetime,
        logs: List[Dict[str, Any]],
        external: Dict[str, Any],
    ) -> Dict[str, Any]:
        last_30 = now - timedelta(days=30)
        recent_logs = [item for item in logs if self._is_in_days(item.get("timestamp"), last_30)]

        assessment_types = set()
        subjective_feedback_count = 0
        subjective_feedback_length = []
        grading_minutes = []
        remediation_count = 0

        for log in recent_logs:
            metadata = log.get("metadata") or {}
            assess_type = metadata.get("assessment_type")
            if isinstance(assess_type, str) and assess_type:
                assessment_types.add(assess_type)
            if metadata.get("feedback_text"):
                feedback_text = str(metadata.get("feedback_text"))
                subjective_feedback_count += 1
                subjective_feedback_length.append(len(feedback_text))
            if metadata.get("grading_minutes") is not None:
                grading_minutes.append(self._safe_float(metadata.get("grading_minutes")))
            if metadata.get("action") in {"remediation_material", "remediation_announcement"}:
                remediation_count += 1

        if not grading_minutes:
            manual = self._safe_float(external.get("subjective_grading_minutes"), default=0.0)
            if manual > 0:
                grading_minutes = [manual]

        avg_feedback_length = round(mean(subjective_feedback_length), 2) if subjective_feedback_length else 0.0
        avg_grading_minutes = round(mean(grading_minutes), 2) if grading_minutes else 0.0

        score = round(
            (self._bounded(len(assessment_types) * 24, 100) * 0.4)
            + (self._bounded((100 - min(avg_grading_minutes, 100)) * 0.5 + min(avg_feedback_length / 2.0, 50), 100) * 0.35)
            + (self._bounded(remediation_count * 18, 100) * 0.25),
            2,
        )

        return {
            "code": "assessment",
            "name": "评估",
            "score": score,
            "sub_items": {
                "assessment_diversification": {
                    "assessment_types": sorted(list(assessment_types)),
                    "type_count": len(assessment_types),
                },
                "feedback_timeliness_and_depth": {
                    "subjective_feedback_count": subjective_feedback_count,
                    "avg_feedback_length": avg_feedback_length,
                    "avg_grading_minutes": avg_grading_minutes,
                },
                "data_driven_adjustment": {
                    "remediation_actions": remediation_count,
                },
            },
        }

    def _dimension_empowering_learners(
        self,
        now: datetime,
        students: List[str],
        student_twins: List[Dict[str, Any]],
        logs: List[Dict[str, Any]],
        external: Dict[str, Any],
    ) -> Dict[str, Any]:
        del now
        personalized_push = self._safe_float(external.get("personalized_push_count"))
        risk_interventions = self._safe_float(external.get("risk_intervention_count"))

        low_mastery_students = sum(1 for twin in student_twins if self._safe_float(twin.get("overall_mastery")) < 60)
        intervention_ratio = 0.0
        if low_mastery_students > 0:
            intervention_ratio = min(risk_interventions / low_mastery_students, 1.0)

        non_forced_engagement = self._calc_non_forced_engagement(logs, students)

        personalized_rate = 0.0
        if students:
            personalized_rate = min(personalized_push / len(students), 1.0)

        score = round(
            (self._bounded(personalized_rate * 100, 100) * 0.4)
            + (self._bounded(intervention_ratio * 100, 100) * 0.35)
            + (self._bounded(non_forced_engagement * 100, 100) * 0.25),
            2,
        )

        return {
            "code": "empowering_learners",
            "name": "赋能学习者",
            "score": score,
            "sub_items": {
                "personalized_path_dispatch_rate": {
                    "personalized_push_count": personalized_push,
                    "student_count": len(students),
                    "dispatch_rate": round(personalized_rate, 4),
                },
                "intervention_strategy_execution": {
                    "risk_intervention_count": risk_interventions,
                    "at_risk_student_count": low_mastery_students,
                    "execution_ratio": round(intervention_ratio, 4),
                },
                "student_initiative_feedback": {
                    "non_forced_engagement": round(non_forced_engagement, 4),
                },
            },
        }

    def _dimension_facilitating_digital_competence(
        self,
        now: datetime,
        plans: List[Dict[str, Any]],
        logs: List[Dict[str, Any]],
        external: Dict[str, Any],
    ) -> Dict[str, Any]:
        last_90 = now - timedelta(days=90)
        recent_logs = [item for item in logs if self._is_in_days(item.get("timestamp"), last_90)]

        total_tasks = self._safe_float(external.get("total_tasks"), default=max(len(plans), 1))
        digital_tasks = self._safe_float(external.get("digital_tasks"), default=0.0)
        collaborative_tasks = self._safe_float(external.get("collaborative_tasks"), default=0.0)
        inquiry_hours = self._safe_float(external.get("inquiry_learning_hours"), default=0.0)
        total_hours = self._safe_float(external.get("total_teaching_hours"), default=1.0)

        if digital_tasks <= 0:
            digital_tasks = self._count_by_meta_key(recent_logs, "task_mode", {"digital", "video", "coding", "mindmap"})
        if collaborative_tasks <= 0:
            collaborative_tasks = self._count_by_meta_key(recent_logs, "task_group_mode", {"group", "collaboration"})
        if inquiry_hours <= 0:
            inquiry_hours = self._safe_float(self._count_by_meta_key(recent_logs, "task_type", {"inquiry", "open_question"}))

        digital_ratio = min(digital_tasks / total_tasks, 1.0) if total_tasks > 0 else 0.0
        collaborative_ratio = min(collaborative_tasks / total_tasks, 1.0) if total_tasks > 0 else 0.0
        inquiry_ratio = min(inquiry_hours / total_hours, 1.0) if total_hours > 0 else 0.0

        score = round(
            (self._bounded(digital_ratio * 100, 100) * 0.4)
            + (self._bounded(collaborative_ratio * 100, 100) * 0.3)
            + (self._bounded(inquiry_ratio * 100, 100) * 0.3),
            2,
        )

        return {
            "code": "facilitating_digital_competence",
            "name": "促进学习者数字能力",
            "score": score,
            "sub_items": {
                "digital_task_ratio": {
                    "digital_tasks": digital_tasks,
                    "total_tasks": total_tasks,
                    "ratio": round(digital_ratio, 4),
                },
                "collaborative_task_design": {
                    "collaborative_tasks": collaborative_tasks,
                    "ratio": round(collaborative_ratio, 4),
                },
                "inquiry_learning_configuration": {
                    "inquiry_learning_hours": inquiry_hours,
                    "total_teaching_hours": total_hours,
                    "ratio": round(inquiry_ratio, 4),
                },
            },
        }

    def _build_teaching_suggestions(self, weakest: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        suggestions: List[Dict[str, str]] = []
        for item in weakest:
            code = item.get("code")
            if code == "assessment":
                suggestions.append(
                    {
                        "dimension": item["name"],
                        "advice": "增加形成性评价闭环：每次测验后 24 小时内发布错题讲解或补充任务。",
                    }
                )
            elif code == "teaching_learning":
                suggestions.append(
                    {
                        "dimension": item["name"],
                        "advice": "将课程公告、讨论发起和答疑响应纳入每周固定节奏，并优先执行 AI 推荐教学动作。",
                    }
                )
            elif code == "digital_resources":
                suggestions.append(
                    {
                        "dimension": item["name"],
                        "advice": "扩展资源形态并提高复用率：每章至少提供 2 种媒体格式，并开放共享可复用资源。",
                    }
                )
            else:
                suggestions.append(
                    {
                        "dimension": item["name"],
                        "advice": "围绕该维度设置周目标并结合平台日志进行复盘，持续提升数字教学能力。",
                    }
                )
        return suggestions

    def _build_intervention_suggestions(self, weakest: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        return [
            {
                "trigger": f"{item['name']} 分值低于阈值",
                "action": "触发教师侧干预策略：生成改进清单、推送智能体建议、跟踪下周改进幅度。",
            }
            for item in weakest
        ]

    def _load_external_metrics(self, teacher_username: str) -> Dict[str, Any]:
        """
        Reserved integration point.
        External ETL or module can write data into user_states with key: teacher_ext::{username}
        """
        key = f"teacher_ext::{teacher_username}"
        raw = self.store.get_user_state(key) or {}
        if isinstance(raw, dict):
            return raw
        return {}

    def _build_missing_data_hooks(self) -> List[Dict[str, str]]:
        hooks = [
            MetricSource(
                field="teaching_research_collaboration",
                source="teacher_ext::<username>.research_posts/shared_courseware/co_preparation_count",
                status="reserved",
                note="待接入教研区/备课组行为日志后自动生效",
            ),
            MetricSource(
                field="feedback_timeliness_and_depth",
                source="teacher_ext::<username>.subjective_grading_minutes",
                status="reserved",
                note="待接入作业批改明细后自动计算平均批改耗时",
            ),
            MetricSource(
                field="empowering_learners",
                source="teacher_ext::<username>.personalized_push_count/risk_intervention_count",
                status="reserved",
                note="待对接学生孪生预警联动日志后自动更新",
            ),
        ]
        return [item.to_dict() for item in hooks]

    def _build_data_sources(self) -> List[str]:
        return [
            "users(teacher/student)",
            "sessions",
            "llm_logs",
            "learning_plans",
            "twin_profiles",
            "user_states(teacher_ext::<username>)",
        ]

    def _count_advanced_feature_usage(self, logs: List[Dict[str, Any]]) -> int:
        targets = {
            "auto_grading",
            "learning_analytics",
            "ai_assistant",
            "difficulty_explanation",
            "auto_reminder",
        }
        count = 0
        for item in logs:
            meta = item.get("metadata") or {}
            feature = meta.get("feature")
            if isinstance(feature, str) and feature in targets:
                count += 1
        return count

    def _count_ai_recommended_actions(self, logs: List[Dict[str, Any]]) -> int:
        return sum(
            1
            for item in logs
            if (item.get("metadata") or {}).get("ai_recommendation") is True
        )

    def _count_ai_executed_actions(self, logs: List[Dict[str, Any]]) -> int:
        return sum(
            1
            for item in logs
            if (item.get("metadata") or {}).get("ai_executed") is True
        )

    def _count_by_meta_key(self, logs: List[Dict[str, Any]], key: str, allowed: set[str]) -> int:
        count = 0
        for item in logs:
            value = (item.get("metadata") or {}).get(key)
            if isinstance(value, str) and value in allowed:
                count += 1
        return count

    def _calc_non_forced_engagement(self, logs: List[Dict[str, Any]], students: List[str]) -> float:
        if not students:
            return 0.0
        student_set = set(students)
        initiations = 0
        for item in logs:
            metadata = item.get("metadata") or {}
            student_username = metadata.get("student_username")
            if (
                isinstance(student_username, str)
                and student_username in student_set
                and metadata.get("initiated_by_student") is True
            ):
                initiations += 1
        return min(initiations / max(len(students), 1), 1.0)

    def _is_in_days(self, timestamp: Any, threshold: datetime) -> bool:
        dt = self._parse_time(timestamp)
        return bool(dt and dt >= threshold)

    def _parse_time(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _session_minutes(self, session: Dict[str, Any]) -> float:
        start = self._parse_time(session.get("created_at"))
        end = self._parse_time(session.get("last_accessed"))
        if not start or not end:
            return 0.0
        return max((end - start).total_seconds() / 60.0, 0.0)

    def _bounded(self, value: float, upper: float) -> float:
        if value < 0:
            return 0.0
        if value > upper:
            return upper
        return value

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default
