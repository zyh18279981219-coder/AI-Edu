"""Local teacher showcase input adapter; read-only access to shared MySQL."""
import json
import os
from datetime import datetime
from pathlib import Path

from DigitalTwinModule.teacher_twin_service import TeacherTwinService
from DatabaseModule.store import get_database_store


def get_demo_teacher_service(username):
    path = os.getenv("TEACHER_DEMO_FILE", "").strip()
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if username != data.get("teacher_username"):
        return None
    actual = get_database_store()
    teacher = actual.get_user_by_identifier("teacher", username)
    if not teacher:
        return None
    roster = actual.list_teacher_students(str(teacher.get("user_id") or username))
    class DemoStore:
        def get_user_by_identifier(self, *args):
            return actual.get_user_by_identifier(*args)
        def list_teacher_students(self, *_args):
            return roster
        def get_twin_profile(self, student):
            from tools.local_student_demo import load_demo
            student_demo = load_demo(student)
            return student_demo["profile"] if student_demo else actual.get_twin_profile(student)
        def list_sessions_for_user(self, *_args, **_kwargs):
            return data["sessions"]
        def list_llm_logs_for_user(self, *_args, **_kwargs):
            return data["logs"]
        def list_learning_plans_by_user_identifier(self, *_args, **_kwargs):
            return data["plans"]
    class DemoRepo:
        def records(self, kind, since):
            return [row for row in data[kind] if not since or row["created_at"] >= since]
        def list_interaction_events(self, _username, since=None):
            return self.records("interactions", since)
        def list_research_events(self, _username, since=None):
            return self.records("research", since)
        def list_grading_events(self, _username, since=None):
            return self.records("grading", since)
        def list_intervention_events(self, _username, since=None):
            return self.records("interventions", since)
    class DemoService(TeacherTwinService):
        def build_summary(self, teacher_username):
            result = super().build_summary(teacher_username)
            result["is_demo"] = True
            result["data_diagnosis"]["summary"] = "本地演示场景：由模拟教研、教学互动、批改和干预事件计算，未写入共享数据库。"
            return result
        def build_dimension_drilldown(self, teacher_username, dimension_code, window_days=30):
            result = super().build_dimension_drilldown(teacher_username, dimension_code, window_days)
            result["is_demo"] = True
            return result
    service = DemoService.__new__(DemoService)
    service.store = DemoStore()
    service.teacher_event_repo = DemoRepo()
    service._load_external_metrics = lambda _: data["external"]
    return service
