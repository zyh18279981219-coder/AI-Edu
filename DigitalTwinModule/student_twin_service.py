from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from DigitalTwinModule.course_tree import CourseTree
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

    def __init__(self) -> None:
        self.course_tree = CourseTree()

    def build_summary(self, profile: TwinProfile, trend: List[TrendPoint] | None = None) -> Dict:
        trend = trend or []
        nodes = list(profile.knowledge_nodes or [])

        radar = self._build_radar(profile, nodes, trend)
        weak_nodes = self._get_weak_nodes(nodes)
        level = self._classify_level(profile.overall_mastery, len(weak_nodes))
        risks = self._build_risks(profile, nodes, trend, weak_nodes)
        trend_summary = self._build_trend_summary(profile, trend)

        return {
            "username": profile.username,
            "last_updated": profile.last_updated,
            "overall_mastery": round(profile.overall_mastery, 2),
            "technical_level": level,
            "radar": radar,
            "weak_nodes": weak_nodes,
            "risk_alerts": [risk.to_dict() for risk in risks],
            "trend": trend_summary,
            "node_summary": {
                "total_nodes": len(nodes),
                "weak_node_count": len(weak_nodes),
                "strong_node_count": sum(1 for node in nodes if node.mastery_score >= 80),
                "average_progress": round(self._average([node.progress for node in nodes]), 2),
                "average_quiz_score": round(self._average([node.quiz_score for node in nodes if node.quiz_score is not None]), 2),
            },
            "outputs": {
                "for_course_twin": {
                    "overall_mastery": round(profile.overall_mastery, 2),
                    "technical_level": level["label"],
                    "weak_nodes": [item["node_id"] for item in weak_nodes[:5]],
                    "learning_risk_level": risks[0].level if risks else "low",
                },
                "for_teacher_twin": {
                    "technical_level": level["label"],
                    "risk_alerts": [risk.to_dict() for risk in risks[:3]],
                    "trend_status": trend_summary["trend_status"],
                    "weak_nodes": weak_nodes[:5],
                },
            },
        }

    def _build_radar(self, profile: TwinProfile, nodes: List[KnowledgeNodeScore], trend: List[TrendPoint]) -> List[Dict]:
        progress_avg = self._average([node.progress for node in nodes])
        quiz_avg = self._average([node.quiz_score for node in nodes if node.quiz_score is not None])
        engagement = self._engagement_score(nodes)
        stability = self._stability_score(trend)
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
            if node.mastery_score >= 60:
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
        if overall_mastery < 40:
            return {"label": "基础薄弱", "code": "foundation_risk", "description": "核心知识掌握较弱，需要优先补齐基础。"}
        if overall_mastery < 60:
            return {"label": "基础建立中", "code": "building_foundation", "description": "已形成部分知识基础，但仍存在明显短板。"}
        if overall_mastery < 80:
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

        if profile.overall_mastery < 45:
            risks.append(RiskAlert("knowledge_gap", "high", "知识薄弱风险", "整体掌握度偏低，建议优先补强基础知识点。"))
        elif profile.overall_mastery < 60:
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
