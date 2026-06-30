from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from TeacherInterventionModule.service import TeacherInterventionService


class CapturingCursor:
    def __init__(self, rows=None) -> None:
        self.executed: list[tuple[str, tuple]] = []
        self.rows = list(rows or [])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        self.executed.append((str(sql), tuple(params)))

    def fetchone(self):
        return {"report_id": "diag_1"}

    def fetchall(self):
        return self.rows


class CapturingConnection:
    def __init__(self, cursor: CapturingCursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


class FakeStore:
    def __init__(self, cursor_rows=None) -> None:
        self.cursor = CapturingCursor(cursor_rows)

    def get_user(self, user_type, username):
        return {"user_id": 1 if user_type == "teacher" else 2, "username": username}

    def connection(self):
        return CapturingConnection(self.cursor)

    def list_course_node_binding_candidates(self, course_id):
        assert course_id == "course_big_data"
        return [
            {
                "node_id": "kafka-basic",
                "node_name": "Kafka basics",
                "node_path": ["Big Data", "Kafka basics"],
                "is_leaf": True,
            }
        ]

    def list_course_resources(self, course_id):
        assert course_id == "course_big_data"
        return [
            {
                "resource_id": 7,
                "course_id": course_id,
                "node_id": "kafka-basic",
                "node_name": "Kafka basics",
                "title": "Kafka 入门视频",
                "resource_path": "https://example.com/kafka",
                "resource_type": "video",
                "review_status": "enabled",
                "is_enabled": True,
                "is_deleted": False,
            },
            {
                "resource_id": 8,
                "course_id": course_id,
                "node_id": "kafka-basic",
                "title": "Rejected",
                "resource_path": "https://example.com/rejected",
                "review_status": "rejected",
                "is_enabled": True,
                "is_deleted": False,
            },
        ]


def test_intervention_package_persists_structured_resource_and_assignment_tasks():
    service = TeacherInterventionService.__new__(TeacherInterventionService)
    service.store = FakeStore()

    package = {
        "id": "pkg_1",
        "teacher_username": "teacher",
        "student_username": "zyh",
        "diagnosis": {"report_id": "diag_1", "course_id": "course_big_data", "risk_level": "medium"},
        "stage": "draft",
        "strategy_summary": "琛ュ厖 Kafka 鍩虹",
        "recommended_concepts": [],
        "recommended_videos": [],
        "resource_tasks": [
            {
                "id": "resource-1",
                "resource_id": 7,
                "title": "Kafka 鍏ラ棬瑙嗛",
                "resource_path": "https://example.com/kafka",
                "resource_type": "video",
                "node_id": "kafka-basic",
                "required": True,
            }
        ],
        "assignment_tasks": [
            {
                "id": "assignment-1",
                "assignment_id": "hw_1",
                "title": "Kafka 缁冧範浣滀笟",
                "course_id": "course_big_data",
                "node_id": "kafka-basic",
                "required": True,
            }
        ],
        "quiz_tasks": [
            {
                "id": "quiz-1",
                "quiz_id": "quiz_kafka_1",
                "title": "Kafka quiz",
                "course_id": "course_big_data",
                "node_id": "kafka-basic",
                "required": True,
            }
        ],
        "code_tasks": [
            {
                "id": "code-1",
                "task_id": "code_kafka_1",
                "title": "Kafka code practice",
                "course_id": "course_big_data",
                "node_id": "kafka-basic",
                "required": True,
            }
        ],
        "questions": [],
        "progress": {"status": "pending", "completion_rate": 0},
        "created_at": "2026-06-28T10:00:00",
        "updated_at": "2026-06-28T10:00:00",
    }

    service._persist_package_to_db(package)

    item_inserts = [
        params
        for sql, params in service.store.cursor.executed
        if "INSERT INTO intervention_package_items" in sql
    ]
    assert len(item_inserts) == 4
    assert item_inserts[0][1] == "course_big_data"
    assert item_inserts[0][2] == "kafka-basic"
    assert item_inserts[0][3] == 7
    assert "resource_task" in item_inserts[0][7]
    assert item_inserts[1][1] == "course_big_data"
    assert item_inserts[1][2] == "kafka-basic"
    assert item_inserts[1][3] == "hw_1"
    assert "assignment_task" in item_inserts[1][7]
    assert "quiz_task" in item_inserts[2][7]
    assert "code_task" in item_inserts[3][7]


def test_intervention_package_does_not_persist_broad_concept_as_node_id():
    service = TeacherInterventionService.__new__(TeacherInterventionService)
    service.store = FakeStore()

    package = {
        "id": "pkg_2",
        "teacher_username": "teacher",
        "student_username": "zyh",
        "diagnosis": {"report_id": "diag_1", "course_id": "course_big_data", "risk_level": "medium"},
        "stage": "draft",
        "strategy_summary": "琛ュ厖 Kafka 鏍稿績鍘熺悊",
        "recommended_concepts": ["Kafka 娑堟伅闃熷垪鏍稿績鍘熺悊"],
        "recommended_videos": [],
        "resource_tasks": [
            {
                "id": "resource-1",
                "title": "Kafka 鍩虹璁茶В",
                "resource_type": "video",
                "node_id": "kafka-basic",
                "required": True,
            }
        ],
        "assignment_tasks": [],
        "questions": [],
        "progress": {"status": "pending", "completion_rate": 0},
        "created_at": "2026-06-28T10:00:00",
        "updated_at": "2026-06-28T10:00:00",
    }

    service._persist_package_to_db(package)

    item_inserts = [
        params
        for sql, params in service.store.cursor.executed
        if "INSERT INTO intervention_package_items" in sql
    ]
    assert len(item_inserts) == 2
    assert item_inserts[0][2] is None
    assert "Kafka 娑堟伅闃熷垪鏍稿績鍘熺悊" in item_inserts[0][4]
    assert item_inserts[1][2] == "kafka-basic"


class _Planner:
    calls = []

    def plan(self, username, *, course_id=None, trigger_type="diagnosis", manual_goal=None):
        self.calls.append(
            {
                "username": username,
                "course_id": course_id,
                "trigger_type": trigger_type,
                "manual_goal": manual_goal,
            }
        )
        return {
            "username": username,
            "course_id": course_id,
            "version_no": 5,
            "trigger_type": trigger_type,
        }


def test_completed_intervention_does_not_generate_student_path(monkeypatch):
    from TeacherInterventionModule import service as intervention_service_module

    _Planner.calls = []
    monkeypatch.setattr(intervention_service_module, "PathPlannerAgent", _Planner)
    service = TeacherInterventionService.__new__(TeacherInterventionService)
    package = {
        "id": "pkg_1",
        "student_username": "zyh",
        "student_status": "completed",
        "diagnosis": {"course_id": "course_big_data"},
        "progress": {"status": "completed"},
    }

    result = service._build_intervention_path_refresh(package)

    assert result["triggered"] is False
    assert result["trigger_type"] == "intervention_completed"
    assert result["path"] is None
    assert _Planner.calls == []


def test_unfinished_intervention_does_not_refresh_path(monkeypatch):
    from TeacherInterventionModule import service as intervention_service_module

    _Planner.calls = []
    monkeypatch.setattr(intervention_service_module, "PathPlannerAgent", _Planner)
    service = TeacherInterventionService.__new__(TeacherInterventionService)

    result = service._build_intervention_path_refresh(
        {
            "id": "pkg_1",
            "student_username": "zyh",
            "student_status": "in_progress",
            "diagnosis": {"course_id": "course_big_data"},
            "progress": {"status": "in_progress"},
        }
    )

    assert result["triggered"] is False
    assert result["path"] is None
    assert _Planner.calls == []


def test_structured_task_completion_contributes_to_progress():
    service = TeacherInterventionService.__new__(TeacherInterventionService)
    package = {
        "id": "pkg_1",
        "student_status": "accepted",
        "resource_tasks": [{"id": "res-1", "title": "Resource", "required": True, "status": "completed"}],
        "assignment_tasks": [{"id": "hw_1", "assignment_id": "hw_1", "title": "Homework", "required": True}],
        "quiz_tasks": [{"id": "quiz_1", "quiz_id": "quiz_1", "title": "Quiz", "required": True, "status": "completed"}],
        "code_tasks": [{"id": "code_1", "task_id": "code_1", "title": "Code", "required": False}],
        "questions": [],
    }

    progress = service._recompute_progress(package, now="2026-06-29T10:00:00")

    assert progress["total_structured_tasks"] == 3
    assert progress["completed_structured_tasks"] == 2
    assert progress["total_items"] == 3
    assert progress["completed_items"] == 2
    assert progress["completion_rate"] == 0.6667
    assert progress["status"] == "in_progress"


class FakeHomeworkRepository:
    def list_assignments(self, **kwargs):
        assert kwargs["status"] == "published"
        assert kwargs["course_id"] == "course_big_data"
        return [
            {
                "id": "hw_1",
                "title": "Kafka 主观作业",
                "course_id": "course_big_data",
                "node_id": "kafka-basic",
                "node_name": "Kafka basics",
                "assignment_type": "subjective",
                "status": "published",
            },
            {
                "id": "code_1",
                "title": "Kafka 代码练习",
                "course_id": "course_big_data",
                "node_id": "kafka-basic",
                "node_name": "Kafka basics",
                "assignment_type": "code",
                "status": "published",
            },
        ]


def test_task_reference_options_include_only_formal_references():
    service = TeacherInterventionService.__new__(TeacherInterventionService)
    service.store = FakeStore(
        [
            {
                "username": "quiz_definitions::course_big_data::kafka-basic",
                "payload_json": {
                    "definitions": [
                        {
                            "definition_id": "draft_quiz",
                            "course_id": "course_big_data",
                            "node_id": "kafka-basic",
                            "title": "草稿测验",
                            "status": "draft",
                            "questions": [{"question": "q", "correct": "a"}],
                        },
                        {
                            "definition_id": "published_quiz",
                            "course_id": "course_big_data",
                            "node_id": "kafka-basic",
                            "title": "Kafka 已发布测验",
                            "status": "published",
                            "questions": [{"question": "q", "correct": "a"}],
                            "published_at": "2026-06-29T10:00:00",
                        },
                    ]
                },
            }
        ]
    )
    service.homework_service = type("HomeworkServiceStub", (), {"repository": FakeHomeworkRepository()})()

    options = service.get_task_reference_options("course_big_data")

    assert [item["resource_id"] for item in options["resources"]] == [7]
    assert {item["assignment_id"] for item in options["assignments"]} == {"hw_1", "code_1"}
    assert [item["task_id"] for item in options["code_tasks"]] == ["code_1"]
    assert [item["quiz_id"] for item in options["quizzes"]] == ["published_quiz"]
    assert options["quizzes"][0]["status"] == "published"
