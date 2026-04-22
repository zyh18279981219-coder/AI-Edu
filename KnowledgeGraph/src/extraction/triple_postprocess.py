from __future__ import annotations

import re
from typing import Any


class TriplePostProcessor:
    """Normalize and deduplicate raw triples."""

    @staticmethod
    def _normalize_token(text: str) -> str:
        cleaned = (text or "").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip("，,。.;；:：")
        return cleaned

    def normalize(self, triples: list[dict[str, Any]]) -> dict[str, Any]:
        dedup: dict[tuple[str, str, str], dict[str, Any]] = {}

        for triple in triples:
            subject = self._normalize_token(str(triple.get("subject", "")))
            predicate = self._normalize_token(str(triple.get("predicate", "")))
            obj = self._normalize_token(str(triple.get("object", "")))

            if not subject or not predicate or not obj:
                continue
            if subject == obj:
                continue
            if len(subject) < 2 or len(obj) < 2:
                continue

            key = (subject.lower(), predicate.lower(), obj.lower())
            candidate = dict(triple)
            candidate["subject"] = subject
            candidate["predicate"] = predicate
            candidate["object"] = obj

            previous = dedup.get(key)
            if previous is None:
                dedup[key] = candidate
            else:
                prev_conf = float(previous.get("confidence", 0) or 0)
                new_conf = float(candidate.get("confidence", 0) or 0)
                if new_conf > prev_conf:
                    dedup[key] = candidate

        normalized = list(dedup.values())
        for idx, item in enumerate(normalized, start=1):
            item["triple_id"] = f"triple_{idx:06d}"

        entities = set()
        edges = set()
        for item in normalized:
            entities.add(item["subject"])
            entities.add(item["object"])
            edges.add(item["predicate"])

        stats = {
            "normalized_triple_count": len(normalized),
            "unique_entity_count": len(entities),
            "unique_edge_count": len(edges),
            "relation_count_gt_entity_count": len(normalized) > len(entities),
        }
        return {"triples": normalized, "stats": stats}
