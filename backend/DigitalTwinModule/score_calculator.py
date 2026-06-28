"""
DigitalTwinModule/score_calculator.py
掌握度评分器：根据多维度原始数据计算知识点综合掌握度评分。
"""

from __future__ import annotations

from typing import Optional

from DigitalTwinModule.models import KnowledgeNodeScore, TwinProfile


class ScoreCalculator:
    """计算知识点掌握度评分（Mastery_Score）及学生整体掌握度（overall_mastery）。"""

    def calculate_mastery(
        self,
        quiz_score: Optional[float],
        progress: float,
        llm_interaction_count: int,
        study_duration_minutes: float,
    ) -> float:
        """
        按公式计算单个知识节点的掌握度评分。

        公式：
            Mastery_Score = 0.40 × quiz_score
                          + 0.30 × progress
                          + 0.20 × min(llm_interaction_count / 10, 1) × 100
                          + 0.10 × min(study_duration_minutes / 30, 1) × 100

        后处理规则：若 quiz_score >= 100 且 progress >= 100，则结果不低于 90.0。
        结果 clamp 至 [0, 100] 并保留两位小数。
        """
        # quiz_score 缺失时默认为 0
        quiz_score = quiz_score if quiz_score is not None else 0.0

        llm_norm = min(llm_interaction_count / 10.0, 1.0) * 100.0
        duration_norm = min(study_duration_minutes / 30.0, 1.0) * 100.0

        score = (
            0.40 * quiz_score
            + 0.30 * progress
            + 0.20 * llm_norm
            + 0.10 * duration_norm
        )

        # 后处理：满分测验 + 满进度时保证不低于 90
        if quiz_score >= 100 and progress >= 100:
            score = max(score, 90.0)

        # clamp 至 [0, 100] 并保留两位小数
        return round(max(0.0, min(100.0, score)), 2)

    def calculate_overall_mastery(self, nodes: list[KnowledgeNodeScore]) -> float:
        """
        计算所有知识节点 mastery_score 的算术平均值。

        空列表返回 0.0，结果保留两位小数。
        """
        if not nodes:
            return 0.0
        total = sum(node.mastery_score for node in nodes)
        return round(total / len(nodes), 2)

    def recalculate_profile(self, profile: TwinProfile) -> TwinProfile:
        """
        重新计算 TwinProfile 中所有节点的 mastery_score 及 overall_mastery。

        不修改原对象，返回更新后的新 TwinProfile 实例。
        """
        updated_nodes = []
        for node in profile.knowledge_nodes:
            new_mastery = self.calculate_mastery(
                quiz_score=node.quiz_score,
                progress=node.progress,
                llm_interaction_count=node.llm_interaction_count,
                study_duration_minutes=node.study_duration_minutes,
            )
            updated_nodes.append(node.model_copy(update={"mastery_score": new_mastery}))

        new_overall = self.calculate_overall_mastery(updated_nodes)

        return profile.model_copy(
            update={
                "knowledge_nodes": updated_nodes,
                "overall_mastery": new_overall,
            }
        )
