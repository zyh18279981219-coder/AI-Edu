from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

class RelationRefiner:
    """Refine graph edges for pedagogical quality and consistency."""

    _RELATION_MAP = {
        "has_child": "HAS_CHILD",
        "contains": "INCLUDES",
        "include": "INCLUDES",
        "includes": "INCLUDES",
        "prerequisite": "PREREQUISITE",
        "pre_requisite": "PREREQUISITE",
        "depends_on": "PREREQUISITE",
        "related_to": "RELATED_TO",
        "related": "RELATED_TO",
        "uses": "USES",
        "used_by": "USES",
        "applies_to": "APPLIES_TO",
        "compare_with": "COMPARES_WITH",
        "compares_with": "COMPARES_WITH",
    }

    _ALLOWED_RELATIONS = {
        "HAS_CHILD",
        "PREREQUISITE",
        "RELATED_TO",
        "USES",
        "APPLIES_TO",
        "INCLUDES",
        "COMPARES_WITH",
    }

    def __init__(
        self,
        logger=None,
        min_confidence: float = 0.35,
    ) -> None:
        self.logger = logger
        self.min_confidence = max(0.0, min(1.0, min_confidence))

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    @staticmethod
    def _normalize_relation_type(relation_type: str, relation_text: str = "") -> str:
        raw = (relation_type or "").strip()
        lowered = raw.lower()
        if lowered in RelationRefiner._RELATION_MAP:
            return RelationRefiner._RELATION_MAP[lowered]
        upper = raw.upper()
        if upper in RelationRefiner._ALLOWED_RELATIONS:
            return upper

        text = (relation_text or "").lower()
        if any(token in text for token in ["前提", "先修", "依赖", "prerequisite", "depend"]):
            return "PREREQUISITE"
        if any(token in text for token in ["包含", "包括", "组成", "include", "contain"]):
            return "INCLUDES"
        if any(token in text for token in ["应用", "用于", "apply"]):
            return "APPLIES_TO"
        if any(token in text for token in ["使用", "基于", "实现", "调用", "use"]):
            return "USES"
        if any(token in text for token in ["比较", "对比", "compare"]):
            return "COMPARES_WITH"
        return "RELATED_TO"

    @staticmethod
    def _clamp_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.5
        return max(0.05, min(1.0, confidence))

    @staticmethod
    def _find_path_exists(
        adjacency: dict[str, set[str]],
        start: str,
        target: str,
    ) -> bool:
        if start == target:
            return True

        queue: deque[str] = deque([start])
        visited: set[str] = set()
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for nxt in adjacency.get(current, set()):
                if nxt == target:
                    return True
                if nxt not in visited:
                    queue.append(nxt)
        return False

    def _prune_prerequisite_cycles(
        self,
        edges: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        prereq = [edge for edge in edges if edge.get("relation_type") == "PREREQUISITE"]
        others = [edge for edge in edges if edge.get("relation_type") != "PREREQUISITE"]
        prereq.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)

        adjacency: dict[str, set[str]] = defaultdict(set)
        kept_prereq: list[dict[str, Any]] = []
        removed_cycle_count = 0

        for edge in prereq:
            source = str(edge.get("source_node_id", ""))
            target = str(edge.get("target_node_id", ""))
            if not source or not target:
                removed_cycle_count += 1
                continue
            if self._find_path_exists(adjacency, target, source):
                removed_cycle_count += 1
                continue
            adjacency[source].add(target)
            kept_prereq.append(edge)

        refined = others + kept_prereq
        return refined, removed_cycle_count

    def refine(self, graph: dict[str, Any]) -> dict[str, Any]:
        nodes = graph.get("nodes", []) or []
        edges = graph.get("edges", []) or []
        node_ids = {str(node.get("node_id")) for node in nodes if node.get("node_id")}

        stats = {
            "input_edge_count": len(edges),
            "removed_invalid_endpoint_count": 0,
            "removed_self_loop_count": 0,
            "removed_low_confidence_count": 0,
            "deduplicated_edge_count": 0,
            "relation_type_remap_count": 0,
            "removed_prerequisite_cycle_count": 0,
            "output_edge_count": 0,
        }

        dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
        for edge in edges:
            source = str(edge.get("source_node_id", "")).strip()
            target = str(edge.get("target_node_id", "")).strip()
            if not source or not target or source not in node_ids or target not in node_ids:
                stats["removed_invalid_endpoint_count"] += 1
                continue
            if source == target:
                stats["removed_self_loop_count"] += 1
                continue

            relation_text = str(edge.get("relation_text", "") or "")
            raw_relation_type = str(edge.get("relation_type", "") or "")
            relation_type = self._normalize_relation_type(raw_relation_type, relation_text)
            if relation_type != raw_relation_type:
                stats["relation_type_remap_count"] += 1

            confidence = self._clamp_confidence(edge.get("confidence"))
            if relation_type != "HAS_CHILD" and confidence < self.min_confidence:
                stats["removed_low_confidence_count"] += 1
                continue

            normalized = {
                "source_node_id": source,
                "target_node_id": target,
                "relation_type": relation_type,
                "relation_text": relation_text,
                "confidence": round(confidence, 3),
                "evidence": str(edge.get("evidence", "") or ""),
            }
            key = (source, target, relation_type)

            previous = dedup.get(key)
            if previous is None:
                dedup[key] = normalized
                continue

            stats["deduplicated_edge_count"] += 1
            prev_conf = float(previous.get("confidence", 0.0))
            if confidence > prev_conf:
                dedup[key] = normalized
            else:
                evidence = set(
                    part.strip()
                    for part in [previous.get("evidence", ""), normalized.get("evidence", "")]
                    if part
                )
                previous["evidence"] = " | ".join(sorted(evidence))

        candidate_edges = list(dedup.values())
        candidate_edges, removed_cycle = self._prune_prerequisite_cycles(candidate_edges)
        stats["removed_prerequisite_cycle_count"] = removed_cycle

        candidate_edges.sort(
            key=lambda item: (
                item.get("source_node_id", ""),
                item.get("target_node_id", ""),
                item.get("relation_type", ""),
            )
        )
        for idx, edge in enumerate(candidate_edges, start=1):
            edge["edge_id"] = f"edge_{idx:06d}"

        stats["output_edge_count"] = len(candidate_edges)
        relation_distribution = defaultdict(int)
        for edge in candidate_edges:
            relation_distribution[str(edge.get("relation_type"))] += 1
        stats["relation_distribution"] = dict(relation_distribution)

        meta = dict(graph.get("meta", {}) or {})
        meta["relation_refiner"] = {"stats": stats}
        refined_graph = dict(graph)
        refined_graph["edges"] = candidate_edges
        refined_graph["meta"] = meta

        self._log(
            "info",
            "Relation refine finished. input_edges=%s output_edges=%s removed_cycle=%s",
            stats["input_edge_count"],
            stats["output_edge_count"],
            stats["removed_prerequisite_cycle_count"],
        )
        return {"graph": refined_graph, "stats": stats}
