from datetime import datetime, timedelta

from DigitalTwinModule.teacher_twin_service import TeacherTwinService


class FakeStore:
    def __init__(self):
        now = datetime.now()
        self._teacher = {
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

    def list_users(self, user_type):
        if user_type == "student":
            return self._students
        return []

    def get_twin_profile(self, username):
        return self._twins.get(username)

    def list_sessions(self):
        return self._sessions

    def list_llm_logs(self, limit=None):
        del limit
        return self._logs

    def list_learning_plans(self, username=None, categories=None):
        del username, categories
        return self._plans

    def get_user_state(self, key):
        return self._user_states.get(key)


def test_teacher_twin_six_dimensions():
    service = TeacherTwinService()
    service.store = FakeStore()

    result = service.build_summary("tea001")

    assert result["teacher_username"] == "tea001"
    assert len(result["dimensions"]) == 6
    assert len(result["radar"]) == 6
    assert result["overall_score"] >= 0
    assert result["student_scope"]["student_count"] == 2
    assert "missing_data_hooks" in result
    assert result["suggestion_generation"]["mode"] == "manual-ai-button"
    assert result["teaching_strategy_suggestions"] == []
