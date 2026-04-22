from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from KnowledgeGraph.src.course_profile import CourseProfile
from KnowledgeGraph.src.kg_text_rules import (
    analyze_candidate,
    is_generic_chapter_name,
    is_noise_keyword,
    normalize_term,
    normalize_token,
)


class HierarchyBuilder:
    """Build pedagogical hierarchy with generic concept quality governance."""

    def __init__(
        self,
        logger=None,
        max_concepts_per_topic: int = 8,
        profile_path: Path | str | None = None,
        course_profile: CourseProfile | None = None,
    ) -> None:
        self.logger = logger
        self.max_concepts_per_topic = max(4, max_concepts_per_topic)
        self.course_profile = course_profile or CourseProfile.from_path(profile_path)

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    @staticmethod
    def _hash_id(prefix: str, value: str) -> str:
        digest = hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:12]
        return f"{prefix}_{digest}"

    @staticmethod
    def _infer_relation_type(predicate: str) -> str:
        p = normalize_term(predicate).lower()
        if any(token in p for token in ["先修", "依赖", "前提", "prerequisite", "depend"]):
            return "PREREQUISITE"
        if any(token in p for token in ["包含", "包括", "组成", "contains", "include"]):
            return "INCLUDES"
        if any(token in p for token in ["用于", "应用", "适用", "applies to", "apply"]):
            return "APPLIES_TO"
        if any(token in p for token in ["使用", "基于", "支持", "实现", "调用", "uses"]):
            return "USES"
        if any(token in p for token in ["比较", "对比", "compare"]):
            return "COMPARES_WITH"
        return "RELATED_TO"

    @staticmethod
    def _chapter_id(doc: dict[str, Any]) -> str:
        lesson_no = doc.get("lesson_no")
        if isinstance(lesson_no, int) and lesson_no > 0:
            return f"chapter_{lesson_no:02d}"
        return "chapter_misc"

    @staticmethod
    def _topic_name(doc: dict[str, Any]) -> str:
        topic = normalize_token(str(doc.get("topic") or ""))
        title = normalize_token(str(doc.get("title") or ""))
        if topic and topic not in {"unknown", "Unknown"}:
            return topic
        if title:
            return title
        source_file = normalize_token(str(doc.get("source_file") or ""))
        if source_file:
            return Path(source_file).stem
        return str(doc.get("doc_id") or "未命名主题")

    @staticmethod
    def _sanitize_topic_text(text: str) -> str:
        value = normalize_token(text)
        value = re.sub(r"\bBDA\b", " ", value, flags=re.IGNORECASE)
        value = re.sub(r"\b\d+\s*-\s*\d+\b", " ", value)
        value = re.sub(r"(课程讲稿|讲稿|课件|第\s*\d+\s*讲)", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _extract_terms(text: str) -> list[str]:
        value = normalize_token(text)
        if not value:
            return []
        tokens = re.findall(r"[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9_+\-]{1,40}", value)
        return [normalize_term(token) for token in tokens if normalize_term(token)]

    def _pick_keywords(self, candidates: list[str], limit: int = 8) -> list[str]:
        scored: list[tuple[str, float]] = []
        seen: set[str] = set()
        for token in candidates:
            norm = normalize_term(token)
            key = norm.lower()
            if not norm or key in seen:
                continue
            seen.add(key)
            analysis = analyze_candidate(norm, self.course_profile, evidence_count=1)
            if analysis.rejected and analysis.reject_reason in {
                "hard_block_term",
                "sentence_fragment",
                "measure_fragment",
                "identifier_fragment",
                "abstract_term",
                "action_term",
                "relation_term",
            }:
                continue
            if is_noise_keyword(norm, self.course_profile):
                continue
            score = analysis.score
            if self.course_profile.contains_domain_term(norm):
                score += 0.4
            if score >= self.course_profile.keyword_min_score:
                scored.append((norm, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [token for token, _ in scored[:limit]]

    def _collect_concept_candidates(
        self,
        doc: dict[str, Any],
        triples_by_doc: dict[str, list[dict[str, Any]]],
        audit_rejected: list[dict[str, Any]],
    ) -> list[tuple[str, float]]:
        doc_id = str(doc.get("doc_id") or "")
        triples = triples_by_doc.get(doc_id, [])

        candidate_map: dict[str, dict[str, Any]] = {}

        def add_candidate(term: str, source: str, role: str = "") -> None:
            norm = normalize_term(term)
            if not norm:
                return
            key = norm.lower()
            entry = candidate_map.setdefault(
                key,
                {
                    "term": norm,
                    "evidence_count": 0,
                    "subject_hits": 0,
                    "object_hits": 0,
                    "sources": set(),
                },
            )
            entry["evidence_count"] += 1
            entry["sources"].add(source)
            if role == "subject":
                entry["subject_hits"] += 1
            if role == "object":
                entry["object_hits"] += 1

        for triple in triples:
            add_candidate(str(triple.get("subject", "")), source="triple_subject", role="subject")
            add_candidate(str(triple.get("object", "")), source="triple_object", role="object")

        topic_text = self._sanitize_topic_text(self._topic_name(doc))
        title_text = self._sanitize_topic_text(str(doc.get("title") or ""))
        for token in self._extract_terms(topic_text):
            add_candidate(token, source="topic")
        for token in self._extract_terms(title_text):
            add_candidate(token, source="title")
        for keyword in doc.get("keywords", []) or []:
            add_candidate(str(keyword), source="keyword")

        accepted: list[tuple[str, float]] = []
        for entry in candidate_map.values():
            term = str(entry["term"])
            analysis = analyze_candidate(
                term,
                self.course_profile,
                evidence_count=int(entry["evidence_count"]),
                occurs_as_subject=int(entry["subject_hits"]) > 0,
                occurs_as_object=int(entry["object_hits"]) > 0,
            )
            if analysis.rejected:
                audit_rejected.append(
                    {
                        "doc_id": doc_id,
                        "source_file": str(doc.get("source_file") or ""),
                        "term": term,
                        "score": round(analysis.score, 3),
                        "reject_reason": analysis.reject_reason,
                        "flags": analysis.flags,
                        "evidence_count": entry["evidence_count"],
                        "sources": sorted(entry["sources"]),
                    }
                )
                continue
            accepted.append((analysis.token, analysis.score))

        accepted.sort(key=lambda item: item[1], reverse=True)
        return accepted[: self.max_concepts_per_topic]

    def _compose_chapter_name(self, ranked_terms: list[str], fallback_topics: list[str]) -> str:
        filtered = []
        for term in ranked_terms:
            token = normalize_term(term)
            if not token:
                continue
            if token.lower().endswith("_to") or token.lower() in {"related_to", "depends_on", "has_child"}:
                continue
            if token.lower() in self.course_profile.relation_terms:
                continue
            if token.lower() in self.course_profile.action_terms:
                continue
            if token.lower() in self.course_profile.abstract_terms:
                continue
            if token.lower() in self.course_profile.hard_block_terms:
                continue
            if token.lower() in self.course_profile.chapter_stopwords:
                continue
            if is_generic_chapter_name(token):
                continue
            filtered.append(token)

        if len(filtered) >= 2:
            first, second = filtered[0], filtered[1]
            if first in second:
                return f"{second}专题"
            if second in first:
                return f"{first}专题"
            return f"{first}与{second}"
        if len(filtered) == 1:
            return f"{filtered[0]}专题"

        for topic in fallback_topics:
            text = self._sanitize_topic_text(topic)
            terms = [term for term in self._extract_terms(text) if term.lower() not in self.course_profile.chapter_stopwords]
            if len(terms) >= 2:
                return f"{terms[0]}与{terms[1]}"
            if len(terms) == 1:
                return f"{terms[0]}专题"
            if text and not is_generic_chapter_name(text):
                return text
        return "数据分析核心专题"

    def _chapter_profiles(
        self,
        docs: list[dict[str, Any]],
        triples_by_doc: dict[str, list[dict[str, Any]]],
        accepted_terms_by_doc: dict[str, list[tuple[str, float]]],
    ) -> dict[str, dict[str, Any]]:
        grouped_docs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for doc in docs:
            grouped_docs[self._chapter_id(doc)].append(doc)

        profiles: dict[str, dict[str, Any]] = {}
        for chapter_id, chapter_docs in grouped_docs.items():
            term_counter: Counter[str] = Counter()
            fallback_topics: list[str] = []
            for doc in chapter_docs:
                doc_id = str(doc.get("doc_id") or "")
                fallback_topics.append(self._topic_name(doc))
                for term, score in accepted_terms_by_doc.get(doc_id, []):
                    term_counter[term] += max(1, int(score * 2))
                for triple in triples_by_doc.get(doc_id, []):
                    relation = normalize_term(str(triple.get("predicate", "")))
                    analysis = analyze_candidate(relation, self.course_profile, evidence_count=2)
                    if (
                        relation
                        and len(relation) <= 10
                        and not is_noise_keyword(relation, self.course_profile)
                        and not relation.lower().endswith("_to")
                        and not analysis.rejected
                    ):
                        term_counter[relation] += 1

            ranked_terms = [term for term, _ in term_counter.most_common(6)]
            chapter_name = self._compose_chapter_name(ranked_terms, fallback_topics)
            chapter_keywords = self._pick_keywords([chapter_name, *ranked_terms], limit=8)

            if ranked_terms:
                focus = "、".join(ranked_terms[:3])
                description = f"{chapter_name}围绕{focus}构建知识结构，重点覆盖核心定义、关键方法和典型应用。"
                learning_objective = f"学习后应能解释{focus}之间的联系，并据此完成相关数据分析任务的方案设计。"
            else:
                description = f"{chapter_name}用于组织课程相关主题，形成可复用的知识学习路径。"
                learning_objective = f"学习后应能梳理{chapter_name}内主题关系，并定位关键知识点。"

            profiles[chapter_id] = {
                "chapter_id": chapter_id,
                "name": chapter_name,
                "depth": 0,
                "description": description,
                "learning_objective": learning_objective,
                "keywords": chapter_keywords,
                "source_refs": sorted(
                    {str(doc.get("source_file") or "") for doc in chapter_docs if doc.get("source_file")}
                ),
                "top_terms": ranked_terms,
            }
        return profiles

    def _topic_texts(
        self,
        topic_name: str,
        chapter_name: str,
        concept_names: list[str],
        local_triples: list[dict[str, Any]],
    ) -> tuple[str, str, list[str]]:
        concept_keywords = self._pick_keywords(concept_names, limit=6)
        predicate_counter: Counter[str] = Counter()
        for triple in local_triples:
            predicate = normalize_term(str(triple.get("predicate", "")))
            if predicate and len(predicate) <= 10 and not is_noise_keyword(predicate, self.course_profile):
                predicate_counter[predicate] += 1
        relations = [item for item, _ in predicate_counter.most_common(2)]

        if concept_keywords:
            focus = "、".join(concept_keywords[:3])
            if relations:
                rel_text = "、".join(relations)
                description = f"主题“{topic_name}”以{focus}为核心，通过{rel_text}等关系组织知识。"
                objective = f"学习后应能围绕{focus}建立概念联系，并理解其在“{chapter_name}”中的作用。"
            else:
                description = f"主题“{topic_name}”聚焦{focus}，强调概念理解到方法实践的衔接。"
                objective = f"学习后应能解释{focus}的核心原理，并完成基础应用分析。"
        else:
            description = f"主题“{topic_name}”用于连接“{chapter_name}”中的关键知识单元。"
            objective = f"学习后应能识别“{topic_name}”在章节知识链路中的位置。"

        topic_keywords = self._pick_keywords([topic_name, *concept_keywords, *relations], limit=8)
        return description, objective, topic_keywords

    def _concept_texts(
        self,
        concept_name: str,
        topic_name: str,
        local_triples: list[dict[str, Any]],
    ) -> tuple[str, str, list[str]]:
        lowered = concept_name.lower()
        neighbors: Counter[str] = Counter()
        relations: Counter[str] = Counter()
        for triple in local_triples:
            subject = normalize_term(str(triple.get("subject", "")))
            predicate = normalize_term(str(triple.get("predicate", "")))
            obj = normalize_term(str(triple.get("object", "")))
            if subject.lower() == lowered and obj:
                neighbors[obj] += 1
                if predicate:
                    relations[predicate] += 1
            elif obj.lower() == lowered and subject:
                neighbors[subject] += 1
                if predicate:
                    relations[predicate] += 1

        top_neighbors = [item for item, _ in neighbors.most_common(2) if item]
        top_relations = [item for item, _ in relations.most_common(2) if item]
        concept_keywords = self._pick_keywords([concept_name, *top_neighbors, *top_relations], limit=6)

        if top_neighbors and top_relations:
            neighbors_text = "、".join(top_neighbors)
            relation_text = "、".join(top_relations)
            description = f"在主题“{topic_name}”中，{concept_name}与{neighbors_text}通过{relation_text}形成关键知识关联。"
            objective = f"学习后应能解释{concept_name}与{neighbors_text}之间的关系，并据此开展分析。"
        elif top_neighbors:
            neighbors_text = "、".join(top_neighbors)
            description = f"{concept_name}在主题“{topic_name}”中与{neighbors_text}紧密相关，是理解流程的重要节点。"
            objective = f"学习后应能说明{concept_name}与{neighbors_text}的联系，并在案例中正确应用。"
        else:
            description = f"{concept_name}是主题“{topic_name}”中的关键概念，用于刻画核心对象与方法边界。"
            objective = f"学习后应能准确定义{concept_name}并在相关场景中完成基础应用。"
        return description, objective, concept_keywords

    def build(
        self,
        triples: list[dict[str, Any]],
        documents: list[dict[str, Any]] | None = None,
        *,
        course_id: str = "course_big_data",
        course_name: str = "大数据分析",
    ) -> dict[str, Any]:
        docs = documents or []
        triples_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for triple in triples:
            triples_by_doc[str(triple.get("doc_id") or "")].append(triple)

        audit_rejected: list[dict[str, Any]] = []
        accepted_terms_by_doc: dict[str, list[tuple[str, float]]] = {}
        for doc in docs:
            doc_id = str(doc.get("doc_id") or "")
            accepted_terms_by_doc[doc_id] = self._collect_concept_candidates(doc, triples_by_doc, audit_rejected)

        chapter_profiles = self._chapter_profiles(docs, triples_by_doc, accepted_terms_by_doc)

        nodes: list[dict[str, Any]] = [
            {
                "node_id": course_id,
                "name": course_name,
                "node_type": "course",
                "depth": -1,
                "description": "本课程覆盖数据采集、存储、建模与分析方法，并通过层级化知识图谱组织学习内容。",
                "learning_objective": "学习后应能基于任务目标定位知识点，构建从概念到应用的学习路径。",
                "keywords": self._pick_keywords([course_name, "数据分析", "知识图谱", "模型", "算法"], limit=8),
                "source_refs": [],
            }
        ]
        edges: list[dict[str, Any]] = []

        chapter_nodes: dict[str, dict[str, Any]] = {}
        topic_nodes: dict[str, dict[str, Any]] = {}
        concept_nodes: dict[str, dict[str, Any]] = {}
        concept_name_to_id: dict[str, str] = {}
        topic_to_concept_ids: dict[str, list[str]] = defaultdict(list)

        for chapter_id, profile in chapter_profiles.items():
            chapter_nodes[chapter_id] = {
                "node_id": chapter_id,
                "name": profile["name"],
                "node_type": "chapter",
                "depth": 0,
                "description": profile["description"],
                "learning_objective": profile["learning_objective"],
                "keywords": profile["keywords"],
                "source_refs": profile["source_refs"],
            }

        for doc in docs:
            doc_id = str(doc.get("doc_id") or "")
            source_file = str(doc.get("source_file") or "")
            chapter_id = self._chapter_id(doc)
            chapter_name = chapter_nodes.get(chapter_id, {}).get("name", "课程专题")
            topic_name = self._sanitize_topic_text(self._topic_name(doc)) or doc_id or "未命名主题"
            topic_id = f"topic_{doc_id}" if doc_id else self._hash_id("topic", topic_name)
            local_triples = triples_by_doc.get(doc_id, [])

            concept_terms = accepted_terms_by_doc.get(doc_id, [])
            concept_names = [term for term, _ in concept_terms][: self.max_concepts_per_topic]
            if not concept_names:
                fallback_terms = self._extract_terms(topic_name)
                fallback_scored = []
                for token in fallback_terms:
                    analysis = analyze_candidate(token, self.course_profile, evidence_count=1)
                    if not analysis.rejected:
                        fallback_scored.append((analysis.token, analysis.score))
                fallback_scored.sort(key=lambda item: item[1], reverse=True)
                concept_names = [term for term, _ in fallback_scored[:1]]

            topic_desc, topic_obj, topic_keywords = self._topic_texts(
                topic_name=topic_name,
                chapter_name=chapter_name,
                concept_names=concept_names,
                local_triples=local_triples,
            )

            if topic_id not in topic_nodes:
                topic_nodes[topic_id] = {
                    "node_id": topic_id,
                    "name": topic_name,
                    "node_type": "topic",
                    "depth": 1,
                    "description": topic_desc,
                    "learning_objective": topic_obj,
                    "keywords": topic_keywords,
                    "source_refs": [source_file] if source_file else [],
                    "parent_chapter_id": chapter_id,
                }
            else:
                refs = set(topic_nodes[topic_id].get("source_refs", []))
                if source_file:
                    refs.add(source_file)
                topic_nodes[topic_id]["source_refs"] = sorted(refs)

            for concept_name in concept_names:
                lowered = concept_name.lower()
                concept_id = concept_name_to_id.get(lowered)
                if concept_id is None:
                    desc, obj, keywords = self._concept_texts(
                        concept_name=concept_name,
                        topic_name=topic_name,
                        local_triples=local_triples,
                    )
                    concept_id = self._hash_id("concept", concept_name)
                    concept_name_to_id[lowered] = concept_id
                    concept_nodes[concept_id] = {
                        "node_id": concept_id,
                        "name": concept_name,
                        "node_type": "concept",
                        "depth": 2,
                        "description": desc,
                        "learning_objective": obj,
                        "keywords": keywords or [concept_name],
                        "source_refs": [source_file] if source_file else [],
                    }
                else:
                    refs = set(concept_nodes[concept_id].get("source_refs", []))
                    if source_file:
                        refs.add(source_file)
                    concept_nodes[concept_id]["source_refs"] = sorted(refs)

                if concept_id not in topic_to_concept_ids[topic_id]:
                    topic_to_concept_ids[topic_id].append(concept_id)

        edge_counter = 0

        def add_edge(
            source: str,
            target: str,
            relation_type: str,
            confidence: float,
            relation_text: str = "",
            evidence: str = "",
        ) -> None:
            nonlocal edge_counter
            edge_counter += 1
            edges.append(
                {
                    "edge_id": f"edge_{edge_counter:06d}",
                    "source_node_id": source,
                    "target_node_id": target,
                    "relation_type": relation_type,
                    "relation_text": relation_text,
                    "confidence": round(float(confidence), 3),
                    "evidence": evidence,
                }
            )

        for chapter_id in chapter_nodes:
            add_edge(course_id, chapter_id, "HAS_CHILD", 1.0, evidence="课程包含章节")
        for topic_id, topic in topic_nodes.items():
            parent = str(topic.get("parent_chapter_id") or "chapter_misc")
            add_edge(parent, topic_id, "HAS_CHILD", 1.0, evidence="章节包含主题")
            for concept_id in topic_to_concept_ids.get(topic_id, []):
                add_edge(topic_id, concept_id, "HAS_CHILD", 1.0, evidence="主题包含知识点")

        concept_lookup = {
            normalize_term(node.get("name", "")).lower(): concept_id
            for concept_id, node in concept_nodes.items()
            if normalize_term(node.get("name", ""))
        }

        semantic_edge_count = 0
        for triple in triples:
            subject = normalize_term(str(triple.get("subject", "")))
            predicate = normalize_term(str(triple.get("predicate", "")))
            obj = normalize_term(str(triple.get("object", "")))
            source_id = concept_lookup.get(subject.lower())
            target_id = concept_lookup.get(obj.lower())
            if not source_id or not target_id or source_id == target_id:
                continue
            relation_type = self._infer_relation_type(predicate)
            confidence = float(triple.get("confidence", 0.75) or 0.75)
            confidence = min(max(confidence, 0.3), 0.95)
            evidence = f"{triple.get('source_file', '')}: {subject} - {predicate} - {obj}"
            add_edge(
                source_id,
                target_id,
                relation_type,
                confidence,
                relation_text=predicate,
                evidence=evidence,
            )
            semantic_edge_count += 1

        if semantic_edge_count == 0:
            for topic_id, concept_ids in topic_to_concept_ids.items():
                for idx in range(len(concept_ids) - 1):
                    add_edge(
                        concept_ids[idx],
                        concept_ids[idx + 1],
                        "RELATED_TO",
                        0.6,
                        relation_text="topic_sequence",
                        evidence=f"fallback sequence in {topic_id}",
                    )
                    semantic_edge_count += 1

        nodes.extend(chapter_nodes.values())
        nodes.extend(topic_nodes.values())
        nodes.extend(concept_nodes.values())

        rejected_by_reason: Counter[str] = Counter(item.get("reject_reason", "unknown") for item in audit_rejected)
        accepted_counter: Counter[str] = Counter()
        for concept in concept_nodes.values():
            accepted_counter[str(concept.get("name", ""))] += 1

        concept_audit = {
            "stats": {
                "candidate_total": len(audit_rejected) + sum(len(v) for v in accepted_terms_by_doc.values()),
                "accepted_unique_count": len(concept_nodes),
                "rejected_count": len(audit_rejected),
                "rejected_by_reason": dict(rejected_by_reason),
                "duplicate_accepted_name_count": sum(count - 1 for count in accepted_counter.values() if count > 1),
            },
            "accepted_concepts_sample": sorted(
                [
                    {"name": name, "count": count}
                    for name, count in accepted_counter.items()
                ],
                key=lambda item: item["count"],
                reverse=True,
            )[:50],
            "rejected_candidates_sample": audit_rejected[:300],
        }

        stats = {
            "course_node_count": 1,
            "chapter_count": len(chapter_nodes),
            "topic_count": len(topic_nodes),
            "concept_count": len(concept_nodes),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "semantic_edge_count": semantic_edge_count,
            "concept_candidate_total": concept_audit["stats"]["candidate_total"],
            "concept_rejected_count": concept_audit["stats"]["rejected_count"],
        }
        self._log(
            "info",
            "Hierarchy build finished. chapters=%s topics=%s concepts=%s nodes=%s edges=%s rejected_candidates=%s",
            stats["chapter_count"],
            stats["topic_count"],
            stats["concept_count"],
            stats["node_count"],
            stats["edge_count"],
            stats["concept_rejected_count"],
        )

        graph = {
            "course_id": course_id,
            "course_name": course_name,
            "version": datetime_now_iso(),
            "nodes": nodes,
            "edges": edges,
            "meta": {
                "builder": "HierarchyBuilder",
                "stats": stats,
                "course_profile": self.course_profile.to_snapshot(),
                "concept_audit_summary": concept_audit["stats"],
            },
        }
        return {"graph": graph, "stats": stats, "concept_audit": concept_audit}


def datetime_now_iso() -> str:
    return datetime.now().isoformat()
