from __future__ import annotations

import re
from collections import Counter
from typing import Any

import dspy

from kg_gen.steps._1_get_entities import get_entities
from kg_gen.steps._2_get_relations import get_relations


class KGGenClient:
    """Extract triples with kg-gen steps and robust fallbacks."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        api_base: str,
        logger=None,
        kggen_doc_limit: int = 2,
        max_chars_per_doc: int = 1200,
    ) -> None:
        self.model = self._normalize_model(model)
        self.api_key = api_key
        self.api_base = self._normalize_api_base(api_base)
        self.logger = logger
        self.kggen_doc_limit = max(1, kggen_doc_limit)
        self.max_chars_per_doc = max(300, max_chars_per_doc)
        self._lm = dspy.LM(
            model=self.model,
            api_key=self.api_key,
            api_base=self.api_base,
            temperature=0.0,
            model_type="chat",
            cache=False,
        )

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    @staticmethod
    def _normalize_model(model: str) -> str:
        raw = (model or "").strip()
        if not raw:
            return "openai/gpt-4o-mini"
        providers = (
            "openai/",
            "anthropic/",
            "gemini/",
            "ollama/",
            "ollama_chat/",
            "deepseek/",
        )
        if raw.startswith(providers):
            return raw
        return f"openai/{raw}"

    @staticmethod
    def _normalize_api_base(api_base: str) -> str:
        raw = (api_base or "").strip()
        if not raw:
            return raw
        return raw if raw.endswith("/v1") else f"{raw.rstrip('/')}/v1"

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        return text[:max_chars].strip() if len(text) > max_chars else text.strip()

    @staticmethod
    def _heuristic_terms(text: str, limit: int = 8) -> list[str]:
        tokens = re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]{2,}", text)
        if not tokens:
            return []
        stop_words = {
            "我们",
            "你们",
            "他们",
            "这个",
            "那个",
            "以及",
            "可以",
            "通过",
            "进行",
            "然后",
            "就是",
            "因为",
            "一个",
            "一种",
            "主要",
        }
        filtered = [token for token in tokens if token not in stop_words]
        counter = Counter(filtered)
        return [term for term, _ in counter.most_common(limit)]

    def _build_records(
        self,
        triples: list[tuple[str, str, str]],
        *,
        doc: dict[str, Any],
        extraction_mode: str,
        confidence: float,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for idx, (subject, predicate, obj) in enumerate(triples, start=1):
            records.append(
                {
                    "triple_local_id": f"{doc.get('doc_id')}_{idx:04d}",
                    "doc_id": doc.get("doc_id"),
                    "source_file": doc.get("source_file"),
                    "chapter_tag": doc.get("chapter_tag"),
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "extraction_mode": extraction_mode,
                    "confidence": confidence,
                }
            )
        return records

    def _relations_from_entities(self, entities: list[str]) -> list[tuple[str, str, str]]:
        if len(entities) < 2:
            return []
        triples: list[tuple[str, str, str]] = []
        for i in range(len(entities) - 1):
            triples.append((entities[i], "related_to", entities[i + 1]))
        return triples

    def _heuristic_triples(self, doc: dict[str, Any]) -> list[tuple[str, str, str]]:
        text = doc.get("cleaned_text", "")
        terms = self._heuristic_terms(text, limit=8)
        if len(terms) < 2:
            title = str(doc.get("title") or doc.get("topic") or "概念")
            topic = str(doc.get("topic") or "课程知识")
            terms = [topic, title]
        triples: list[tuple[str, str, str]] = []
        for i in range(len(terms) - 1):
            triples.append((terms[i], "related_to", terms[i + 1]))
        return triples

    def _extract_with_kggen_steps(
        self, doc: dict[str, Any]
    ) -> tuple[list[tuple[str, str, str]], list[str]]:
        text = self._truncate(str(doc.get("cleaned_text", "")), self.max_chars_per_doc)
        if not text:
            return [], []

        with dspy.context(lm=self._lm):
            entities = get_entities(
                text,
                is_conversation=False,
                use_litellm_prompt=False,
                model=self.model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.0,
            )
            relations = get_relations(
                text,
                entities,
                is_conversation=False,
                use_litellm_prompt=False,
                model=self.model,
                api_key=self.api_key,
                api_base=self.api_base,
                temperature=0.0,
            )

        cleaned_relations = [
            (str(s).strip(), str(p).strip(), str(o).strip()) for s, p, o in relations
        ]
        cleaned_relations = [triple for triple in cleaned_relations if all(triple)]

        if not cleaned_relations:
            cleaned_relations = self._relations_from_entities([str(e).strip() for e in entities if str(e).strip()])

        return cleaned_relations, [str(e).strip() for e in entities if str(e).strip()]

    def extract(self, cleaned_docs: list[dict[str, Any]]) -> dict[str, Any]:
        all_records: list[dict[str, Any]] = []
        doc_stats: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        mode_counter = Counter()

        for index, doc in enumerate(cleaned_docs, start=1):
            doc_id = str(doc.get("doc_id") or f"doc_{index:03d}")
            source_file = str(doc.get("source_file") or "")
            triples: list[tuple[str, str, str]] = []
            entities: list[str] = []
            extraction_mode = "heuristic"
            confidence = 0.55

            if index <= self.kggen_doc_limit:
                try:
                    triples, entities = self._extract_with_kggen_steps(doc)
                    extraction_mode = "kg-gen-steps"
                    confidence = 0.85
                except Exception as exc:
                    errors.append({"doc_id": doc_id, "source_file": source_file, "error": str(exc)})
                    self._log(
                        "warning",
                        "kg-gen extraction failed for %s, fallback to heuristic. error=%s",
                        source_file,
                        exc,
                    )

            if not triples:
                triples = self._heuristic_triples(doc)
                extraction_mode = "heuristic"
                confidence = 0.55

            records = self._build_records(
                triples,
                doc=doc,
                extraction_mode=extraction_mode,
                confidence=confidence,
            )
            all_records.extend(records)
            mode_counter[extraction_mode] += 1

            doc_stats.append(
                {
                    "doc_id": doc_id,
                    "source_file": source_file,
                    "extraction_mode": extraction_mode,
                    "entity_count": len(set(entities)) if entities else 0,
                    "triple_count": len(records),
                }
            )

        docs_with_triples = sum(1 for item in doc_stats if item["triple_count"] > 0)
        stats = {
            "total_docs": len(cleaned_docs),
            "docs_with_triples": docs_with_triples,
            "kggen_attempted_docs": min(len(cleaned_docs), self.kggen_doc_limit),
            "kggen_success_docs": mode_counter.get("kg-gen-steps", 0),
            "heuristic_docs": mode_counter.get("heuristic", 0),
            "failed_docs": len(cleaned_docs) - docs_with_triples,
            "raw_triple_count": len(all_records),
            "mode_distribution": dict(mode_counter),
        }

        self._log(
            "info",
            "Stage2 extraction finished. docs=%s raw_triples=%s kggen_success_docs=%s heuristic_docs=%s",
            stats["total_docs"],
            stats["raw_triple_count"],
            stats["kggen_success_docs"],
            stats["heuristic_docs"],
        )

        return {
            "triples": all_records,
            "doc_stats": doc_stats,
            "errors": errors,
            "stats": stats,
        }
