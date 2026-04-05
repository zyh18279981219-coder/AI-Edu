import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from DatabaseModule.sqlite_store import get_sqlite_store
from DigitalTwinModule.models import LearningPath, WeakNode
from DigitalTwinModule.twin_profile_store import TwinProfileStore
from PathPlannerModule.resource_recommender import ResourceRecommender
from PathPlannerModule.weak_node_detector import WeakNodeDetector

load_dotenv()
logger = logging.getLogger(__name__)


class PathPlannerAgent:
    def __init__(self):
        self.sqlite_store = get_sqlite_store()
        self.store = TwinProfileStore()
        self.detector = WeakNodeDetector()
        self.recommender = ResourceRecommender()
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=os.environ.get("model_name"),
                temperature=0.3,
                base_url=os.environ.get("base_url"),
                api_key=os.environ.get("api_key"),
            )
        return self._llm

    def _save_path_result(self, username: str, payload: dict):
        filename = f"{username}_path_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.sqlite_store.save_learning_plan(
            username=username,
            filename=filename,
            payload=payload,
            plan_path="",
            category="path",
        )
        logger.info("PathPlannerAgent: wrote path to SQLite for %s (%s)", username, filename)

    def _llm_reorder_nodes(self, weak_nodes: list[WeakNode]) -> tuple[list[WeakNode], str]:
        if len(weak_nodes) <= 1:
            return weak_nodes, ""

        node_list = "\n".join(f"- {node.node_id}" for node in weak_nodes)
        prompt = (
            "你是一名大数据课程专家。以下是一名学生需要学习的知识点：\n"
            f"{node_list}\n\n"
            "请仅根据这些知识点之间的学习依赖关系，给出最合理的学习顺序。"
            "只返回 JSON，格式为 "
            '{"order": ["知识点1", "知识点2"], "reason": "一句话说明排序依据"}'
        )
        try:
            llm = self._get_llm()
            resp = llm.invoke(prompt)
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
        if not weak_nodes:
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
            f"你是一名大数据课程学习顾问。该学生存在以下薄弱知识点：\n{weak_list}\n\n"
            f"{order_context}\n\n"
            "请给出一段个性化学习建议："
            "1. 解释为什么按这个顺序学习更合理；"
            "2. 针对掌握度最低的两个知识点，各给一条可执行建议；"
            "3. 最后给一句鼓励；"
            "4. 总字数控制在 150 字以内。"
        )
        try:
            llm = self._get_llm()
            return llm.invoke(prompt).content.strip()
        except Exception as exc:
            logger.warning("PathPlannerAgent: LLM advice failed: %s", exc)
            return ""

    def plan(self, username: str) -> dict:
        try:
            profile = self.store.load(username)
        except FileNotFoundError:
            return {"status": "error", "message": f"TwinProfile for user '{username}' not found"}

        weak_nodes = self.detector.detect(profile)
        if not weak_nodes:
            result = {
                "status": "no_weak_nodes",
                "message": "暂无薄弱知识点",
                "username": username,
                "generated_at": datetime.now().isoformat(),
                "weak_nodes": [],
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
            generated_at=datetime.now().isoformat(),
            status="active",
            weak_nodes=enriched_nodes,
            llm_advice=advice,
            llm_order_reason=order_reason,
        )

        payload = path_obj.model_dump()
        self._save_path_result(username, payload)
        return payload

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

        raw["generated_at"] = datetime.now().isoformat()
        self._save_path_result(username, raw)
        logger.info("PathPlannerAgent: updated path in SQLite for %s", username)
        return raw

    def get_latest_path(self, username: str) -> dict | None:
        try:
            latest = self.sqlite_store.get_latest_learning_plan(
                username=username,
                category="path",
                filename_prefix=f"{username}_path_",
            )
            if latest is not None:
                logger.info("PathPlannerAgent: read latest path from SQLite for %s (%s)", username, latest["filename"])
                return latest["data"]
        except Exception:
            logger.exception("PathPlannerAgent: failed reading latest path from SQLite for %s", username)
        return None
