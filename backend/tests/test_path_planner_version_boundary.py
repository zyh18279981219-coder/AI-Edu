from __future__ import annotations

import os
import sys
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DigitalTwinModule.models import Resource, TwinProfile, WeakNode
from PathPlannerModule.path_planner_agent import PathPlannerAgent


@dataclass
class _Detector:
    nodes: list[WeakNode]

    def detect(self, _profile):
        return self.nodes


class _Store:
    def __init__(self):
        self.saved_payload = None

    def list_learning_path_versions(self, **_kwargs):
        return []

    def save_learning_path_version(self, **kwargs):
        self.saved_payload = kwargs["payload"]
        self.saved_payload["path_id"] = 1
        self.saved_payload["version_no"] = 1
        return {"path_id": 1, "version_no": 1}

    def get_course_summary(self, course_id):
        return {
            "course_id": course_id,
            "lifecycle_status": "published",
        }

    def list_learning_nodes_for_course(self, course_id):
        assert course_id == "course_big_data"
        return ["Kafka 数据接入"]


class _ProfileStore:
    def load(self, username):
        return TwinProfile(username=username, last_updated="2026-06-28T00:00:00", knowledge_nodes=[])


class _Diagnosis:
    def generate_student_diagnosis(self, username, course_id=None, persist=True):
        assert username == "zyh"
        assert course_id == "course_big_data"
        assert persist is True
        return {
            "report_id": "diag-001",
            "course_id": course_id,
            "evidence_level": "sufficient",
            "confidence": 0.82,
            "weak_nodes": [
                {
                    "node_id": "Kafka 数据接入",
                    "mastery_score": 45,
                    "evidence_level": "sufficient",
                    "suggested_actions": ["复习消息队列基础"],
                },
                {
                    "node_id": "图谱外薄弱点",
                    "mastery_score": 52,
                    "evidence_level": "sufficient",
                },
                {
                    "node_id": "证据不足节点",
                    "mastery_score": 30,
                    "evidence_level": "insufficient",
                    "suggested_actions": ["补一次小测"],
                },
            ],
        }


class _Recommender:
    def __init__(self):
        self.calls = []

    def recommend(self, node_id, node_name="", course_id=None):
        self.calls.append((node_id, node_name, course_id))
        return [
            Resource(
                type="document",
                title=f"{node_id} 资料",
                url=f"https://example.com/{node_id}",
                source="test",
                reason="测试推荐理由",
            )
        ]


def test_path_payload_splits_formal_nodes_and_supplemental_items():
    agent = PathPlannerAgent.__new__(PathPlannerAgent)
    agent.database_store = _Store()
    agent.store = _ProfileStore()
    agent.detector = _Detector([])
    agent.recommender = _Recommender()
    agent.diagnosis_service = _Diagnosis()
    agent._llm = None
    agent._llm_enabled = lambda: False

    payload = agent.plan(
        "zyh",
        course_id="course_big_data",
        trigger_type="manual_goal",
        manual_goal="考试冲刺",
    )

    assert payload["course_id"] == "course_big_data"
    assert payload["version_no"] == 1
    assert payload["trigger_type"] == "manual_goal"
    assert payload["manual_goal"] == "考试冲刺"
    assert payload["basis_report_id"] == "diag-001"
    assert payload["basis"]["insufficient_node_count"] == 1
    assert payload["basis"]["insufficient_nodes"][0]["node_id"] == "证据不足节点"

    assert [item["node_id"] for item in payload["formal_path_nodes"]] == ["Kafka 数据接入"]
    assert payload["formal_path_nodes"][0]["mapping_status"] == "confirmed_course_node"

    supplemental_by_source = {item["source"]: item for item in payload["supplemental_items"]}
    assert supplemental_by_source["resource_recommendation"]["item_type"] == "supplemental_item"
    assert supplemental_by_source["resource_recommendation"]["resource"]["url"].startswith("https://example.com/")
    assert supplemental_by_source["resource_recommendation"]["reason"] == "测试推荐理由"
    assert supplemental_by_source["diagnosis_weak_node_outside_published_graph"]["node_id"] == "图谱外薄弱点"
    assert supplemental_by_source["diagnosis_weak_node_outside_published_graph"]["item_type"] == "supplemental_learning_item"
    assert supplemental_by_source["diagnosis_weak_node_outside_published_graph"]["mapping_status"] == "outside_published_course_graph"

    all_path_node_ids = [item["node_id"] for item in payload["formal_path_nodes"]] + [
        item["node_id"] for item in payload["supplemental_items"]
    ]
    assert "证据不足节点" not in all_path_node_ids
    assert all(call[2] == "course_big_data" for call in agent.recommender.calls)
    assert agent.database_store.saved_payload == payload


def test_intervention_completion_trigger_reason_is_student_side_path_refresh():
    agent = PathPlannerAgent.__new__(PathPlannerAgent)

    reason = agent._trigger_reason(
        "intervention_completed",
        "Completed teacher intervention package: pkg-1",
        diagnosis={"report_id": "diag-001"},
    )

    assert "教师干预任务完成后" in reason
    assert "学生端刷新" in reason
