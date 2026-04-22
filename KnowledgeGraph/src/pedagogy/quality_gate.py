from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from KnowledgeGraph.src.course_profile import CourseProfile
from KnowledgeGraph.src.kg_text_rules import (
    analyze_candidate,
    is_generic_chapter_name,
    is_generic_text,
    is_noise_keyword,
    normalize_term,
    normalize_token,
)


class QualityGate:
    """Evaluate graph quality with generic + profile-driven hard checks."""

    def __init__(
        self,
        logger=None,
        profile_path: Path | str | None = None,
        course_profile: CourseProfile | None = None,
    ) -> None:
        self.logger = logger
        self.course_profile = course_profile or CourseProfile.from_path(profile_path)

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    @staticmethod
    def _build_adjacency(edges: list[dict[str, Any]], relation_type: str) -> dict[str, set[str]]:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.get("relation_type") != relation_type:
                continue
            source = str(edge.get("source_node_id", ""))
            target = str(edge.get("target_node_id", ""))
            if source and target:
                adjacency[source].add(target)
        return adjacency

    @staticmethod
    def _has_cycle(adjacency: dict[str, set[str]]) -> bool:
        state: dict[str, int] = {}

        def dfs(node: str) -> bool:
            node_state = state.get(node, 0)
            if node_state == 1:
                return True
            if node_state == 2:
                return False
            state[node] = 1
            for nxt in adjacency.get(node, set()):
                if dfs(nxt):
                    return True
            state[node] = 2
            return False

        for node in adjacency:
            if state.get(node, 0) == 0 and dfs(node):
                return True
        return False

    @staticmethod
    def _node_type_counts(nodes: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(str(node.get("node_type", "unknown")) for node in nodes))

    @staticmethod
    def _depth_distribution(nodes: list[dict[str, Any]]) -> dict[str, int]:
        return dict(Counter(str(node.get("depth", "unknown")) for node in nodes))

    @staticmethod
    def _duplicate_concept_rate(nodes: list[dict[str, Any]]) -> tuple[float, int, int]:
        concept_names: list[str] = []
        for node in nodes:
            if str(node.get("node_type", "")).lower() != "concept":
                continue
            name = normalize_term(str(node.get("name", ""))).lower()
            if name:
                concept_names.append(name)
        if not concept_names:
            return 100.0, 0, 0
        counter = Counter(concept_names)
        duplicate_count = sum(count - 1 for count in counter.values() if count > 1)
        total_count = len(concept_names)
        return round(duplicate_count / total_count * 100.0, 2), duplicate_count, total_count

    @staticmethod
    def _orphan_nodes(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[str]:
        inbound: dict[str, int] = defaultdict(int)
        outbound: dict[str, int] = defaultdict(int)
        for edge in edges:
            source = str(edge.get("source_node_id", ""))
            target = str(edge.get("target_node_id", ""))
            if source:
                outbound[source] += 1
            if target:
                inbound[target] += 1

        orphan_ids: list[str] = []
        for node in nodes:
            node_id = str(node.get("node_id", ""))
            node_type = str(node.get("node_type", ""))
            if not node_id or node_type == "course":
                continue
            if inbound.get(node_id, 0) == 0 and outbound.get(node_id, 0) == 0:
                orphan_ids.append(node_id)
        return orphan_ids

    @staticmethod
    def _hierarchy_integrity(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
        node_type = {str(node.get("node_id")): str(node.get("node_type", "")) for node in nodes}
        has_child_parent: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.get("relation_type") != "HAS_CHILD":
                continue
            source = str(edge.get("source_node_id", ""))
            target = str(edge.get("target_node_id", ""))
            if source and target:
                has_child_parent[target].add(source)

        expected = {"chapter": "course", "topic": "chapter", "concept": "topic"}
        missing_parent: list[str] = []
        wrong_parent: list[str] = []
        for node_id, node_kind in node_type.items():
            if node_kind not in expected:
                continue
            parents = has_child_parent.get(node_id, set())
            if not parents:
                missing_parent.append(node_id)
                continue
            expected_parent = expected[node_kind]
            if not any(node_type.get(parent) == expected_parent for parent in parents):
                wrong_parent.append(node_id)

        return {
            "missing_parent_count": len(missing_parent),
            "wrong_parent_type_count": len(wrong_parent),
            "missing_parent_node_ids": missing_parent[:20],
            "wrong_parent_type_node_ids": wrong_parent[:20],
        }

    @staticmethod
    def _generic_text_rate(nodes: list[dict[str, Any]], field: str) -> tuple[float, list[str]]:
        values = []
        for node in nodes:
            if node.get("node_type") == "course":
                continue
            value = normalize_token(str(node.get(field, "")))
            if value:
                values.append(value)
        if not values:
            return 100.0, []
        generic_samples = [value for value in values if is_generic_text(value)]
        duplicate_rate = (len(values) - len(set(values))) / len(values)
        generic_rate = len(generic_samples) / len(values)
        return round(max(duplicate_rate, generic_rate) * 100.0, 2), generic_samples[:10]

    def _chapter_name_issues(self, nodes: list[dict[str, Any]]) -> list[str]:
        issues: list[str] = []
        for node in nodes:
            if str(node.get("node_type", "")) != "chapter":
                continue
            name = normalize_term(str(node.get("name", "")))
            if is_generic_chapter_name(name):
                issues.append(name or str(node.get("node_id", "")))
        return issues

    def _keyword_noise_issues(self, nodes: list[dict[str, Any]]) -> list[str]:
        issues: list[str] = []
        for node in nodes:
            node_id = str(node.get("node_id", ""))
            for keyword in node.get("keywords", []) or []:
                kw = normalize_term(str(keyword))
                if kw and is_noise_keyword(kw, self.course_profile):
                    issues.append(f"{node_id}:{kw}")
        return issues

    def _concept_quality_issues(self, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        rejected: list[dict[str, Any]] = []
        reason_counter: Counter[str] = Counter()
        reason_samples: dict[str, list[str]] = defaultdict(list)

        for node in nodes:
            if str(node.get("node_type", "")) != "concept":
                continue
            name = normalize_term(str(node.get("name", "")))
            analysis = analyze_candidate(name, self.course_profile, evidence_count=4)
            if analysis.rejected and analysis.reject_reason != "score_below_threshold":
                reason = analysis.reject_reason or "unknown"
                reason_counter[reason] += 1
                if len(reason_samples[reason]) < 20:
                    reason_samples[reason].append(name)
                rejected.append(
                    {
                        "name": name,
                        "reason": reason,
                        "score": round(analysis.score, 3),
                        "flags": analysis.flags,
                    }
                )

        return {
            "total_invalid_count": len(rejected),
            "invalid_samples": rejected[:50],
            "reason_count": dict(reason_counter),
            "reason_samples": dict(reason_samples),
            "abstract_concept_count": reason_counter.get("abstract_term", 0),
            "sentence_fragment_concept_count": reason_counter.get("sentence_fragment", 0),
            "measure_fragment_concept_count": reason_counter.get("measure_fragment", 0),
            "identifier_fragment_concept_count": reason_counter.get("identifier_fragment", 0),
        }

    def evaluate(
        self,
        graph: dict[str, Any],
        model_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nodes = graph.get("nodes", []) or []
        edges = graph.get("edges", []) or []
        type_counts = self._node_type_counts(nodes)
        depth_distribution = self._depth_distribution(nodes)
        duplicate_rate, duplicate_count, concept_count = self._duplicate_concept_rate(nodes)
        orphan_ids = self._orphan_nodes(nodes, edges)
        hierarchy_integrity = self._hierarchy_integrity(nodes, edges)

        prereq_adj = self._build_adjacency(edges, "PREREQUISITE")
        prerequisite_cycle_detected = self._has_cycle(prereq_adj)
        semantic_edge_count = sum(1 for edge in edges if edge.get("relation_type") != "HAS_CHILD")

        chapter_issues = self._chapter_name_issues(nodes)
        description_generic_rate, description_generic_samples = self._generic_text_rate(nodes, "description")
        objective_generic_rate, objective_generic_samples = self._generic_text_rate(nodes, "learning_objective")
        keyword_noise_issues = self._keyword_noise_issues(nodes)
        concept_issues = self._concept_quality_issues(nodes)

        metrics = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_type_distribution": type_counts,
            "hierarchy_depth_distribution": depth_distribution,
            "prerequisite_cycle_detected": prerequisite_cycle_detected,
            "concept_count": concept_count,
            "semantic_edge_count": semantic_edge_count,
            "duplicate_name_rate": duplicate_rate,
            "duplicate_name_count": duplicate_count,
            "orphan_node_count": len(orphan_ids),
            "orphan_node_ids_sample": orphan_ids[:20],
            "hierarchy_integrity": hierarchy_integrity,
            "chapter_name_issue_count": len(chapter_issues),
            "chapter_name_issues_sample": chapter_issues[:20],
            "generic_description_rate": description_generic_rate,
            "generic_description_samples": description_generic_samples,
            "generic_learning_objective_rate": objective_generic_rate,
            "generic_learning_objective_samples": objective_generic_samples,
            "keyword_noise_count": len(keyword_noise_issues),
            "keyword_noise_samples": keyword_noise_issues[:40],
            "invalid_concept_count": concept_issues["total_invalid_count"],
            "invalid_concept_samples": concept_issues["invalid_samples"],
            "invalid_concept_reason_count": concept_issues["reason_count"],
            "abstract_concept_count": concept_issues["abstract_concept_count"],
            "sentence_fragment_concept_count": concept_issues["sentence_fragment_concept_count"],
            "measure_fragment_concept_count": concept_issues["measure_fragment_concept_count"],
            "identifier_fragment_concept_count": concept_issues["identifier_fragment_concept_count"],
            "concept_text_resource_coverage": 0.0,
            "video_match_rate": 0.0,
            "generation_timestamp": datetime.now().isoformat(),
            "model_config_snapshot": model_config or {},
            "course_profile_snapshot": self.course_profile.to_snapshot(),
        }

        acceptance = {
            "canonical_has_course_chapter_topic_concept": (
                type_counts.get("course", 0) >= 1
                and type_counts.get("chapter", 0) >= 1
                and type_counts.get("topic", 0) >= 1
                and type_counts.get("concept", 0) >= 1
            ),
            "prerequisite_acyclic": not prerequisite_cycle_detected,
            "duplicate_name_rate_lt_5pct": duplicate_rate < 5.0,
            "hierarchy_integrity_passed": (
                hierarchy_integrity["missing_parent_count"] == 0
                and hierarchy_integrity["wrong_parent_type_count"] == 0
            ),
            "semantic_edge_positive": semantic_edge_count > 0,
            "chapter_semantic_name_pass": len(chapter_issues) == 0,
            "generic_description_rate_lt_20pct": description_generic_rate < 20.0,
            "generic_learning_objective_rate_lt_20pct": objective_generic_rate < 20.0,
            "keyword_noise_count_zero": len(keyword_noise_issues) == 0,
            "invalid_concept_count_zero": concept_issues["total_invalid_count"] == 0,
            "abstract_concept_count_zero": concept_issues["abstract_concept_count"] == 0,
            "sentence_fragment_concept_count_zero": concept_issues["sentence_fragment_concept_count"] == 0,
            "measure_fragment_concept_count_zero": concept_issues["measure_fragment_concept_count"] == 0,
            "identifier_fragment_concept_count_zero": concept_issues["identifier_fragment_concept_count"] == 0,
        }
        passed = all(acceptance.values())

        self._log(
            "info",
            "Quality gate evaluated. passed=%s nodes=%s edges=%s invalid_concepts=%s keyword_noise=%s",
            passed,
            metrics["node_count"],
            metrics["edge_count"],
            metrics["invalid_concept_count"],
            metrics["keyword_noise_count"],
        )
        return {"passed": passed, "metrics": metrics, "acceptance": acceptance}
