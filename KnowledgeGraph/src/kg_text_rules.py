from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from KnowledgeGraph.src.course_profile import CourseProfile


DEFAULT_NOISE_KEYWORDS = {
    "例如",
    "比如",
    "本节课",
    "如图所示",
    "纯文本可直接复制",
    "无多余格式",
}

DEFAULT_NOISE_MARKERS = {
    "我们",
    "你们",
    "他们",
    "同学",
    "老师",
    "分钟",
    "图片",
    "此外",
    "同时",
}

SENTENCE_MARKERS = (
    "指出",
    "转而",
    "放弃",
    "渴求",
    "关注",
    "我们将",
    "我们会",
    "我是",
    "本节课",
    "此外",
    "对于",
    "同时",
    "其中",
    "因此",
    "所以",
)

PREFIX_STOPWORDS = ("是", "对", "由", "从", "将", "把", "在", "以", "对于", "此外", "作为", "为", "无需", "仅", "的", "我")


def normalize_token(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip("，。；：!?！？()（）[]【】\"'、")
    return value


def normalize_term(text: str) -> str:
    token = normalize_token(text)
    if not token:
        return ""
    token = re.sub(r"[（(][^）)]*[）)]", "", token)
    token = re.sub(r"[（(].*$", "", token)
    token = re.sub(r"\s+", " ", token).strip()
    return token


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def looks_like_identifier_fragment(text: str) -> bool:
    token = normalize_token(text).lower()
    if not token:
        return False
    if re.fullmatch(r"[a-z]\d+", token):
        return True
    if re.fullmatch(r"[a-z]{1,3}\d{1,3}", token):
        return True
    if re.fullmatch(r"\d+[a-z]{1,2}", token):
        return True
    return False


def looks_like_measure_fragment(text: str, unit_terms: set[str] | None = None) -> bool:
    token = normalize_token(text).lower()
    if not token:
        return False

    units = set(unit_terms or set())
    units.update({"条", "个", "次", "次方", "字节", "记录", "箱", "kb", "mb", "gb", "tb", "分钟"})

    if re.fullmatch(r"\d+(\.\d+)?", token):
        return True
    if re.fullmatch(r"\d+(\.\d+)?([a-z]{1,4}|次|次方|字节|条|个|箱|记录)", token):
        return True
    if re.fullmatch(r"[条个次箱]\w{0,4}", token):
        return True
    if any(unit in token for unit in units) and re.search(r"\d|次方|记录|箱|条|个", token):
        return True
    return False


def looks_like_sentence_fragment(text: str, discourse_markers: set[str] | None = None) -> bool:
    token = normalize_token(text)
    if not token:
        return False
    lowered = token.lower()

    if any(ch in token for ch in "，。！？!?；;“”\""):
        return True
    if len(token) >= 18 and not re.search(r"[A-Za-z]{4,}", token):
        return True
    if token.startswith(PREFIX_STOPWORDS):
        return True
    if token.endswith("等") and len(token) >= 4:
        return True
    if token.endswith(("高", "低")) and "度" in token:
        return True
    if token.count("的") >= 2:
        return True
    if len(token) >= 8 and "的" in token and not re.search(r"[A-Za-z]{3,}", token):
        return True
    if any(pattern in token for pattern in ("为代表的", "顺序为", "作为属性", "最大的转变", "一书中")):
        return True

    markers = set(discourse_markers or set())
    markers.update(SENTENCE_MARKERS)
    if any(marker.lower() in lowered for marker in markers if marker):
        return True
    return False


def is_noise_keyword(text: str, profile: "CourseProfile | None" = None) -> bool:
    token = normalize_token(text).lower()
    if not token:
        return True
    if token.isdigit():
        return True
    if len(token) <= 1:
        return True
    if token in {item.lower() for item in DEFAULT_NOISE_KEYWORDS}:
        return True
    if any(marker.lower() in token for marker in DEFAULT_NOISE_MARKERS):
        return True
    if profile:
        if token in profile.hard_block_terms:
            return True
        if token in profile.discourse_markers:
            return True
        if looks_like_measure_fragment(token, profile.unit_terms):
            return True
    return False


@dataclass
class CandidateAnalysis:
    token: str
    score: float
    rejected: bool
    reject_reason: str
    flags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "score": round(self.score, 3),
            "rejected": self.rejected,
            "reject_reason": self.reject_reason,
            "flags": self.flags,
        }


def analyze_candidate(
    text: str,
    profile: "CourseProfile",
    *,
    evidence_count: int = 1,
    occurs_as_subject: bool = False,
    occurs_as_object: bool = False,
) -> CandidateAnalysis:
    token = normalize_term(text)
    flags: list[str] = []
    if not token:
        return CandidateAnalysis(token="", score=0.0, rejected=True, reject_reason="empty", flags=["empty"])

    lowered = token.lower()
    score = 0.0
    reject_reason = ""

    if lowered in profile.whitelist_terms:
        score = max(3.0, profile.concept_min_score + 0.5)
        return CandidateAnalysis(token=token, score=score, rejected=False, reject_reason="", flags=["whitelist"])

    if lowered in profile.hard_block_terms:
        return CandidateAnalysis(
            token=token,
            score=-1.0,
            rejected=True,
            reject_reason="hard_block_term",
            flags=["hard_block_term"],
        )

    if len(token) < profile.min_term_length or len(token) > profile.max_term_length:
        return CandidateAnalysis(
            token=token,
            score=-1.0,
            rejected=True,
            reject_reason="length_out_of_range",
            flags=["length_out_of_range"],
        )

    if token.isdigit():
        return CandidateAnalysis(
            token=token,
            score=-1.0,
            rejected=True,
            reject_reason="pure_number",
            flags=["pure_number"],
        )

    if looks_like_identifier_fragment(token):
        return CandidateAnalysis(
            token=token,
            score=-0.8,
            rejected=True,
            reject_reason="identifier_fragment",
            flags=["identifier_fragment"],
        )

    if looks_like_measure_fragment(token, profile.unit_terms):
        return CandidateAnalysis(
            token=token,
            score=-0.8,
            rejected=True,
            reject_reason="measure_fragment",
            flags=["measure_fragment"],
        )

    if looks_like_sentence_fragment(token, profile.discourse_markers):
        return CandidateAnalysis(
            token=token,
            score=-0.8,
            rejected=True,
            reject_reason="sentence_fragment",
            flags=["sentence_fragment"],
        )

    if lowered in profile.abstract_terms:
        return CandidateAnalysis(
            token=token,
            score=-0.6,
            rejected=True,
            reject_reason="abstract_term",
            flags=["abstract_term"],
        )

    if lowered in profile.action_terms:
        return CandidateAnalysis(
            token=token,
            score=-0.6,
            rejected=True,
            reject_reason="action_term",
            flags=["action_term"],
        )

    if any(action in lowered for action in profile.action_terms if len(action) >= 2) and len(token) >= 4:
        return CandidateAnalysis(
            token=token,
            score=-0.6,
            rejected=True,
            reject_reason="action_phrase",
            flags=["action_phrase"],
        )

    if lowered in profile.relation_terms:
        return CandidateAnalysis(
            token=token,
            score=-0.4,
            rejected=True,
            reject_reason="relation_term",
            flags=["relation_term"],
        )
    if lowered in {"related_to", "depends_on", "has_child"} or lowered.endswith("_to"):
        return CandidateAnalysis(
            token=token,
            score=-0.4,
            rejected=True,
            reject_reason="relation_term",
            flags=["relation_term_pattern"],
        )

    if len(token) <= 6 and token.endswith(("时代", "转变")):
        return CandidateAnalysis(
            token=token,
            score=-0.5,
            rejected=True,
            reject_reason="abstract_topic_phrase",
            flags=["abstract_topic_phrase"],
        )

    if lowered in profile.weak_block_terms:
        flags.append("weak_block_term")
        score -= 0.5

    if is_noise_keyword(token, profile):
        flags.append("noise_keyword")
        score -= 0.5

    score += min(1.8, 0.6 + 0.35 * max(0, evidence_count - 1))
    if occurs_as_subject:
        score += 0.4
        flags.append("subject_role")
    if occurs_as_object:
        score += 0.4
        flags.append("object_role")
    if profile.contains_domain_term(lowered):
        score += 0.8
        flags.append("domain_anchor")
    else:
        score -= 0.2
        flags.append("no_domain_anchor")
        if evidence_count <= 1:
            score -= 0.15
            flags.append("low_evidence")
    if contains_cjk(token) and len(token) >= 3:
        score += 0.25
        flags.append("cjk_term")
    if re.search(r"[A-Za-z]{3,}", token):
        score += 0.2
        flags.append("latin_term")

    rejected = score < profile.concept_min_score
    if rejected:
        reject_reason = "score_below_threshold"
    return CandidateAnalysis(
        token=token,
        score=score,
        rejected=rejected,
        reject_reason=reject_reason,
        flags=flags,
    )


def is_generic_chapter_name(text: str) -> bool:
    name = normalize_token(text)
    if not name:
        return True
    if re.fullmatch(r"第[一二三四五六七八九十百0-9]+章", name):
        return True
    if re.fullmatch(r"chapter[_\-\s]?\d+", name.lower()):
        return True
    if name.lower() in {"章节", "课程", "chapter", "topic"}:
        return True
    return False


def is_generic_text(text: str) -> bool:
    value = normalize_token(text).lower()
    if not value:
        return True
    generic_markers = (
        "知识组织节点",
        "关键知识点",
        "完整学习路径",
        "用于连接",
        "基础概念",
    )
    return any(marker in value for marker in generic_markers)
