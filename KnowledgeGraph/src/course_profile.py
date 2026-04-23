from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _to_lower_set(values: list[str] | set[str] | tuple[str, ...] | None) -> set[str]:
    if not values:
        return set()
    return {str(item).strip().lower() for item in values if str(item).strip()}


@dataclass
class CourseProfile:
    """Configurable profile for domain-aware concept quality control."""

    profile_name: str = "generic"
    domain_terms: set[str] = field(default_factory=set)
    whitelist_terms: set[str] = field(default_factory=set)
    hard_block_terms: set[str] = field(default_factory=set)
    weak_block_terms: set[str] = field(default_factory=set)
    abstract_terms: set[str] = field(default_factory=set)
    discourse_markers: set[str] = field(default_factory=set)
    action_terms: set[str] = field(default_factory=set)
    relation_terms: set[str] = field(default_factory=set)
    unit_terms: set[str] = field(default_factory=set)
    chapter_stopwords: set[str] = field(default_factory=set)
    concept_min_score: float = 1.9
    keyword_min_score: float = 1.2
    max_term_length: int = 36
    min_term_length: int = 2

    @classmethod
    def default(cls) -> "CourseProfile":
        return cls(
            profile_name="generic-default",
            domain_terms={
                "data",
                "dataset",
                "model",
                "algorithm",
                "feature",
                "nosql",
                "hadoop",
                "spark",
                "mllib",
                "hdfs",
                "mapreduce",
                "graph",
                "recommend",
                "矩阵",
                "分解",
                "聚类",
                "回归",
                "分类",
                "特征",
                "向量",
                "维度",
                "数据",
                "模型",
                "算法",
                "存储",
                "计算",
                "推荐",
                "图",
                "网络",
                "流计算",
            },
            abstract_terms={
                "用户",
                "算法",
                "模型",
                "系统",
                "阶段",
                "方法",
                "文档",
                "组合",
                "定理",
                "过程",
                "结果",
                "结构",
                "关系",
                "内容",
                "东西",
                "事情",
                "对象",
                "部分",
                "模块",
                "组件",
                "数据时代",
            },
            discourse_markers={
                "此外",
                "同时",
                "其中",
                "对于",
                "然后",
                "首先",
                "其次",
                "最后",
                "因此",
                "所以",
                "我们",
                "你们",
                "他们",
                "指出",
                "转而",
                "放弃",
                "from",
                "then",
                "therefore",
                "however",
            },
            action_terms={
                "使用",
                "攻击",
                "加载",
                "爬取",
                "顺序",
                "插入",
                "更新",
                "删除",
                "计算",
                "执行",
                "出发",
                "作为",
                "无需",
                "仅",
                "关注",
                "渴求",
            },
            relation_terms={
                "相关",
                "关联",
                "包含",
                "组成",
                "用于",
                "适用",
                "支持",
                "依赖",
                "比较",
                "related",
                "contains",
                "depend",
            },
            unit_terms={
                "个",
                "条",
                "次",
                "次方",
                "字节",
                "kb",
                "mb",
                "gb",
                "tb",
                "秒",
                "分钟",
                "小时",
                "记录",
                "箱",
            },
            chapter_stopwords={"课程", "讲稿", "介绍", "概述", "章节", "第", "chapter"},
            concept_min_score=1.9,
            keyword_min_score=1.2,
            max_term_length=36,
            min_term_length=2,
        )

    @classmethod
    def from_path(cls, path: Path | str | None) -> "CourseProfile":
        profile = cls.default()
        if path is None:
            return profile

        file_path = Path(path)
        if not file_path.exists():
            return profile

        payload = _load_yaml_payload(file_path)
        if not isinstance(payload, dict):
            return profile

        profile.profile_name = str(payload.get("profile_name") or profile.profile_name)
        profile.domain_terms = _to_lower_set(payload.get("domain_terms")) or profile.domain_terms
        profile.whitelist_terms = _to_lower_set(payload.get("whitelist_terms"))
        profile.hard_block_terms = _to_lower_set(payload.get("hard_block_terms"))
        profile.weak_block_terms = _to_lower_set(payload.get("weak_block_terms"))
        profile.abstract_terms = _to_lower_set(payload.get("abstract_terms")) or profile.abstract_terms
        profile.discourse_markers = _to_lower_set(payload.get("discourse_markers")) or profile.discourse_markers
        profile.action_terms = _to_lower_set(payload.get("action_terms")) or profile.action_terms
        profile.relation_terms = _to_lower_set(payload.get("relation_terms")) or profile.relation_terms
        profile.unit_terms = _to_lower_set(payload.get("unit_terms")) or profile.unit_terms
        profile.chapter_stopwords = _to_lower_set(payload.get("chapter_stopwords")) or profile.chapter_stopwords

        profile.concept_min_score = _to_float(payload.get("concept_min_score"), profile.concept_min_score)
        profile.keyword_min_score = _to_float(payload.get("keyword_min_score"), profile.keyword_min_score)
        profile.max_term_length = int(payload.get("max_term_length", profile.max_term_length))
        profile.min_term_length = int(payload.get("min_term_length", profile.min_term_length))
        return profile

    def contains_domain_term(self, text: str) -> bool:
        token = (text or "").lower()
        if not token:
            return False
        if token in self.domain_terms:
            return True
        return any(term in token for term in self.domain_terms if len(term) >= 3)

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "domain_terms_count": len(self.domain_terms),
            "whitelist_terms_count": len(self.whitelist_terms),
            "hard_block_terms_count": len(self.hard_block_terms),
            "weak_block_terms_count": len(self.weak_block_terms),
            "concept_min_score": self.concept_min_score,
            "keyword_min_score": self.keyword_min_score,
            "min_term_length": self.min_term_length,
            "max_term_length": self.max_term_length,
        }


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_yaml_payload(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = yaml.safe_load(content)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
