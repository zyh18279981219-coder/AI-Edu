"""
DigitalTwinModule/models.py
核心数据模型定义（Pydantic v2）及运行时目录初始化工具函数。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class KnowledgeNodeScore(BaseModel):
    """单个知识节点的多维度评分数据。"""

    model_config = {"extra": "ignore"}

    node_id: str
    node_path: list[str] = []
    quiz_score: Optional[float] = None
    progress: float
    study_duration_minutes: float
    llm_interaction_count: int
    mastery_score: float


class TwinProfile(BaseModel):
    """学生数字孪生画像快照。"""

    model_config = {"extra": "ignore"}

    username: str
    last_updated: str
    overall_mastery: float = 0.0
    knowledge_nodes: list[KnowledgeNodeScore] = []


class TrendPoint(BaseModel):
    """单日掌握度趋势数据点。"""

    model_config = {"extra": "ignore"}

    date: str
    overall_mastery: float


class Resource(BaseModel):
    """推荐学习资源条目。"""

    model_config = {"extra": "ignore"}

    type: str
    title: str
    url: str
    source: str


class WeakNode(BaseModel):
    """薄弱知识节点及其推荐资源。"""

    model_config = {"extra": "ignore"}

    node_id: str
    mastery_score: float
    priority: int                  # 按掌握度升序的优先级
    llm_priority: Optional[int] = None   # LLM 按依赖关系重排后的优先级
    resources: list[Resource] = []


class LearningPath(BaseModel):
    """学生个性化学习路径。"""

    model_config = {"extra": "ignore"}

    username: str
    generated_at: str
    status: str
    weak_nodes: list[WeakNode] = []
    llm_advice: str = ""          # LLM 生成的个性化学习建议
    llm_order_reason: str = ""    # LLM 对学习顺序的解释


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------

class TwinProfileParseError(ValueError):
    """Twin_Profile 解析失败时抛出，包含缺失或非法字段的描述信息。"""


# ---------------------------------------------------------------------------
# 运行时目录初始化
# ---------------------------------------------------------------------------

_DATA_DIRS = [
    Path("data/digital_twins"),
    Path("data/digital_twins/history"),
    Path("data/learning_plans"),
]


def ensure_data_dirs() -> None:
    """在运行时自动创建所需的数据目录（若已存在则跳过）。"""
    for directory in _DATA_DIRS:
        directory.mkdir(parents=True, exist_ok=True)
