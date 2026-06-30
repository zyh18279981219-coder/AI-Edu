from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DigitalTwinModule.models import KnowledgeNodeScore
from DigitalTwinModule.models import TwinProfile
from DigitalTwinModule.student_twin_service import StudentTwinService


class StoreStub:
    def __init__(self, mappings, lifecycle_status="published"):
        self.mappings = mappings
        self.requested_course_id = None
        self.lifecycle_status = lifecycle_status

    def get_course_summary(self, course_id: str):
        return {
            "course_id": course_id,
            "course_name": "Test Course",
            "lifecycle_status": self.lifecycle_status,
        }

    def list_course_ability_mappings(self, course_id: str):
        self.requested_course_id = course_id
        return self.mappings


def _node(node_id: str, mastery: float) -> KnowledgeNodeScore:
    return KnowledgeNodeScore(
        node_id=node_id,
        node_path=["课程", node_id],
        quiz_score=mastery,
        progress=80,
        study_duration_minutes=30,
        llm_interaction_count=3,
        mastery_score=mastery,
    )


def _service(mappings, lifecycle_status="published") -> StudentTwinService:
    service = StudentTwinService.__new__(StudentTwinService)
    service.store = StoreStub(mappings, lifecycle_status=lifecycle_status)
    service.course_tree = type("CourseTreeStub", (), {"course_id": "course_big_data"})()
    service.homework_evidence = type(
        "HomeworkEvidenceStub",
        (),
        {"build_student_evidence": lambda self, username, course_id: {}},
    )()
    return service


def test_career_ability_attainment_uses_only_confirmed_mappings():
    service = _service(
        [
            {
                "mapping_id": 1,
                "ability_id": 101,
                "ability_name": "数据采集能力",
                "position_id": 9,
                "position_name": "大数据工程师",
                "node_id": "kafka-basic",
                "node_name": "Kafka 数据接入",
                "support_level": "high",
                "review_status": "confirmed",
            },
            {
                "mapping_id": 2,
                "ability_id": 101,
                "ability_name": "数据采集能力",
                "node_id": "flink-window",
                "node_name": "Flink 窗口计算",
                "support_level": "high",
                "review_status": "draft",
            },
        ]
    )

    result = service._build_career_ability_attainment(
        "zyh",
        "course_big_data",
        [_node("kafka-basic", 82), _node("flink-window", 20)],
    )

    assert service.store.requested_course_id == "course_big_data"
    assert len(result) == 1
    assert result[0]["attainment_score"] == 82
    assert result[0]["level"] == "较好达成"
    assert result[0]["gap_nodes"] == []
    assert [node["node_id"] for node in result[0]["supporting_nodes"]] == ["kafka-basic"]


def test_career_ability_attainment_weights_support_levels_and_reports_gaps():
    service = _service(
        [
            {
                "mapping_id": 1,
                "ability_id": 201,
                "ability_name": "实时计算能力",
                "node_id": "stream-basic",
                "node_name": "流式计算基础",
                "support_level": "high",
                "review_status": "confirmed",
            },
            {
                "mapping_id": 2,
                "ability_id": 201,
                "ability_name": "实时计算能力",
                "node_id": "window-join",
                "node_name": "窗口关联分析",
                "support_level": "medium",
                "review_status": "confirmed",
            },
            {
                "mapping_id": 3,
                "ability_id": 201,
                "ability_name": "实时计算能力",
                "node_id": "checkpoint",
                "node_name": "状态一致性",
                "support_level": "low",
                "review_status": "confirmed",
            },
        ]
    )

    result = service._build_career_ability_attainment(
        "zyh",
        "course_big_data",
        [_node("stream-basic", 90), _node("window-join", 50)],
    )

    assert len(result) == 1
    item = result[0]
    assert item["attainment_score"] == 63.16
    assert item["level"] == "基本达成"
    assert [node["node_id"] for node in item["gap_nodes"]] == ["checkpoint", "window-join"]
    weights = {node["node_id"]: node["support_weight"] for node in item["supporting_nodes"]}
    assert weights == {"stream-basic": 1.0, "window-join": 0.6, "checkpoint": 0.3}


def test_career_ability_attainment_skips_unpublished_course_even_with_confirmed_mappings():
    service = _service(
        [
            {
                "mapping_id": 1,
                "ability_id": 301,
                "ability_name": "草稿课程能力",
                "node_id": "draft-node",
                "node_name": "草稿节点",
                "support_level": "high",
                "review_status": "confirmed",
            },
        ],
        lifecycle_status="draft",
    )

    result = service._build_career_ability_attainment(
        "zyh",
        "draft_course",
        [_node("draft-node", 95)],
    )

    assert result == []
    assert service.store.requested_course_id is None


def test_student_summary_hides_ability_mapping_weights_and_supporting_evidence():
    service = _service(
        [
            {
                "mapping_id": 1,
                "ability_id": 401,
                "ability_name": "数据采集能力",
                "position_id": 9,
                "position_name": "大数据工程师",
                "node_id": "flume-basic",
                "node_name": "Flume 基础",
                "support_level": "high",
                "support_weight": 1.0,
                "review_status": "confirmed",
            },
            {
                "mapping_id": 2,
                "ability_id": 401,
                "ability_name": "数据采集能力",
                "position_id": 9,
                "position_name": "大数据工程师",
                "node_id": "kafka-basic",
                "node_name": "Kafka 基础",
                "support_level": "medium",
                "support_weight": 0.6,
                "review_status": "confirmed",
            },
        ]
    )
    profile = TwinProfile(
        username="zyh",
        last_updated="2026-06-28T10:00:00",
        overall_mastery=65,
        knowledge_nodes=[_node("flume-basic", 82), _node("kafka-basic", 45)],
    )

    summary = service.build_summary(profile, trend=[], course_id="course_big_data")

    student_item = summary["career_abilities"][0]
    assert "supporting_nodes" not in student_item
    assert "calculation_note" not in student_item
    assert "support_weight" not in student_item["gap_nodes"][0]
    assert student_item["gap_nodes"][0]["node_id"] == "kafka-basic"

    teacher_item = summary["outputs"]["for_teacher_twin"]["career_abilities"][0]
    assert "supporting_nodes" in teacher_item
    assert teacher_item["supporting_nodes"][0]["support_weight"] == 1.0
