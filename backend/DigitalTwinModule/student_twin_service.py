from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from DatabaseModule.database_factory import DatabaseFactory
from DiagnosisModule.diagnosis_service import StudentDiagnosisService
from DigitalTwinModule.course_tree import CourseTree
from DigitalTwinModule.homework_evidence_service import HomeworkEvidenceService
from DigitalTwinModule.models import KnowledgeNodeScore, TrendPoint, TwinProfile


@dataclass
class RiskAlert:
    code: str
    level: str
    title: str
    detail: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "level": self.level,
            "title": self.title,
            "detail": self.detail,
        }


class StudentTwinService:
    """Build student digital twin summaries for visualization and coordination."""

    WEAK_NODE_THRESHOLD = 60.0
    STRONG_NODE_THRESHOLD = 80.0
    FOUNDATION_RISK_THRESHOLD = 40.0
    BUILDING_FOUNDATION_THRESHOLD = 60.0
    ADVANCED_GROWTH_THRESHOLD = 80.0
    HIGH_RISK_THRESHOLD = 45.0
    MEDIUM_RISK_THRESHOLD = 60.0
    TREND_DROP_THRESHOLD = 5.0

    def __init__(self, course_id: str = "course_big_data") -> None:
        self.course_tree = CourseTree(course_id)
        self.homework_evidence = HomeworkEvidenceService()
        self.store = DatabaseFactory.get_store()

    def build_summary(self, profile: TwinProfile, trend: List[TrendPoint] | None = None, course_id: str | None = None) -> Dict:
        trend = trend or []
        nodes = list(profile.knowledge_nodes or [])
        homework_evidence = self.homework_evidence.build_student_evidence(profile.username, course_id)

        radar = self._build_radar(profile, nodes, trend, homework_evidence)
        weak_nodes = self._get_weak_nodes(nodes)
        level = self._classify_level(profile.overall_mastery, len(weak_nodes))
        risks = self._build_risks(profile, nodes, trend, weak_nodes)
        trend_summary = self._build_trend_summary(profile, trend)
        trend_summary["attribution_points"] = self._build_trend_attribution_points(profile.username, trend, course_id)
        homework_summary = homework_evidence.get("practice_summary") or {}
        career_abilities = self._build_career_ability_attainment(profile.username, course_id, nodes)
        student_career_abilities = self._student_career_ability_view(career_abilities)
        
        # 计算整体风险等级
        overall_risk_level = self._calculate_overall_risk_level(risks)

        return {
            "username": profile.username,
            "last_updated": profile.last_updated,
            "generated_at": profile.last_updated,  # 新增：诊断生成时间
            "overall_mastery": round(profile.overall_mastery, 2),
            "overall_risk_level": overall_risk_level,  # 新增：整体风险等级
            "technical_level": level,
            "radar": radar,
            "weak_nodes": weak_nodes,
            "chapter_practice": homework_evidence.get("chapter_practice", []),
            "knowledge_point_homework_evidence": homework_evidence.get("knowledge_point_homework_evidence", []),
            "practice_summary": homework_summary,
            "career_abilities": student_career_abilities,
            "risk_alerts": [risk.to_dict() for risk in risks],
            "trend": trend_summary,
            "node_summary": {
                "total_nodes": len(nodes),
                "weak_node_count": len(weak_nodes),
                "strong_node_count": sum(1 for node in nodes if node.mastery_score >= self.STRONG_NODE_THRESHOLD),
                "average_progress": round(self._average([node.progress for node in nodes]), 2),
                "average_quiz_score": round(self._average([node.quiz_score for node in nodes if node.quiz_score is not None]), 2),
                "average_practice_score": homework_summary.get("average_practice_score"),
                "homework_coverage_node_count": homework_summary.get("coverage_node_count", 0),
            },
            "outputs": {
                "for_course_twin": {
                    "overall_mastery": round(profile.overall_mastery, 2),
                    "technical_level": level["label"],
                    "weak_nodes": [item["node_id"] for item in weak_nodes[:5]],
                    "career_ability_risks": [
                        item for item in student_career_abilities if item.get("level") == "待提升"
                    ],
                    "learning_risk_level": risks[0].level if risks else "low",
                },
                "for_teacher_twin": {
                    "technical_level": level["label"],
                    "risk_alerts": [risk.to_dict() for risk in risks[:3]],
                    "trend_status": trend_summary["trend_status"],
                    "weak_nodes": weak_nodes[:5],
                    "career_abilities": career_abilities,
                    "chapter_practice": homework_evidence.get("chapter_practice", [])[:5],
                    "knowledge_point_homework_evidence": homework_evidence.get("knowledge_point_homework_evidence", [])[:5],
                },
            },
        }

    def _build_career_ability_attainment(
        self,
        username: str,
        course_id: str | None,
        nodes: List[KnowledgeNodeScore],
    ) -> List[Dict]:
        resolved_course_id = str(course_id or getattr(self.course_tree, "course_id", "") or "course_big_data")
        try:
            summary = self.store.get_course_summary(resolved_course_id)
        except Exception:
            summary = None
        if summary and str(summary.get("lifecycle_status") or "") != "published":
            return []
        mastery_by_node = {str(node.node_id): float(node.mastery_score or 0) for node in nodes}
        try:
            mappings = [
                item
                for item in self.store.list_course_ability_mappings(resolved_course_id)
                if str(item.get("review_status") or "") == "confirmed"
            ]
        except Exception:
            return []
        if not mappings:
            return []

        grouped: Dict[int, Dict] = {}
        for item in mappings:
            ability_id = int(item.get("ability_id") or 0)
            if ability_id <= 0:
                continue
            grouped.setdefault(
                ability_id,
                {
                    "ability_id": ability_id,
                    "ability_name": item.get("ability_name") or f"能力{ability_id}",
                    "ability_category": item.get("ability_category"),
                    "position_id": item.get("position_id"),
                    "position_name": item.get("position_name"),
                    "position_type": item.get("position_type"),
                    "nodes": [],
                },
            )
            grouped[ability_id]["nodes"].append(item)

        result: List[Dict] = []
        for ability in grouped.values():
            weighted_sum = 0.0
            total_weight = 0.0
            gap_nodes: List[Dict] = []
            supporting_nodes: List[Dict] = []
            for item in ability["nodes"]:
                node_id = str(item.get("node_id") or "")
                if not node_id:
                    continue
                weight = self._ability_support_weight(item)
                mastery = mastery_by_node.get(node_id)
                mastery_value = float(mastery) if mastery is not None else 0.0
                weighted_sum += weight * mastery_value
                total_weight += weight
                node_payload = {
                    "node_id": node_id,
                    "node_name": item.get("node_name"),
                    "node_path": item.get("node_path") or [],
                    "mastery_score": round(mastery_value, 2),
                    "support_weight": round(weight, 2),
                    "support_level": item.get("support_level"),
                }
                supporting_nodes.append(node_payload)
                if mastery is None or mastery_value < self.WEAK_NODE_THRESHOLD:
                    gap_nodes.append(node_payload)
            if total_weight <= 0:
                continue
            attainment = round(weighted_sum / total_weight, 2)
            result.append(
                {
                    "ability_id": ability["ability_id"],
                    "ability_name": ability["ability_name"],
                    "ability_category": ability.get("ability_category"),
                    "position_id": ability.get("position_id"),
                    "position_name": ability.get("position_name"),
                    "position_type": ability.get("position_type"),
                    "attainment_score": attainment,
                    "level": self._career_ability_level(attainment),
                    "gap_nodes": sorted(gap_nodes, key=lambda item: item["mastery_score"])[:5],
                    "supporting_nodes": sorted(
                        supporting_nodes,
                        key=lambda item: item["support_weight"],
                        reverse=True,
                    )[:8],
                    "calculation_note": "读取教师确认发布的职业能力-叶子知识点支撑关系，并结合学生知识点掌握度折算。",
                }
            )
        level_order = {"待提升": 0, "基本达成": 1, "较好达成": 2}
        return sorted(result, key=lambda item: (level_order.get(item["level"], 9), item["attainment_score"]))

    def _student_career_ability_view(self, abilities: List[Dict]) -> List[Dict]:
        """Keep student-facing ability attainment free of audit weights and source evidence."""
        result: List[Dict] = []
        for ability in abilities:
            if not isinstance(ability, dict):
                continue
            gap_nodes = []
            for node in ability.get("gap_nodes") or []:
                if not isinstance(node, dict):
                    continue
                gap_nodes.append(
                    {
                        "node_id": node.get("node_id"),
                        "node_name": node.get("node_name"),
                        "node_path": node.get("node_path") or [],
                        "mastery_score": node.get("mastery_score"),
                    }
                )
            result.append(
                {
                    "ability_id": ability.get("ability_id"),
                    "ability_name": ability.get("ability_name"),
                    "ability_category": ability.get("ability_category"),
                    "position_id": ability.get("position_id"),
                    "position_name": ability.get("position_name"),
                    "position_type": ability.get("position_type"),
                    "attainment_score": ability.get("attainment_score"),
                    "level": ability.get("level"),
                    "gap_nodes": gap_nodes,
                }
            )
        return result

    def _ability_support_weight(self, item: Dict) -> float:
        raw_weight = item.get("support_weight")
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            weight = 0.0
        if weight > 0:
            return weight
        level = str(item.get("support_level") or "").lower()
        return {
            "high": 1.0,
            "strong": 1.0,
            "medium": 0.6,
            "middle": 0.6,
            "low": 0.3,
            "weak": 0.3,
        }.get(level, 0.6)

    def _career_ability_level(self, score: float) -> str:
        if score < 60:
            return "待提升"
        if score < 80:
            return "基本达成"
        return "较好达成"

    def _build_radar(
        self,
        profile: TwinProfile,
        nodes: List[KnowledgeNodeScore],
        trend: List[TrendPoint],
        homework_evidence: Dict | None = None,
    ) -> List[Dict]:
        progress_avg = self._average([node.progress for node in nodes])
        quiz_avg = self._average([node.quiz_score for node in nodes if node.quiz_score is not None])
        engagement = self._engagement_score(nodes)
        stability = self._stability_score(trend)
        practice_summary = (homework_evidence or {}).get("practice_summary") or {}
        practice = practice_summary.get("average_practice_score")
        if practice is None:
            practice = self._practice_proxy(nodes)

        return [
            {"name": "知识掌握", "value": round(profile.overall_mastery, 2)},
            {"name": "学习投入", "value": round(engagement, 2)},
            {"name": "实践能力", "value": round(practice, 2)},
            {"name": "学习稳定性", "value": round(stability, 2)},
            {"name": "测验表现", "value": round(max(quiz_avg, progress_avg * 0.8), 2)},
        ]

    def _get_weak_nodes(self, nodes: List[KnowledgeNodeScore]) -> List[Dict]:
        ordered = sorted(nodes, key=lambda item: item.mastery_score)
        weak_nodes = []
        for node in ordered:
            if node.mastery_score >= self.WEAK_NODE_THRESHOLD:
                continue
            node_path = list(node.node_path or [])
            if not node_path:
                node_path = list(self.course_tree.resolve_node_path(node.node_id) or [])
            weak_nodes.append(
                {
                    "node_id": node.node_id,
                    "node_path": node_path,
                    "mastery_score": round(node.mastery_score, 2),
                    "progress": round(node.progress, 2),
                    "quiz_score": round(node.quiz_score or 0.0, 2),
                }
            )
        return weak_nodes

    def _classify_level(self, overall_mastery: float, weak_count: int) -> Dict:
        if overall_mastery < self.FOUNDATION_RISK_THRESHOLD:
            return {"label": "基础薄弱", "code": "foundation_risk", "description": "核心知识掌握较弱，需要优先补齐基础。"}
        if overall_mastery < self.BUILDING_FOUNDATION_THRESHOLD:
            return {"label": "基础建立中", "code": "building_foundation", "description": "已形成部分知识基础，但仍存在明显短板。"}
        if overall_mastery < self.ADVANCED_GROWTH_THRESHOLD:
            label = "能力成型" if weak_count <= 4 else "基础建立中"
            description = "核心能力正在成型，可进入更系统的强化训练。" if label == "能力成型" else "整体水平中等，但仍有较多薄弱知识点。"
            code = "capability_forming" if label == "能力成型" else "building_foundation"
            return {"label": label, "code": code, "description": description}
        return {"label": "进阶提升", "code": "advanced_growth", "description": "整体掌握较好，可进入更高阶任务与项目实践。"}

    def _build_risks(self, profile: TwinProfile, nodes: List[KnowledgeNodeScore], trend: List[TrendPoint], weak_nodes: List[Dict]) -> List[RiskAlert]:
        risks: List[RiskAlert] = []
        progress_avg = self._average([node.progress for node in nodes])
        engagement = self._engagement_score(nodes)
        trend_status = self._build_trend_summary(profile, trend)["trend_status"]

        if profile.overall_mastery < self.HIGH_RISK_THRESHOLD:
            risks.append(RiskAlert("knowledge_gap", "high", "知识薄弱风险", "整体掌握度偏低，建议优先补强基础知识点。"))
        elif profile.overall_mastery < self.MEDIUM_RISK_THRESHOLD:
            risks.append(RiskAlert("knowledge_gap", "medium", "知识薄弱风险", "部分关键知识点掌握不足，需要持续巩固。"))

        if progress_avg < 50:
            risks.append(RiskAlert("progress_lag", "high", "进度滞后风险", "平均学习进度偏低，存在课程推进滞后的风险。"))
        elif progress_avg < 70:
            risks.append(RiskAlert("progress_lag", "medium", "进度滞后风险", "学习进度仍有提升空间，建议保持稳定推进。"))

        if engagement < 45:
            risks.append(RiskAlert("engagement_low", "medium", "学习投入风险", "互动次数和学习时长偏低，可能影响持续掌握。"))

        if trend_status == "downward":
            risks.append(RiskAlert("trend_down", "medium", "趋势下滑风险", "最近掌握度出现下降，建议及时干预。"))

        if len(weak_nodes) >= 5:
            risks.append(RiskAlert("weak_nodes_cluster", "medium", "薄弱点集中风险", "当前存在多个薄弱知识点，建议按优先级逐步突破。"))

        level_order = {"high": 0, "medium": 1, "low": 2}
        return sorted(risks, key=lambda item: (level_order.get(item.level, 9), item.code))
    
    def _calculate_overall_risk_level(self, risks: List[RiskAlert]) -> str:
        """
        计算整体风险等级
        
        规则：
        - 有任何 high 风险 → high
        - 有 medium 风险 → medium
        - 否则 → low
        """
        if not risks:
            return "low"
        
        for risk in risks:
            if risk.level == "high":
                return "high"
        
        for risk in risks:
            if risk.level == "medium":
                return "medium"
        
        return "low"

    def _build_trend_summary(self, profile: TwinProfile, trend: List[TrendPoint]) -> Dict:
        points = [point.model_dump() if hasattr(point, "model_dump") else {"date": point.date, "overall_mastery": point.overall_mastery} for point in trend]
        if len(points) < 2:
            return {
                "trend_status": "stable",
                "change": 0.0,
                "points": points,
                "summary": "当前趋势数据较少，暂按稳定状态处理。",
            }

        start = float(points[0]["overall_mastery"])
        end = float(points[-1]["overall_mastery"])
        change = round(end - start, 2)
        if change >= 5:
            status = "upward"
            summary = "近期整体掌握度呈上升趋势。"
        elif change <= -5:
            status = "downward"
            summary = "近期整体掌握度呈下降趋势，需要关注。"
        else:
            status = "stable"
            summary = "近期整体掌握度较为稳定。"
        return {
            "trend_status": status,
            "change": change,
            "points": points,
            "summary": summary,
        }

    def _build_trend_attribution_points(
        self,
        username: str,
        trend: List[TrendPoint],
        course_id: str | None,
    ) -> List[Dict]:
        points = [
            point.model_dump() if hasattr(point, "model_dump") else {"date": point.date, "overall_mastery": point.overall_mastery}
            for point in trend
        ]
        if len(points) < 2:
            return []

        drops: List[Dict] = []
        for index in range(1, len(points)):
            previous = points[index - 1]
            current = points[index]
            previous_score = float(previous.get("overall_mastery") or 0)
            current_score = float(current.get("overall_mastery") or 0)
            drop = round(previous_score - current_score, 2)
            if drop < self.TREND_DROP_THRESHOLD:
                continue
            drops.append(
                {
                    "date": str(current.get("date") or ""),
                    "previous_date": str(previous.get("date") or ""),
                    "previous_mastery": round(previous_score, 2),
                    "current_mastery": round(current_score, 2),
                    "drop": drop,
                }
            )
        if not drops:
            return []

        try:
            evidence = StudentDiagnosisService()._load_evidence_timeline(
                username,
                str(course_id or getattr(self.course_tree, "course_id", "") or "course_big_data"),
                limit=80,
            )
        except Exception:
            evidence = []

        result = []
        for drop in sorted(drops, key=lambda item: item["drop"], reverse=True)[:3]:
            related = self._evidence_near_date(evidence, drop["date"])
            evidence_level = "partial" if related else "insufficient"
            result.append(
                {
                    **drop,
                    "evidence_level": evidence_level,
                    "evidence_status_label": "可追溯到当天学习证据" if related else "依据不足，不能强行归因",
                    "snapshot_compare": self._drop_snapshot_compare(drop),
                    "primary_reason": self._drop_primary_reason(related),
                    "reason_summary": self._drop_reason_summary(drop, related),
                    "evidence_summary": self._drop_evidence_summary(related),
                    "evidence": related[:5],
                    "suggested_actions": self._drop_suggested_actions(related),
                }
            )
        return result

    def _evidence_near_date(self, evidence: List[Dict], target_date: str) -> List[Dict]:
        if not target_date:
            return []
        related = []
        for item in evidence:
            occurred_at = str(item.get("occurred_at") or "")
            if not occurred_at.startswith(target_date):
                continue
            related.append(self._compact_evidence_item(item))
        return related

    def _compact_evidence_item(self, item: Dict) -> Dict:
        item_type = str(item.get("type") or "")
        summary = ""
        if item_type == "quiz":
            summary = f"测验得分 {float(item.get('score') or 0):.1f}/{float(item.get('total') or 0):.1f}"
        elif item_type == "homework":
            summary = f"{item.get('title') or '作业'}，得分 {float(item.get('score') or 0):.1f}/{float(item.get('total') or 0):.1f}"
        elif item_type == "resource_learning":
            summary = f"资源学习进度 {float(item.get('progress_percent') or 0):.0f}%"
        elif item_type == "fivee_effectiveness":
            summary = f"5E 引导有效度 {float(item.get('effectiveness_score') or 0):.1f}"
        return {
            "type": item_type,
            "node_id": item.get("node_id"),
            "occurred_at": item.get("occurred_at"),
            "title": item.get("title") or item.get("resource_path") or item.get("summary"),
            "summary": summary or str(item.get("summary") or "学习证据已记录"),
        }

    def _drop_reason_summary(self, drop: Dict, related: List[Dict]) -> str:
        if not related:
            return (
                f"{drop['date']} 掌握度较前一快照下降 {drop['drop']:.1f} 分，"
                "但当天缺少可直接关联的测验、作业或资源学习证据，暂不能强行归因。"
            )
        quiz_items = [item for item in related if item.get("type") == "quiz"]
        homework_items = [item for item in related if item.get("type") == "homework"]
        resource_items = [item for item in related if item.get("type") == "resource_learning"]
        parts = [f"{drop['date']} 掌握度较前一快照下降 {drop['drop']:.1f} 分"]
        if quiz_items:
            parts.append(f"当天存在 {len(quiz_items)} 条测验证据")
        if homework_items:
            parts.append(f"{len(homework_items)} 条作业证据")
        if resource_items:
            parts.append(f"{len(resource_items)} 条资源学习证据")
        return "，".join(parts) + "，建议结合下方证据进一步核查。"

    def _drop_snapshot_compare(self, drop: Dict) -> Dict:
        previous_mastery = float(drop.get("previous_mastery") or 0)
        current_mastery = float(drop.get("current_mastery") or 0)
        return {
            "previous": {
                "date": drop.get("previous_date"),
                "overall_mastery": round(previous_mastery, 2),
            },
            "current": {
                "date": drop.get("date"),
                "overall_mastery": round(current_mastery, 2),
            },
            "change": round(current_mastery - previous_mastery, 2),
            "drop": round(float(drop.get("drop") or 0), 2),
        }

    def _drop_evidence_summary(self, related: List[Dict]) -> List[Dict]:
        if not related:
            return [
                {
                    "type": "missing",
                    "label": "依据不足",
                    "count": 0,
                    "detail": "当天没有可直接关联的测验、作业或资源学习记录。",
                }
            ]

        type_labels = {
            "quiz": "在线测验",
            "homework": "作业/实践",
            "resource_learning": "资源学习",
            "fivee_effectiveness": "5E 互动",
            "intervention_completion": "干预任务",
        }
        grouped: Dict[str, List[Dict]] = {}
        for item in related:
            grouped.setdefault(str(item.get("type") or "unknown"), []).append(item)

        summary: List[Dict] = []
        for item_type, items in grouped.items():
            details = [str(item.get("summary") or item.get("title") or "") for item in items]
            details = [item for item in details if item]
            summary.append(
                {
                    "type": item_type,
                    "label": type_labels.get(item_type, "学习证据"),
                    "count": len(items),
                    "detail": "；".join(details[:2]) if details else "已记录当天相关学习证据。",
                }
            )
        return summary

    def _drop_primary_reason(self, related: List[Dict]) -> str:
        if not related:
            return "依据不足"

        quiz_items = [item for item in related if item.get("type") == "quiz"]
        if quiz_items:
            low_quiz = []
            for item in quiz_items:
                score_text = str(item.get("summary") or "")
                try:
                    score_part = score_text.split()[1]
                    score, total = score_part.split("/")[:2]
                    score_rate = float(score) / float(total) if float(total) else 0
                except Exception:
                    score_rate = 0
                if score_rate and score_rate < 0.6:
                    low_quiz.append(item)
            if low_quiz:
                return "当天测验表现偏低"
            return "当天存在测验记录，需结合错题进一步核查"

        if any(item.get("type") == "homework" for item in related):
            return "当天作业或实践结果需要复查"

        if any(item.get("type") == "resource_learning" for item in related):
            return "当天资源学习进度需要复查"

        return "当天存在过程证据，需结合测验或作业补充判断"

    def _drop_suggested_actions(self, related: List[Dict]) -> List[str]:
        if not related:
            return ["补充当天测验、作业或学习记录", "完成一次针对薄弱知识点的小测"]
        actions = ["复查当天证据对应的知识点"]
        if any(item.get("type") == "quiz" for item in related):
            actions.append("查看错题并重新练习")
        if any(item.get("type") == "homework" for item in related):
            actions.append("回看作业反馈")
        if any(item.get("type") == "resource_learning" for item in related):
            actions.append("补看未完成资源")
        return actions

    def _engagement_score(self, nodes: List[KnowledgeNodeScore]) -> float:
        if not nodes:
            return 0.0
        interaction_avg = self._average([min(node.llm_interaction_count / 10.0, 1.0) * 100 for node in nodes])
        duration_avg = self._average([min(node.study_duration_minutes / 30.0, 1.0) * 100 for node in nodes])
        return 0.6 * interaction_avg + 0.4 * duration_avg

    def _stability_score(self, trend: List[TrendPoint]) -> float:
        if len(trend) < 3:
            return 70.0
        values = [float(point.overall_mastery) for point in trend]
        diffs = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
        volatility = self._average(diffs)
        return max(0.0, 100.0 - min(volatility * 4, 100.0))

    def _practice_proxy(self, nodes: List[KnowledgeNodeScore]) -> float:
        if not nodes:
            return 0.0
        progress_avg = self._average([node.progress for node in nodes])
        quiz_avg = self._average([node.quiz_score for node in nodes if node.quiz_score is not None])
        engagement = self._engagement_score(nodes)
        return 0.4 * progress_avg + 0.35 * quiz_avg + 0.25 * engagement

    def _average(self, values: List[float]) -> float:
        valid = [float(item) for item in values if item is not None]
        if not valid:
            return 0.0
        return sum(valid) / len(valid)
