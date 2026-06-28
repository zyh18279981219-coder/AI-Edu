from datetime import datetime, timedelta

from DigitalTwinModule.teacher_twin_service import TeacherTwinService


class FakeTeacherEventRepository:
    def __init__(self):
        now = datetime.now().isoformat()
        self._interaction_events = [
            {
                "event_type": "assignment_published",
                "created_at": now,
                "response_minutes": None,
                "payload": {"published_on_time": True, "task_mode": "digital", "task_type": "inquiry"},
            },
            {
                "event_type": "announcement_published",
                "created_at": now,
                "response_minutes": None,
                "payload": {"published_on_time": True},
            },
            {
                "event_type": "student_question",
                "created_at": now,
                "response_minutes": None,
                "payload": {},
            },
            {
                "event_type": "teacher_reply",
                "created_at": now,
                "response_minutes": 15,
                "payload": {},
            },
        ]
        self._research_events = [
            {"event_type": "research_post", "created_at": now, "payload": {}},
            {"event_type": "shared_courseware", "created_at": now, "payload": {}},
            {"event_type": "co_preparation", "created_at": now, "payload": {}},
        ]
        self._grading_events = [
            {
                "event_type": "ai_recommendation_generated",
                "created_at": now,
                "grading_minutes": 8,
                "payload": {"assessment_type": "subjective", "feedback_text": "建议补充案例分析"},
            },
            {
                "event_type": "teacher_final_grade",
                "created_at": now,
                "grading_minutes": 12,
                "payload": {"assessment_type": "subjective", "feedback_text": "教师终审反馈"},
            },
            {
                "event_type": "remediation_material",
                "created_at": now,
                "grading_minutes": None,
                "payload": {"feedback_text": "请完成补救练习"},
            },
        ]
        self._intervention_events = [
            {
                "event_type": "package_pushed",
                "created_at": now,
                "student_username": "stu001",
                "payload": {},
            },
            {
                "event_type": "package_accepted",
                "created_at": now,
                "student_username": "stu001",
                "payload": {},
            },
            {
                "event_type": "teacher_reviewed",
                "created_at": now,
                "student_username": "stu001",
                "payload": {},
            },
            {
                "event_type": "package_completed",
                "created_at": now,
                "student_username": "stu001",
                "payload": {},
            },
        ]

    def list_interaction_events(self, teacher_username, since=None):
        del teacher_username, since
        return list(self._interaction_events)

    def list_research_events(self, teacher_username, since=None):
        del teacher_username, since
        return list(self._research_events)

    def list_grading_events(self, teacher_username, since=None):
        del teacher_username, since
        return list(self._grading_events)

    def list_intervention_events(self, teacher_username, since=None):
        del teacher_username, since
        return list(self._intervention_events)


class FakeStore:
    def __init__(self):
        now = datetime.now()
        self._teacher = {
            "user_id": 101,
            "username": "tea001",
            "name": "Teacher A",
            "students": ["stu001", "stu002"],
        }
        self._students = [
            {"username": "stu001", "teacher": "tea001"},
            {"username": "stu002", "teacher": "tea001"},
        ]
        self._sessions = [
            {
                "username": "tea001",
                "user_type": "teacher",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "last_accessed": now.isoformat(),
            },
            {
                "username": "tea001",
                "user_type": "teacher",
                "created_at": (now - timedelta(days=1, hours=1)).isoformat(),
                "last_accessed": (now - timedelta(days=1)).isoformat(),
            },
        ]
        self._logs = [
            {
                "username": "tea001",
                "timestamp": now.isoformat(),
                "metadata": {"feature": "auto_grading", "ai_recommendation": True, "ai_executed": True},
            },
            {
                "username": "tea001",
                "timestamp": now.isoformat(),
                "metadata": {"assessment_type": "objective", "feedback_text": "feedback text", "grading_minutes": 10},
            },
        ]
        self._plans = [
            {
                "filename": "lesson1.pdf",
                "data": {"revision_count": 2},
            },
            {
                "filename": "lesson2.mp4",
                "data": {"revision_count": 1},
            },
        ]
        self._twins = {
            "stu001": {"overall_mastery": 58},
            "stu002": {"overall_mastery": 81},
        }
        self._user_states = {
            "teacher_ext::tea001": {
                "research_posts": 2,
                "shared_courseware": 1,
                "co_preparation_count": 1,
                "personalized_push_count": 2,
                "risk_intervention_count": 1,
                "digital_tasks": 3,
                "total_tasks": 4,
                "total_teaching_hours": 10,
                "inquiry_learning_hours": 2,
                "collaborative_tasks": 1,
                "on_time_release_ratio": 0.8,
                "teacher_reply_rate": 0.75,
            }
        }

    def get_user(self, user_type, username):
        if user_type == "teacher" and username == "tea001":
            return self._teacher
        return None

    def get_user_by_identifier(self, user_type, identifier):
        if user_type == "teacher" and identifier in {"tea001", "101"}:
            return self._teacher
        return None

    def list_teacher_students(self, teacher_identifier):
        if str(teacher_identifier) not in {"101", "tea001"}:
            return []
        return [
            {"student_username": "stu001"},
            {"student_username": "stu002"},
        ]

    def list_users(self, user_type):
        if user_type == "student":
            return self._students
        return []

    def get_twin_profile(self, username):
        return self._twins.get(username)

    def list_sessions(self):
        return self._sessions

    def list_sessions_for_user(self, user_type, user_identifier, limit=None):
        del user_type, user_identifier, limit
        return self._sessions

    def list_llm_logs(self, limit=None):
        del limit
        return self._logs

    def list_llm_logs_for_user(self, user_identifier, user_type=None, limit=None):
        del user_identifier, user_type, limit
        return self._logs

    def list_learning_plans(self, username=None, categories=None):
        del username, categories
        return self._plans

    def list_learning_plans_by_user_identifier(self, user_identifier, user_type=None, categories=None):
        del user_identifier, user_type, categories
        return self._plans

    def get_user_state(self, key):
        return self._user_states.get(key)


def test_teacher_twin_six_dimensions():
    service = TeacherTwinService()
    service.store = FakeStore()
    service.teacher_event_repo = FakeTeacherEventRepository()

    result = service.build_summary("tea001")

    assert result["teacher_username"] == "tea001"
    assert len(result["dimensions"]) == 6
    assert len(result["radar"]) == 6
    assert result["overall_score"] >= 0
    assert result["student_scope"]["student_count"] == 2
    assert "missing_data_hooks" in result
    assert result["suggestion_generation"]["mode"] == "manual-ai-button"
    assert result["teaching_strategy_suggestions"] == []
    assert "teaching_interaction_events" in result["data_sources"]


def test_teacher_twin_prefers_internal_events_over_external_fallback():
    service = TeacherTwinService()
    fake_store = FakeStore()
    fake_store._user_states["teacher_ext::tea001"] = {}
    service.store = fake_store
    service.teacher_event_repo = FakeTeacherEventRepository()

    result = service.build_summary("tea001")
    dims = {item["code"]: item for item in result["dimensions"]}

    assert dims["professional_engagement"]["sub_items"]["teaching_research_collaboration"]["posts"] == 1
    assert dims["teaching_learning"]["sub_items"]["online_interaction_frequency"]["teacher_reply_rate"] == 1.0
    assert dims["assessment"]["sub_items"]["data_driven_adjustment"]["remediation_actions"] >= 1
    assert dims["empowering_learners"]["sub_items"]["personalized_path_dispatch_rate"]["personalized_push_count"] == 1
