from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from tools.env_loader import load_project_env

from DatabaseModule.database_factory import DatabaseFactory
from DiagnosisModule.diagnosis_service import StudentDiagnosisService
from DigitalTwinModule.models import LearningPath, WeakNode
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from PathPlannerModule.resource_recommender import ResourceRecommender
from PathPlannerModule.weak_node_detector import WeakNodeDetector

load_project_env()
logger = logging.getLogger(__name__)


class PathPlannerAgent:
    def __init__(self) -> None:
        self.database_store = DatabaseFactory.get_store()
        self.store = TwinProfileStore()
        self.detector = WeakNodeDetector()
        self.recommender = ResourceRecommender()
        self.diagnosis_service = StudentDiagnosisService()
        self._llm = None

    def _llm_enabled(self) -> bool:
        value = os.environ.get("PATH_PLANNER_LLM_ENABLED", "0").strip().lower()
        return value in {"1", "true", "yes", "on"} and bool(os.environ.get("api_key"))

    def _get_llm(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            import httpx

            self._llm = ChatOpenAI(
                model=os.environ.get("model_name"),
                temperature=0.3,
                base_url=os.environ.get("base_url"),
                api_key=os.environ.get("api_key"),
                http_client=httpx.Client(verify=False),
            )
        return self._llm

    def _save_path_result(self, username: str, payload: dict) -> None:
        filename = f"{username}_path_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.database_store.save_learning_plan(
            username=username,
            filename=filename,
            payload=payload,
            plan_path="",
            category="path",
        )
        logger.info(
            "PathPlannerAgent: wrote path to %s for %s (%s)",
            type(self.database_store).__name__,
            username,
            filename,
        )

    def _weak_nodes_from_diagnosis(self, diagnosis: dict | None) -> list[WeakNode]:
        if not diagnosis:
            return []
        result: list[WeakNode] = []
        for priority, item in enumerate(diagnosis.get("weak_nodes", []), start=1):
            if not isinstance(item, dict) or not item.get("node_id"):
                continue
            if item.get("evidence_level") == "insufficient":
                continue
            result.append(
                WeakNode(
                    node_id=str(item["node_id"]),
                    mastery_score=float(item.get("mastery_score") or 0),
                    priority=priority,
                    resources=[],
                )
            )
        return result

    def _llm_reorder_nodes(self, weak_nodes: list[WeakNode]) -> tuple[list[WeakNode], str]:
        if len(weak_nodes) <= 1 or not self._llm_enabled():
            return weak_nodes, ""

        node_list = "\n".join(f"- {node.node_id}" for node in weak_nodes)
        prompt = (
            "你是课程学习路径规划助手。请仅根据下列薄弱知识点，给出更合理的学习顺序。\n"
            f"{node_list}\n\n"
            "只返回 JSON，格式为 "
            '{"order": ["知识点A", "知识点B"], "reason": "一句话说明排序依据"}'
        )
        try:
            resp = self._get_llm().invoke(prompt)
            content = resp.content.strip()
            if "```" in content:
                content = content.split("```", 1)[1].replace("json", "").strip()
            data = json.loads(content)
            order: list[str] = data.get("order", [])
            reason: str = data.get("reason", "")
            node_map = {node.node_id: node for node in weak_nodes}
            reordered = [node_map[node_id] for node_id in order if node_id in node_map]
            mentioned = set(order)
            reordered += [node for node in weak_nodes if node.node_id not in mentioned]
            reordered = [
                node.model_copy(update={"priority": idx})
                for idx, node in enumerate(reordered, start=1)
            ]
            return reordered, reason
        except Exception as exc:
            logger.warning("PathPlannerAgent: LLM reorder failed: %s", exc)
            return weak_nodes, ""

    def _llm_generate_advice(self, weak_nodes: list[WeakNode], order_reason: str = "") -> str:
        if not weak_nodes or not self._llm_enabled():
            return ""

        sorted_nodes = sorted(
            weak_nodes,
            key=lambda node: node.llm_priority if node.llm_priority is not None else node.priority,
        )
        order_list = " -> ".join(node.node_id for node in sorted_nodes[:6])
        weak_list = "\n".join(
            f"- {node.node_id}（掌握度 {node.mastery_score:.1f}%）"
            for node in sorted(weak_nodes, key=lambda item: item.mastery_score)[:4]
        )
        order_context = f"推荐学习顺序：{order_list}。"
        if order_reason:
            order_context += f" 排序依据：{order_reason}"

        prompt = (
            f"你是课程学习顾问。学生存在以下薄弱知识点：\n{weak_list}\n\n"
            f"{order_context}\n\n"
            "请给出 150 字以内的学习建议，语气鼓励，避免使用严重风险标签。"
        )
        try:
            return self._get_llm().invoke(prompt).content.strip()
        except Exception as exc:
            logger.warning("PathPlannerAgent: LLM advice failed: %s", exc)
            return ""

    def plan(self, username: str) -> dict:
        try:
            profile = self.store.load(username)
        except FileNotFoundError:
            return {"status": "error", "message": f"TwinProfile for user '{username}' not found"}

        diagnosis: dict | None = None
        try:
            diagnosis = self.diagnosis_service.generate_student_diagnosis(username, persist=True)
        except Exception:
            logger.exception(
                "PathPlannerAgent: diagnosis failed for %s, falling back to twin profile detector",
                username,
            )

        weak_nodes = self._weak_nodes_from_diagnosis(diagnosis) or self.detector.detect(profile)
        if not weak_nodes:
            result = {
                "status": "no_weak_nodes",
                "message": "暂未发现需要优先补学的薄弱知识点",
                "username": username,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "weak_nodes": [],
                "diagnosis": self._diagnosis_summary(diagnosis),
            }
            self._save_path_result(username, result)
            return result

        enriched_nodes: list[WeakNode] = []
        for priority, node in enumerate(weak_nodes, start=1):
            resources = self.recommender.recommend(node.node_id, node.node_id)
            enriched_nodes.append(
                WeakNode(
                    node_id=node.node_id,
                    mastery_score=node.mastery_score,
                    priority=priority,
                    resources=resources,
                )
            )

        llm_nodes, order_reason = self._llm_reorder_nodes(enriched_nodes)
        llm_priority_map = {node.node_id: node.priority for node in llm_nodes}
        enriched_nodes = [
            node.model_copy(update={"llm_priority": llm_priority_map.get(node.node_id, node.priority)})
            for node in enriched_nodes
        ]

        advice = self._llm_generate_advice(enriched_nodes, order_reason)
        path_obj = LearningPath(
            username=username,
            generated_at=datetime.now().isoformat(timespec="seconds"),
            status="active",
            weak_nodes=enriched_nodes,
            llm_advice=advice,
            llm_order_reason=order_reason,
        )

        payload = path_obj.model_dump()
        payload["diagnosis"] = self._diagnosis_summary(diagnosis)
        payload["formal_path_nodes"] = self._build_formal_path_nodes(enriched_nodes, diagnosis)
        payload["supplemental_items"] = []
        self._save_path_result(username, payload)
        return payload

    def _diagnosis_summary(self, diagnosis: dict | None) -> dict:
        if not diagnosis:
            return {}
        return {
            "report_id": diagnosis.get("report_id"),
            "course_id": diagnosis.get("course_id"),
            "evidence_level": diagnosis.get("evidence_level"),
            "confidence": diagnosis.get("confidence"),
            "persona_summary": diagnosis.get("persona_summary"),
            "student_view": diagnosis.get("student_view"),
        }

    def _build_formal_path_nodes(self, weak_nodes: list[WeakNode], diagnosis: dict | None) -> list[dict]:
        diagnosis_map = {}
        if diagnosis:
            diagnosis_map = {
                str(item.get("node_id")): item
                for item in diagnosis.get("weak_nodes", [])
                if isinstance(item, dict) and item.get("node_id")
            }
        sorted_nodes = sorted(
            weak_nodes,
            key=lambda node: node.llm_priority if node.llm_priority is not None else node.priority,
        )
        result = []
        for index, node in enumerate(sorted_nodes, start=1):
            item = diagnosis_map.get(node.node_id, {})
            result.append(
                {
                    "sequence_order": index,
                    "node_id": node.node_id,
                    "item_type": "course_knowledge_point",
                    "source": "published_course_graph",
                    "mastery_score": node.mastery_score,
                    "student_level": item.get("student_level"),
                    "reason_type": item.get("reason_type"),
                    "evidence_level": item.get("evidence_level"),
                    "suggested_actions": item.get("suggested_actions", []),
                    "resources": [resource.model_dump() for resource in node.resources],
                }
            )
        return result

    def update_path_on_mastery_change(self, username: str, node_id: str, new_score: float) -> dict:
        raw = self.get_latest_path(username)
        if raw is None:
            return {"status": "error", "message": f"No learning path found for user '{username}'"}

        if new_score >= 60:
            raw["weak_nodes"] = [node for node in raw.get("weak_nodes", []) if node["node_id"] != node_id]
        else:
            for node in raw.get("weak_nodes", []):
                if node["node_id"] == node_id:
                    node["mastery_score"] = new_score
                    break

        for idx, node in enumerate(raw.get("weak_nodes", []), start=1):
            node["priority"] = idx

        raw["generated_at"] = datetime.now().isoformat(timespec="seconds")
        self._save_path_result(username, raw)
        logger.info("PathPlannerAgent: updated path in %s for %s", type(self.database_store).__name__, username)
        return raw

    def get_latest_path(self, username: str) -> dict | None:
        try:
            latest = self.database_store.get_latest_learning_plan(
                username=username,
                category="path",
                filename_prefix=f"{username}_path_",
            )
            if latest is not None:
                logger.info(
                    "PathPlannerAgent: read latest path from %s for %s (%s)",
                    type(self.database_store).__name__,
                    username,
                    latest["filename"],
                )
                data = latest["data"]
                if isinstance(data, dict) and hasattr(self.database_store, "list_learning_path_node_status"):
                    data = dict(data)
                    data["path_node_status"] = self.database_store.list_learning_path_node_status(
                        username,
                        plan_id=latest.get("plan_id"),
                    )
                return data
        except Exception:
            logger.exception(
                "PathPlannerAgent: failed reading latest path from %s for %s",
                type(self.database_store).__name__,
                username,
            )
        return None
