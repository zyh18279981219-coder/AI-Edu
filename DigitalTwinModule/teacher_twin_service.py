from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Dict, List, Optional

from DigitalTwinModule.teacher_event_repository import get_teacher_event_repository
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
        self.teacher_event_repo = get_teacher_event_repository()

    def build_summary(self, teacher_username: str) -> Dict[str, Any]:
        now = datetime.now()
        teacher = self.store.get_user_by_identifier("teacher", teacher_username)
        if not teacher:
            raise ValueError(f"Teacher '{teacher_username}' not found")
        canonical_teacher_username = str(teacher.get("username") or teacher_username)
        canonical_teacher_identifier = str(teacher.get("user_id") or canonical_teacher_username)

        students = self._resolve_teacher_students(teacher)
        student_twins = [
            self.store.get_twin_profile(student_username)
            for student_username in students
        ]
        student_twins = [item for item in student_twins if item]

        sessions = self.store.list_sessions_for_user("teacher", canonical_teacher_identifier, limit=4000)
        logs = self.store.list_llm_logs_for_user(canonical_teacher_identifier, user_type="teacher", limit=4000)
        plans = self.store.list_learning_plans_by_user_identifier(canonical_teacher_identifier, user_type="teacher")
        recent_since = (now - timedelta(days=180)).isoformat()
        interaction_events = self.teacher_event_repo.list_interaction_events(canonical_teacher_username, since=recent_since)
        research_events = self.teacher_event_repo.list_research_events(canonical_teacher_username, since=recent_since)
        grading_events = self.teacher_event_repo.list_grading_events(canonical_teacher_username, since=recent_since)
        intervention_events = self.teacher_event_repo.list_intervention_events(canonical_teacher_username, since=recent_since)

        external = self._load_external_metrics(canonical_teacher_username)

        dim1 = self._dimension_professional_engagement(now, sessions, logs, external, research_events)
        dim2 = self._dimension_digital_resources(now, plans, external, research_events)
        dim3 = self._dimension_teaching_learning(now, logs, plans, sessions, external, interaction_events, grading_events, intervention_events)
        dim4 = self._dimension_assessment(now, logs, external, grading_events, interaction_events)
        dim5 = self._dimension_empowering_learners(now, students, student_twins, logs, external, intervention_events)
        dim6 = self._dimension_facilitating_digital_competence(now, plans, logs, external, interaction_events)

        dimensions = [dim1, dim2, dim3, dim4, dim5, dim6]
        overall = round(mean([item["score"] for item in dimensions]), 2)
        radar = [{"name": item["name"], "value": item["score"]} for item in dimensions]

        return {
            "teacher_username": canonical_teacher_username,
            "teacher_name": teacher.get("name", canonical_teacher_username),
            "last_updated": now.isoformat(),
            "overall_score": overall,
            "radar": radar,
            "dimensions": dimensions,
            "teaching_strategy_suggestions": [],
            "intervention_suggestions": [],
            "student_scope": {
                "student_count": len(students),
                "students_with_twin": len(student_twins),
                "students": students,
            },
            "suggestion_generation": {
                "mode": "manual-ai-button",
                "is_ai_generated": False,
                "note": "点击按钮后才调用 AI 生成建议；默认不生成，节省资源。",
            },
            "data_diagnosis": self._build_data_diagnosis(external),
            "missing_data_hooks": self._build_missing_data_hooks(),
            "data_sources": self._build_data_sources(),
        }

    def build_dimension_drilldown(
        self,
        teacher_username: str,
        dimension_code: str,
        window_days: int = 30,
    ) -> Dict[str, Any]:
        summary = self.build_summary(teacher_username)
        dimension = next((item for item in summary["dimensions"] if item["code"] == dimension_code), None)
        if not dimension:
            raise ValueError(f"Unknown dimension '{dimension_code}'")

        now = datetime.now()
        since = (now - timedelta(days=window_days)).isoformat()
        interaction_events = self.teacher_event_repo.list_interaction_events(summary["teacher_username"], since=since)
        research_events = self.teacher_event_repo.list_research_events(summary["teacher_username"], since=since)
        grading_events = self.teacher_event_repo.list_grading_events(summary["teacher_username"], since=since)
        intervention_events = self.teacher_event_repo.list_intervention_events(summary["teacher_username"], since=since)

        evidence_map = {
            "professional_engagement": research_events,
            "digital_resources": research_events,
            "teaching_learning": interaction_events + grading_events + intervention_events,
            "assessment": grading_events + interaction_events,
            "empowering_learners": intervention_events,
            "facilitating_digital_competence": interaction_events,
        }
        source_events = evidence_map.get(dimension_code, [])
        evidence_items = [
            {
                "event_type": str(item.get("event_type") or ""),
                "created_at": str(item.get("created_at") or ""),
                "student_username": item.get("student_username"),
                "target_id": item.get("target_id") or item.get("assignment_id") or item.get("package_id"),
                "summary": self._format_event_summary(item),
                "payload": item.get("payload") or {},
            }
            for item in sorted(source_events, key=lambda x: str(x.get("created_at") or ""), reverse=True)[:50]
        ]
        coverage_ratio = 1.0 if evidence_items else summary["data_diagnosis"]["external_coverage_ratio"]
        return {
            "teacher_username": summary["teacher_username"],
            "dimension": {
                "code": dimension["code"],
                "name": dimension["name"],
                "score": dimension["score"],
                "sub_items": dimension["sub_items"],
            },
            "window_days": window_days,
            "coverage_ratio": round(float(coverage_ratio), 4),
            "evidence_count": len(evidence_items),
            "evidence_items": evidence_items,
        }

    def _resolve_teacher_students(self, teacher: Dict[str, Any]) -> List[str]:
        teacher_identifier = str(teacher.get("user_id") or "")
        try:
            links = self.store.list_teacher_students(teacher_identifier)
            linked_usernames = [
                str(item.get("student_username") or "")
                for item in links
                if item.get("student_username")
            ]
            if linked_usernames:
                return sorted(set(linked_usernames))
        except Exception:
            pass

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
        research_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        last_7 = now - timedelta(days=7)
        active_sessions = [s for s in sessions if self._parse_time(s.get("last_accessed")) and self._parse_time(s.get("last_accessed")) >= last_7]
        weekly_hours = round(sum(self._session_minutes(item) for item in active_sessions) / 60.0, 2)
        login_frequency = len(active_sessions)

        recent_research = self._filter_events_since(research_events, now - timedelta(days=90))
        collab_posts = self._prefer_internal_metric(
            self._count_events(recent_research, {"research_post", "teaching_research_post"}),
            external.get("research_posts"),
        )
        shared_courseware = self._prefer_internal_metric(
            self._count_events(recent_research, {"shared_courseware", "resource_shared"}),
            external.get("shared_courseware"),
        )
        co_preparation = self._prefer_internal_metric(
            self._count_events(recent_research, {"co_preparation", "collective_preparation"}),
            external.get("co_preparation_count"),
        )

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
        research_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        del now
        formats = set()
        iterations = 0
        shared_reuse = self._prefer_internal_metric(
            self._count_events(research_events, {"shared_courseware", "resource_shared"}),
            external.get("resource_referenced_by_others"),
        )

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
        interaction_events: List[Dict[str, Any]],
        grading_events: List[Dict[str, Any]],
        intervention_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        del plans
        last_30 = now - timedelta(days=30)
        recent_logs = [item for item in logs if self._is_in_days(item.get("timestamp"), last_30)]
        recent_interactions = self._filter_events_since(interaction_events, last_30)
        recent_gradings = self._filter_events_since(grading_events, last_30)
        recent_interventions = self._filter_events_since(intervention_events, last_30)

        internal_announcements = self._count_events(recent_interactions, {"announcement_published", "publish_announcement", "assignment_published"})
        internal_discussions = self._count_events(recent_interactions, {"discussion_topic", "start_discussion", "student_question"})
        announcements = internal_announcements or self._count_by_meta_key(recent_logs, "action", {"announcement", "publish_announcement"})
        discussion_topics = internal_discussions or self._count_by_meta_key(recent_logs, "action", {"discussion_topic", "start_discussion"})
        teacher_reply_count = self._count_events(recent_interactions, {"teacher_reply"})
        student_question_count = self._count_events(recent_interactions, {"student_question"})
        if student_question_count > 0:
            teacher_reply_rate = min(teacher_reply_count / student_question_count, 1.0)
        else:
            teacher_reply_rate = self._safe_float(external.get("teacher_reply_rate"))
        response_values = [
            self._safe_float(item.get("response_minutes"))
            for item in recent_interactions
            if item.get("response_minutes") is not None
        ]
        avg_response_minutes = (
            round(mean(response_values), 2)
            if response_values
            else self._safe_float(external.get("avg_response_minutes"), default=120.0)
        )

        publish_events = self._filter_by_event_type(recent_interactions, {"assignment_published", "announcement_published", "publish_announcement"})
        publish_timely_flags = [
            1.0 if (item.get("payload") or {}).get("published_on_time", True) else 0.0
            for item in publish_events
        ]
        on_time_release_ratio = (
            round(sum(publish_timely_flags) / len(publish_timely_flags), 4)
            if publish_timely_flags
            else self._safe_float(external.get("on_time_release_ratio"), default=0.7)
        )
        ai_recommended_actions = self._count_ai_recommended_actions(recent_logs) + self._count_events(
            recent_gradings, {"ai_recommendation_generated"}
        ) + self._count_events(recent_interventions, {"draft_generated"})
        ai_executed_actions = self._count_ai_executed_actions(recent_logs) + self._count_events(
            recent_gradings, {"teacher_final_grade", "auto_code_grade_completed", "auto_objective_grade_completed"}
        ) + self._count_events(recent_interventions, {"package_pushed", "teacher_reviewed"})
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
        grading_events: List[Dict[str, Any]],
        interaction_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        last_30 = now - timedelta(days=30)
        recent_logs = [item for item in logs if self._is_in_days(item.get("timestamp"), last_30)]
        recent_grading_events = self._filter_events_since(grading_events, last_30)
        recent_interactions = self._filter_events_since(interaction_events, last_30)

        assessment_types = set()
        subjective_feedback_count = 0
        subjective_feedback_length = []
        grading_minutes = []
        remediation_count = 0

        for event in recent_grading_events:
            payload = event.get("payload") or {}
            assess_type = payload.get("assessment_type") or payload.get("assignment_type")
            if isinstance(assess_type, str) and assess_type:
                assessment_types.add(assess_type)
            feedback_text = payload.get("feedback_text") or payload.get("teacher_comment")
            if feedback_text:
                text = str(feedback_text)
                subjective_feedback_count += 1
                subjective_feedback_length.append(len(text))
            if event.get("grading_minutes") is not None:
                grading_minutes.append(self._safe_float(event.get("grading_minutes")))
            if str(event.get("event_type") or "") in {"remediation_material", "remediation_announcement"}:
                remediation_count += 1

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
        remediation_count += self._count_events(recent_interactions, {"remediation_material", "remediation_announcement"})

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
        intervention_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        del now
        pushed_events = self._filter_by_event_type(intervention_events, {"package_pushed"})
        personalized_push = self._prefer_internal_metric(len(pushed_events), external.get("personalized_push_count"))
        risk_interventions = self._prefer_internal_metric(
            len(self._filter_by_event_type(intervention_events, {"package_pushed", "teacher_reviewed", "package_completed"})),
            external.get("risk_intervention_count"),
        )

        low_mastery_students = sum(1 for twin in student_twins if self._safe_float(twin.get("overall_mastery")) < 60)
        intervention_ratio = 0.0
        targeted_students = {
            str(item.get("student_username") or "").strip()
            for item in pushed_events
            if str(item.get("student_username") or "").strip()
        }
        if low_mastery_students > 0:
            intervention_ratio = min(len(targeted_students) / low_mastery_students, 1.0)

        accepted_or_completed = self._count_events(intervention_events, {"package_accepted", "package_completed"})
        if personalized_push > 0:
            non_forced_engagement = min(accepted_or_completed / personalized_push, 1.0)
        else:
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
        interaction_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        last_90 = now - timedelta(days=90)
        recent_logs = [item for item in logs if self._is_in_days(item.get("timestamp"), last_90)]
        recent_interactions = self._filter_events_since(interaction_events, last_90)
        assignment_events = self._filter_by_event_type(recent_interactions, {"assignment_created", "assignment_published"})
        internal_total_tasks = len(assignment_events)

        total_tasks = self._prefer_internal_metric(internal_total_tasks, external.get("total_tasks"), default=max(len(plans), 1))
        digital_tasks = self._safe_float(external.get("digital_tasks"), default=0.0)
        collaborative_tasks = self._safe_float(external.get("collaborative_tasks"), default=0.0)
        inquiry_hours = self._safe_float(external.get("inquiry_learning_hours"), default=0.0)
        total_hours = self._safe_float(external.get("total_teaching_hours"), default=1.0)

        internal_digital_tasks = sum(1 for item in assignment_events if self._is_digital_task_event(item))
        internal_collaborative_tasks = sum(1 for item in assignment_events if self._is_collaborative_task_event(item))
        internal_inquiry_tasks = sum(1 for item in assignment_events if self._is_inquiry_task_event(item))

        if internal_digital_tasks > 0:
            digital_tasks = float(internal_digital_tasks)
        elif digital_tasks <= 0:
            digital_tasks = self._count_by_meta_key(recent_logs, "task_mode", {"digital", "video", "coding", "mindmap"})
        if internal_collaborative_tasks > 0:
            collaborative_tasks = float(internal_collaborative_tasks)
        elif collaborative_tasks <= 0:
            collaborative_tasks = self._count_by_meta_key(recent_logs, "task_group_mode", {"group", "collaboration"})
        if internal_inquiry_tasks > 0:
            inquiry_hours = float(internal_inquiry_tasks)
        elif inquiry_hours <= 0:
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
                source="teaching_research_events + teacher_ext::<username>",
                status="active",
                note="优先读取内部教研事件；外部灌数仅作兜底",
            ),
            MetricSource(
                field="feedback_timeliness_and_depth",
                source="homework_grading_events + teacher_ext::<username>",
                status="active",
                note="优先读取作业批改回流事件；外部灌数仅作兜底",
            ),
            MetricSource(
                field="empowering_learners",
                source="teacher_intervention_events + teacher_ext::<username>",
                status="active",
                note="优先读取内部干预任务包回流；外部灌数仅作兜底",
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
            "teaching_interaction_events",
            "teaching_research_events",
            "homework_grading_events",
            "teacher_intervention_events",
            "user_states(teacher_ext::<username>)",
        ]

    def _build_data_diagnosis(self, external: Dict[str, Any]) -> Dict[str, Any]:
        required_external_fields = [
            "research_posts",
            "shared_courseware",
            "co_preparation_count",
            "subjective_grading_minutes",
            "personalized_push_count",
            "risk_intervention_count",
            "total_tasks",
            "digital_tasks",
            "collaborative_tasks",
            "inquiry_learning_hours",
            "total_teaching_hours",
            "teacher_reply_rate",
            "avg_response_minutes",
            "on_time_release_ratio",
            "resource_referenced_by_others",
        ]
        present = [field for field in required_external_fields if external.get(field) is not None]
        missing = [field for field in required_external_fields if external.get(field) is None]
        ratio = round((len(present) / len(required_external_fields)) if required_external_fields else 1.0, 4)

        if ratio >= 0.8:
            summary = "外部指标覆盖较高，雷达分数参考性较强。"
        elif ratio >= 0.4:
            summary = "外部指标覆盖一般，部分维度分数可能偏保守。"
        else:
            summary = "外部指标覆盖较低，当前雷达分数主要基于基础日志，可能偏低。"

        return {
            "external_metrics_present": present,
            "external_metrics_missing": missing,
            "external_coverage_ratio": ratio,
            "summary": summary + " 当前系统已支持内部结构化事件优先计分。",
        }

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

    def _filter_events_since(self, events: List[Dict[str, Any]], threshold: datetime) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for item in events:
            if self._is_in_days(item.get("created_at"), threshold):
                result.append(item)
        return result

    def _filter_by_event_type(self, events: List[Dict[str, Any]], allowed: set[str]) -> List[Dict[str, Any]]:
        return [
            item
            for item in events
            if str(item.get("event_type") or "").strip() in allowed
        ]

    def _count_events(self, events: List[Dict[str, Any]], allowed: set[str]) -> int:
        return len(self._filter_by_event_type(events, allowed))

    def _prefer_internal_metric(self, internal_value: Any, external_value: Any, default: float = 0.0) -> float:
        internal = self._safe_float(internal_value, default=default)
        if internal > 0:
            return internal
        return self._safe_float(external_value, default=default)

    def _is_digital_task_event(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload") or {}
        task_mode = str(payload.get("task_mode") or "").strip().lower()
        assignment_type = str(payload.get("assignment_type") or "").strip().lower()
        if task_mode in {"digital", "video", "coding", "mindmap", "online"}:
            return True
        return assignment_type in {"code", "objective", "choice", "subjective"}

    def _is_collaborative_task_event(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload") or {}
        group_mode = str(payload.get("task_group_mode") or "").strip().lower()
        class_name = str(payload.get("class_name") or "").strip()
        return group_mode in {"group", "collaboration", "team"} or ("小组" in class_name)

    def _is_inquiry_task_event(self, event: Dict[str, Any]) -> bool:
        payload = event.get("payload") or {}
        task_type = str(payload.get("task_type") or "").strip().lower()
        node_name = str(payload.get("node_name") or "").strip()
        return task_type in {"inquiry", "open_question", "project"} or ("探究" in node_name)

    def _format_event_summary(self, event: Dict[str, Any]) -> str:
        event_type = str(event.get("event_type") or "")
        payload = event.get("payload") or {}
        title = str(payload.get("title") or payload.get("assignment_title") or "")
        feedback = str(payload.get("feedback_text") or payload.get("teacher_comment") or "")
        if title:
            return f"{event_type}: {title}"
        if feedback:
            return f"{event_type}: {feedback[:60]}"
        return event_type

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
