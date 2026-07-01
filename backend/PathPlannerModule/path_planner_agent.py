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
        filename = f"{username}_path_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        payload["lifecycle_status"] = "active"
        save_path = getattr(self.database_store, "save_learning_path_version", None)
        if not callable(save_path):
            raise RuntimeError("Database store does not support canonical learning path versions")
        saved = save_path(username=username, payload=payload, filename=filename)
        if isinstance(saved, dict):
            payload["path_id"] = saved.get("path_id")
            payload["version_no"] = saved.get("version_no", payload.get("version_no"))
        logger.info(
            "PathPlannerAgent: wrote path to %s for %s (%s)",
            type(self.database_store).__name__,
            username,
            filename,
        )

    def _next_version_no(self, username: str, course_id: str | None = None) -> int:
        try:
            list_versions = getattr(self.database_store, "list_learning_path_versions", None)
            versions = list_versions(username=username, course_id=course_id, limit=1) if callable(list_versions) else []
        except Exception:
            logger.exception("PathPlannerAgent: failed to inspect latest path version for %s", username)
            return 1
        latest = versions[0] if versions else None
        data = latest.get("data") if isinstance(latest, dict) else None
        if not isinstance(data, dict):
            return 1
        if course_id and str(data.get("course_id") or "") != str(course_id):
            return 1
        try:
            return int(data.get("version_no") or 0) + 1
        except (TypeError, ValueError):
            return 1

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

    def _insufficient_weak_nodes_from_diagnosis(self, diagnosis: dict | None) -> list[dict]:
        if not diagnosis:
            return []
        result: list[dict] = []
        for item in diagnosis.get("weak_nodes", []):
            if not isinstance(item, dict) or not item.get("node_id"):
                continue
            if item.get("evidence_level") != "insufficient":
                continue
            result.append(
                {
                    "node_id": str(item.get("node_id") or ""),
                    "mastery_score": item.get("mastery_score"),
                    "evidence_level": "insufficient",
                    "suggested_actions": item.get("suggested_actions", []),
                    "reason": "依据不足，暂不进入正式补学路径；建议先补测验、补作业或补学习记录。",
                }
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

    def plan(
        self,
        username: str,
        *,
        course_id: str | None = None,
        trigger_type: str = "diagnosis",
        manual_goal: str | None = None,
    ) -> dict:
        try:
            profile = self.store.load(username)
        except FileNotFoundError:
            return {"status": "error", "message": f"TwinProfile for user '{username}' not found"}

        diagnosis: dict | None = None
        resolved_course_id = str(course_id or "").strip() or None
        try:
            diagnosis = self.diagnosis_service.generate_student_diagnosis(
                username,
                course_id=resolved_course_id,
                persist=True,
            )
            resolved_course_id = str(diagnosis.get("course_id") or resolved_course_id or "").strip() or None
        except PermissionError as exc:
            return {"status": "error", "message": str(exc)}
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
                "course_id": resolved_course_id,
                "version_no": self._next_version_no(username, resolved_course_id),
                "trigger_type": trigger_type,
                "trigger_reason": self._trigger_reason(trigger_type, manual_goal, diagnosis),
                "manual_goal": manual_goal,
                "basis_report_id": diagnosis.get("report_id") if diagnosis else None,
                "basis": self._path_basis(diagnosis, trigger_type, manual_goal),
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "weak_nodes": [],
                "diagnosis": self._diagnosis_summary(diagnosis),
                "formal_path_nodes": [],
                "supplemental_items": [],
            }
            self._save_path_result(username, result)
            return result

        enriched_nodes: list[WeakNode] = []
        for priority, node in enumerate(weak_nodes, start=1):
            resources = self.recommender.recommend(node.node_id, node.node_id, course_id=resolved_course_id)
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
        formal_nodes, supplemental_items = self._split_formal_and_supplemental_nodes(
            enriched_nodes,
            diagnosis,
            resolved_course_id,
        )
        payload["course_id"] = resolved_course_id
        payload["version_no"] = self._next_version_no(username, resolved_course_id)
        payload["trigger_type"] = trigger_type
        payload["trigger_reason"] = self._trigger_reason(trigger_type, manual_goal, diagnosis)
        payload["manual_goal"] = manual_goal
        payload["basis_report_id"] = diagnosis.get("report_id") if diagnosis else None
        payload["basis"] = self._path_basis(diagnosis, trigger_type, manual_goal)
        payload["diagnosis"] = self._diagnosis_summary(diagnosis)
        payload["formal_path_nodes"] = formal_nodes
        payload["supplemental_items"] = supplemental_items
        self._save_path_result(username, payload)
        return payload

    def _trigger_reason(self, trigger_type: str, manual_goal: str | None, diagnosis: dict | None) -> str:
        normalized = str(trigger_type or "diagnosis").strip() or "diagnosis"
        if normalized == "manual_goal" and manual_goal:
            return f"学生手动目标：{manual_goal}"
        if normalized == "node_completed":
            return "路径节点完成后重新评估学习安排"
        if normalized == "intervention_completed":
            return "教师干预任务完成后，学生端刷新后续学习安排"
        if normalized == "new_course":
            return "首次进入课程后生成初始学习路径"
        if diagnosis and diagnosis.get("report_id"):
            return f"根据诊断报告 {diagnosis.get('report_id')} 生成"
        return "根据当前学生画像和诊断结果生成"

    def _path_basis(self, diagnosis: dict | None, trigger_type: str, manual_goal: str | None) -> dict:
        weak_nodes = diagnosis.get("weak_nodes", []) if diagnosis else []
        insufficient_nodes = self._insufficient_weak_nodes_from_diagnosis(diagnosis)
        return {
            "trigger_type": trigger_type,
            "manual_goal": manual_goal,
            "diagnosis_report_id": diagnosis.get("report_id") if diagnosis else None,
            "diagnosis_evidence_level": diagnosis.get("evidence_level") if diagnosis else None,
            "diagnosis_confidence": diagnosis.get("confidence") if diagnosis else None,
            "weak_node_count": len(weak_nodes) if isinstance(weak_nodes, list) else 0,
            "insufficient_node_count": len(insufficient_nodes),
            "insufficient_nodes": insufficient_nodes,
            "formal_node_rule": "正式路径节点必须来自已发布课程图谱；无法映射的内容进入 supplemental_items。",
        }

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

    def _published_course_node_names(self, course_id: str | None) -> set[str]:
        resolved = str(course_id or "").strip()
        if not resolved:
            return set()
        try:
            summary = self.database_store.get_course_summary(resolved)
            if not summary or str(summary.get("lifecycle_status") or "") != "published":
                return set()
        except Exception:
            logger.exception("PathPlannerAgent: failed to verify course publish status for %s", resolved)
            return set()
        try:
            return {
                str(item).strip()
                for item in self.database_store.list_learning_nodes_for_course(resolved)
                if str(item).strip()
            }
        except Exception:
            logger.exception("PathPlannerAgent: failed to load course nodes for %s", resolved)
            return set()

    def _split_formal_and_supplemental_nodes(
        self,
        weak_nodes: list[WeakNode],
        diagnosis: dict | None,
        course_id: str | None,
    ) -> tuple[list[dict], list[dict]]:
        formal_candidates = self._build_formal_path_nodes(weak_nodes, diagnosis)
        published_nodes = self._published_course_node_names(course_id)
        formal_nodes: list[dict] = []
        supplemental_items: list[dict] = []
        for item in formal_candidates:
            node_id = str(item.get("node_id") or "").strip()
            if node_id and node_id in published_nodes:
                formal_nodes.append({
                    **item,
                    "course_id": course_id,
                    "mapping_status": "confirmed_course_node",
                })
                supplemental_items.extend(self._resource_supplemental_items(item, course_id))
                continue
            supplemental_items.append({
                **item,
                "item_type": "supplemental_learning_item",
                "source": "diagnosis_weak_node_outside_published_graph",
                "course_id": course_id,
                "mapping_status": "outside_published_course_graph",
                "reason": "该薄弱点未匹配到已发布课程图谱叶子知识点，作为辅助学习项展示，不写入正式路径节点状态。",
            })
        return formal_nodes, supplemental_items

    def _resource_supplemental_items(self, formal_node: dict, course_id: str | None) -> list[dict]:
        resources = formal_node.get("resources")
        if not isinstance(resources, list):
            return []
        node_id = str(formal_node.get("node_id") or "").strip()
        result: list[dict] = []
        for index, resource in enumerate(resources[:3], start=1):
            if not isinstance(resource, dict) or not resource.get("url"):
                continue
            result.append(
                {
                    "sequence_order": formal_node.get("sequence_order"),
                    "node_id": node_id,
                    "item_id": f"{node_id}::resource::{index}",
                    "item_type": "supplemental_item",
                    "source": "resource_recommendation",
                    "course_id": course_id,
                    "mapping_status": "resource_for_confirmed_course_node",
                    "title": resource.get("title") or resource.get("url"),
                    "resource": resource,
                    "resources": [resource],
                    "reason": resource.get("reason") or "根据薄弱知识点推荐的补充学习资源。",
                    "mastery_score": formal_node.get("mastery_score"),
                    "evidence_level": formal_node.get("evidence_level"),
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

    def get_latest_path(self, username: str, course_id: str | None = None) -> dict | None:
        try:
            latest = None
            get_active = getattr(self.database_store, "get_active_learning_path", None)
            if callable(get_active):
                latest = get_active(username=username, course_id=course_id)
            if latest is not None:
                logger.info(
                    "PathPlannerAgent: read latest path from %s for %s (%s)",
                    type(self.database_store).__name__,
                    username,
                    latest["filename"],
                )
                data = latest["data"]
                if isinstance(data, dict) and not self._is_path_course_published(data):
                    logger.info(
                        "PathPlannerAgent: skipped path for unpublished course: username=%s course_id=%s",
                        username,
                        data.get("course_id"),
                    )
                    return None
                if isinstance(data, dict) and hasattr(self.database_store, "list_learning_path_node_status"):
                    data = dict(data)
                    data["path_node_status"] = self.database_store.list_learning_path_node_status(
                        username,
                        path_id=latest.get("path_id") or data.get("path_id"),
                    )
                return data
        except Exception:
            logger.exception(
                "PathPlannerAgent: failed reading latest path from %s for %s",
                type(self.database_store).__name__,
                username,
            )
        return None

    def list_path_versions(self, username: str, limit: int = 10, course_id: str | None = None) -> list[dict]:
        """Return visible personalized path versions, newest first."""
        try:
            list_versions = getattr(self.database_store, "list_learning_path_versions", None)
            if not callable(list_versions):
                return []
            plans = list_versions(username=username, course_id=course_id, limit=limit)
        except Exception:
            logger.exception(
                "PathPlannerAgent: failed listing path versions from %s for %s",
                type(self.database_store).__name__,
                username,
            )
            return []

        result: list[dict] = []
        for plan in plans:
            data = plan.get("data") if isinstance(plan, dict) else None
            if not isinstance(data, dict):
                continue
            if course_id and str(data.get("course_id") or "").strip() != str(course_id).strip():
                continue
            if not self._is_path_course_published(data):
                continue

            item = dict(data)
            item["path_id"] = plan.get("path_id") or item.get("path_id")
            item["filename"] = plan.get("filename")
            item["updated_at"] = plan.get("updated_at") or item.get("generated_at")
            item["lifecycle_status"] = str(plan.get("status") or item.get("lifecycle_status") or "archived")
            if hasattr(self.database_store, "list_learning_path_node_status"):
                item["path_node_status"] = self.database_store.list_learning_path_node_status(
                    username,
                    path_id=item.get("path_id"),
                )
            result.append(item)
            if len(result) >= max(int(limit or 10), 1):
                break
        return result

    def _is_path_course_published(self, data: dict) -> bool:
        course_id = str(data.get("course_id") or "").strip()
        if not course_id:
            return True
        try:
            summary = self.database_store.get_course_summary(course_id)
        except Exception:
            logger.exception("PathPlannerAgent: failed checking path course publish status for %s", course_id)
            return False
        return bool(summary) and str(summary.get("lifecycle_status") or "") == "published"
