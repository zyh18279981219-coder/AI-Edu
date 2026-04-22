from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


_EN_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+\-]{1,31}", re.IGNORECASE)
_ZH_CHUNK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")

_NOISE_TOKENS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "you",
    "our",
    "ours",
    "课程",
    "学习",
    "知识",
    "内容",
    "目标",
    "介绍",
    "例如",
    "此外",
    "其中",
    "我们",
    "你们",
    "他们",
    "本节课",
    "图示",
    "如图",
    "分钟",
}


def normalize_text(text: str) -> str:
    value = str(text or "").strip().lower()
    if not value:
        return ""
    value = value.replace("\u3000", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_key(text: str) -> str:
    value = normalize_text(text)
    if not value:
        return ""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value)


def tokenize(text: str) -> set[str]:
    value = normalize_text(text)
    if not value:
        return set()

    tokens: set[str] = set()

    for token in _EN_TOKEN_RE.findall(value):
        lowered = token.lower()
        if len(lowered) < 2:
            continue
        if lowered in _NOISE_TOKENS:
            continue
        tokens.add(lowered)

    for chunk in _ZH_CHUNK_RE.findall(value):
        token = chunk.strip()
        if len(token) < 2:
            continue
        if token not in _NOISE_TOKENS:
            tokens.add(token)
        for ngram_size in (2, 3):
            if len(token) < ngram_size:
                continue
            for index in range(0, len(token) - ngram_size + 1):
                ngram = token[index : index + ngram_size]
                if ngram not in _NOISE_TOKENS:
                    tokens.add(ngram)

    return tokens


def token_overlap_score(lhs: set[str], rhs: set[str]) -> float:
    if not lhs or not rhs:
        return 0.0
    intersection_size = len(lhs.intersection(rhs))
    if intersection_size == 0:
        return 0.0
    return 2.0 * intersection_size / (len(lhs) + len(rhs))


def stable_index(key: str, size: int) -> int:
    if size <= 0:
        return 0
    digest = hashlib.md5(str(key).encode("utf-8")).hexdigest()
    return int(digest, 16) % size


def rebuild_resource_refs(resources: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for resource in resources:
        ref = str(resource.get("path") or resource.get("url") or "").strip()
        if not ref or ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return refs


def build_concept_context(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = graph.get("nodes", []) or []
    edges = graph.get("edges", []) or []

    node_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        node_id = str(node.get("node_id", "")).strip()
        if node_id:
            node_by_id[node_id] = node

    parent_map: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if str(edge.get("relation_type", "")).upper() != "HAS_CHILD":
            continue
        source = str(edge.get("source_node_id", "")).strip()
        target = str(edge.get("target_node_id", "")).strip()
        if source and target:
            parent_map[target].add(source)

    contexts: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if str(node.get("node_type", "")) != "concept":
            continue

        concept_id = str(node.get("node_id", "")).strip()
        if not concept_id:
            continue

        topic_candidates = [
            parent_id
            for parent_id in sorted(parent_map.get(concept_id, set()))
            if str(node_by_id.get(parent_id, {}).get("node_type", "")) == "topic"
        ]
        topic_id = topic_candidates[0] if topic_candidates else ""
        topic_name = str(node_by_id.get(topic_id, {}).get("name", "")).strip() if topic_id else ""

        chapter_id = ""
        chapter_name = ""
        if topic_id:
            chapter_candidates = [
                parent_id
                for parent_id in sorted(parent_map.get(topic_id, set()))
                if str(node_by_id.get(parent_id, {}).get("node_type", "")) == "chapter"
            ]
            if chapter_candidates:
                chapter_id = chapter_candidates[0]
            else:
                fallback_chapter = str(
                    node_by_id.get(topic_id, {}).get("parent_chapter_id", "")
                ).strip()
                if fallback_chapter and fallback_chapter in node_by_id:
                    chapter_id = fallback_chapter
            if chapter_id:
                chapter_name = str(node_by_id.get(chapter_id, {}).get("name", "")).strip()

        query_parts = [
            str(node.get("name", "")),
            str(node.get("description", "")),
            str(node.get("learning_objective", "")),
            " ".join(str(item) for item in (node.get("keywords") or [])),
            " ".join(str(item) for item in (node.get("source_refs") or [])),
            topic_name,
            chapter_name,
        ]
        query_text = " ".join(part for part in query_parts if part).strip()
        contexts[concept_id] = {
            "concept_id": concept_id,
            "concept_name": str(node.get("name", "")).strip(),
            "concept_key": normalize_key(str(node.get("name", ""))),
            "topic_id": topic_id,
            "topic_name": topic_name,
            "topic_key": normalize_key(topic_name),
            "chapter_id": chapter_id,
            "chapter_name": chapter_name,
            "chapter_key": normalize_key(chapter_name),
            "query_text": query_text,
            "query_tokens": tokenize(query_text),
        }

    return contexts


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _normalize_path(path: str) -> str:
    return str(path or "").replace("\\", "/").strip()


def _is_video_resource(path: str) -> bool:
    lowered = path.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _is_book_resource(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith(".pdf"):
        return True
    return "/book/" in lowered


def load_legacy_leaf_entries(path: Path | str | None) -> list[dict[str, Any]]:
    if path is None:
        return []

    file_path = Path(path)
    if not file_path.exists():
        return []

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    children = payload.get("children", []) if isinstance(payload, dict) else []
    if not isinstance(children, list):
        return []

    entries: list[dict[str, Any]] = []
    for chapter in children:
        chapter_name = str(chapter.get("name", "")).strip()
        topics = chapter.get("grandchildren", []) or []
        if not isinstance(topics, list):
            continue

        for topic in topics:
            topic_name = str(topic.get("name", "")).strip()
            concepts = topic.get("great-grandchildren", []) or []
            if not isinstance(concepts, list):
                continue

            for concept in concepts:
                concept_name = str(concept.get("name", "")).strip()
                resources = _as_list(concept.get("resource_path"))
                normalized_resources = [_normalize_path(item) for item in resources if item]
                books = [item for item in normalized_resources if _is_book_resource(item)]
                videos = [item for item in normalized_resources if _is_video_resource(item)]
                if not concept_name:
                    continue
                entries.append(
                    {
                        "name": concept_name,
                        "name_key": normalize_key(concept_name),
                        "name_tokens": tokenize(concept_name),
                        "topic_name": topic_name,
                        "topic_key": normalize_key(topic_name),
                        "chapter_name": chapter_name,
                        "chapter_key": normalize_key(chapter_name),
                        "books": books,
                        "videos": videos,
                    }
                )
    return entries
