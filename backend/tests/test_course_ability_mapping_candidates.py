from __future__ import annotations

import os
import sys
from types import MethodType

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from DatabaseModule.mysql_store import MySQLStore


def _store_stub(*, existing=None, abilities=None):
    store = MySQLStore.__new__(MySQLStore)
    store._saved_batches = []
    store._existing = existing or []
    store._abilities = abilities or [
        {
            "ability_id": 101,
            "ability_name": "Kafka 数据接入能力",
            "ability_category": "数据采集",
            "position_name": "大数据工程师",
            "evidence": {"keyword": "Kafka 数据接入"},
        },
        {
            "ability_id": 102,
            "ability_name": "图像识别模型训练",
            "ability_category": "计算机视觉",
            "position_name": "算法工程师",
            "evidence": {"keyword": "视觉识别"},
        },
    ]
    store._nodes = [
        {
            "node_id": "chapter-data-ingestion",
            "node_name": "数据采集",
            "node_path": ["大数据分析", "数据采集"],
            "is_leaf": False,
        },
        {
            "node_id": "kafka-basic",
            "node_name": "Kafka 数据接入",
            "node_path": ["大数据分析", "数据采集", "Kafka 数据接入"],
            "is_leaf": True,
        },
        {
            "node_id": "flume-basic",
            "node_name": "Flume 日志采集",
            "node_path": ["大数据分析", "数据采集", "Flume 日志采集"],
            "is_leaf": True,
        },
    ]

    def list_course_abilities(self, course_id):
        return list(self._abilities)

    def list_course_node_binding_candidates(self, course_id):
        return list(self._nodes)

    def list_course_ability_mappings(self, course_id):
        return list(self._existing)

    def upsert_course_ability_mappings(self, course_id, mappings, *, updated_by=None):
        saved = []
        rejected = []
        leaf_ids = {node["node_id"] for node in self._nodes if node["is_leaf"]}
        for item in mappings:
            if item["node_id"] not in leaf_ids:
                rejected.append({**item, "reason": "node is not a leaf knowledge point"})
                continue
            saved.append(item)
        self._saved_batches.append(saved)
        self._existing.extend(
            {
                "mapping_id": index + 1,
                "course_id": course_id,
                "ability_id": item["ability_id"],
                "node_id": item["node_id"],
                "support_level": item["support_level"],
                "review_status": item["review_status"],
                "match_reason": item["match_reason"],
                "evidence": item["evidence"],
            }
            for index, item in enumerate(saved)
        )
        return {"course_id": course_id, "saved": len(saved), "rejected": rejected}

    store.list_course_abilities = MethodType(list_course_abilities, store)
    store.list_course_node_binding_candidates = MethodType(list_course_node_binding_candidates, store)
    store.list_course_ability_mappings = MethodType(list_course_ability_mappings, store)
    store.upsert_course_ability_mappings = MethodType(upsert_course_ability_mappings, store)
    return store


def test_generate_ability_mapping_candidates_creates_draft_leaf_mapping_only():
    store = _store_stub(abilities=[
        {
            "ability_id": 101,
            "ability_name": "Kafka 数据接入能力",
            "ability_category": "数据采集",
            "position_name": "大数据工程师",
            "evidence": {"keyword": "Kafka 数据接入"},
        }
    ])

    result = store.generate_course_ability_mapping_candidates("course_big_data")

    assert result["generated"] == 1
    saved = store._saved_batches[0]
    assert saved[0]["node_id"] == "kafka-basic"
    assert saved[0]["review_status"] == "draft"
    assert saved[0]["evidence"]["requires_teacher_review"] is True


def test_generate_ability_mapping_candidates_skips_unmatched_ability():
    store = _store_stub(abilities=[
        {
            "ability_id": 102,
            "ability_name": "图像识别模型训练",
            "ability_category": "计算机视觉",
            "position_name": "算法工程师",
            "evidence": {"keyword": "视觉识别"},
        }
    ])

    result = store.generate_course_ability_mapping_candidates("course_big_data")

    assert result["generated"] == 0
    assert result["skipped"][0]["ability_id"] == 102
    assert store._saved_batches == []


def test_generate_ability_mapping_candidates_does_not_duplicate_existing_mapping():
    store = _store_stub(
        existing=[
            {
                "mapping_id": 9,
                "ability_id": 101,
                "node_id": "kafka-basic",
                "review_status": "draft",
            }
        ],
        abilities=[
            {
                "ability_id": 101,
                "ability_name": "Kafka 数据接入能力",
                "ability_category": "数据采集",
                "position_name": "大数据工程师",
                "evidence": {"keyword": "Kafka 数据接入"},
            }
        ],
    )

    result = store.generate_course_ability_mapping_candidates("course_big_data")

    assert result["generated"] == 0
    assert result["skipped"][0]["reason"] == "未找到达到阈值的叶子知识点候选"
    assert store._saved_batches == []
