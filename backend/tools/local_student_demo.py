"""Local-only student portrait overlay. Never persist synthetic evidence to MySQL."""
import json
import os
from pathlib import Path


def load_demo(username, course_id=None):
    path = os.getenv("TWIN_DEMO_TREND_FILE", "").strip()
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("username") != username or not data.get("profile"):
        return None
    if course_id and course_id != data.get("course_id"):
        return None
    return data


def build_demo_summary(data):
    from DigitalTwinModule.models import TwinProfile, TrendPoint
    from DigitalTwinModule.student_twin_service import StudentTwinService
    service = StudentTwinService(data["course_id"])
    class DemoHomework:
        def build_student_evidence(self, *_args):
            return data["homework_evidence"]
    service.homework_evidence = DemoHomework()
    result = service.build_summary(TwinProfile.model_validate(data["profile"]),
                                   [TrendPoint(**p) for p in data["points"]], data["course_id"])
    # Demo movements have no measured causes; do not attribute them to real records.
    result["trend"]["attribution_points"] = []
    result["is_demo"] = True
    return result


def build_demo_diagnosis(data):
    from DiagnosisModule.diagnosis_service import StudentDiagnosisService
    service = StudentDiagnosisService()
    actual_store = service.store
    class DemoStore:
        def get_twin_profile(self, _username):
            return data["profile"]
        def __getattr__(self, name):
            return getattr(actual_store, name)
    service.store = DemoStore()
    service._load_profile_nodes = lambda *_args: data["profile"]["knowledge_nodes"]
    service._load_quiz_stats = lambda *_args: data["quiz_stats"]
    service._load_homework_stats = lambda *_args: data["homework_stats"]
    service._load_evidence_timeline = lambda *_args, **_kwargs: data["timeline"]
    result = service.generate_student_diagnosis(data["username"], course_id=data["course_id"], persist=False)
    result["report_id"] = "local_demo_portrait"
    return result
