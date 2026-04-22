from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from KnowledgeGraph.src.resource_match.utils import (
    build_concept_context,
    load_legacy_leaf_entries,
    normalize_key,
    rebuild_resource_refs,
    stable_index,
    token_overlap_score,
    tokenize,
)

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None

class BookIndexer:
    """Build local PDF index and match one mandatory text resource per concept."""

    def __init__(
        self,
        book_dir: Path | str,
        logger=None,
        max_pages: int = 3,
        max_chars: int = 12000,
        min_score: float = 0.06,
    ) -> None:
        self.book_dir = Path(book_dir)
        self.logger = logger
        self.max_pages = max(1, int(max_pages))
        self.max_chars = max(2000, int(max_chars))
        self.min_score = max(0.0, min(1.0, float(min_score)))

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        if fitz is None:
            return ""
        try:
            chunks: list[str] = []
            total_chars = 0
            with fitz.open(pdf_path) as doc:
                for page_index in range(min(len(doc), self.max_pages)):
                    page_text = (doc.load_page(page_index).get_text("text") or "").strip()
                    if not page_text:
                        continue
                    chunks.append(page_text)
                    total_chars += len(page_text)
                    if total_chars >= self.max_chars:
                        break
            if not chunks:
                return ""
            return "\n".join(chunks)[: self.max_chars]
        except Exception as exc:
            self._log("warning", "Book index extraction failed: %s (%s)", pdf_path.name, exc)
            return ""

    @staticmethod
    def _sort_key(path: Path) -> tuple[int, str]:
        stem = path.stem
        if stem.isdigit():
            return int(stem), path.name.lower()
        return 10**9, path.name.lower()

    @staticmethod
    def _build_text_resource(book: dict[str, Any], score: float, method: str) -> dict[str, Any]:
        return {
            "resource_id": f"text_{book['book_id']}",
            "resource_type": "text",
            "title": str(book.get("title", "") or book.get("file_name", "")),
            "path": str(book.get("relative_path", "")),
            "score": round(score, 3),
            "match_method": method,
            "provider": "local_book",
        }

    @staticmethod
    def _strip_text_resources(node: dict[str, Any]) -> list[dict[str, Any]]:
        resources = node.get("resources", [])
        if not isinstance(resources, list):
            return []
        return [
            item
            for item in resources
            if str(item.get("resource_type", "")).lower() not in {"text", "book", "pdf"}
        ]

    @staticmethod
    def _title_from_text(file_stem: str, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if len(stripped) > 64:
                continue
            return stripped
        return file_stem

    @staticmethod
    def _similarity(lhs: str, rhs: str) -> float:
        if not lhs or not rhs:
            return 0.0
        return SequenceMatcher(None, lhs, rhs).ratio()

    def index(self, legacy_graph_path: Path | str | None = None) -> dict[str, Any]:
        pdf_files = sorted(self.book_dir.glob("*.pdf"), key=self._sort_key)
        legacy_entries = load_legacy_leaf_entries(legacy_graph_path)

        aliases_by_book: dict[str, set[str]] = defaultdict(set)
        concept_to_books: dict[str, list[str]] = defaultdict(list)
        for entry in legacy_entries:
            concept_name = str(entry.get("name", "")).strip()
            concept_key = str(entry.get("name_key", "")).strip()
            for book_path in entry.get("books", []) or []:
                normalized_path = str(book_path).replace("\\", "/")
                if concept_name:
                    aliases_by_book[normalized_path].add(concept_name)
                if concept_key and normalized_path not in concept_to_books[concept_key]:
                    concept_to_books[concept_key].append(normalized_path)

        books: list[dict[str, Any]] = []
        extraction_failed_count = 0
        for index, pdf_path in enumerate(pdf_files, start=1):
            extracted = self._extract_pdf_text(pdf_path)
            if not extracted:
                extraction_failed_count += 1
            relative_path = f"data/Book/{pdf_path.name}"
            aliases = sorted(aliases_by_book.get(relative_path, set()))
            title = self._title_from_text(pdf_path.stem, extracted)
            token_source = " ".join([title, extracted, " ".join(aliases)]).strip()
            token_set = tokenize(token_source)
            books.append(
                {
                    "book_id": f"book_{index:03d}",
                    "file_name": pdf_path.name,
                    "absolute_path": str(pdf_path),
                    "relative_path": relative_path,
                    "title": title,
                    "aliases": aliases[:20],
                    "alias_keys": [normalize_key(item) for item in aliases if normalize_key(item)],
                    "token_set": sorted(token_set),
                    "char_count": len(extracted),
                }
            )

        stats = {
            "pdf_count": len(pdf_files),
            "indexed_count": len(books),
            "extraction_failed_count": extraction_failed_count,
            "fitz_available": fitz is not None,
            "legacy_hint_concept_count": len(concept_to_books),
        }
        self._log(
            "info",
            "Book index built: pdf_count=%s indexed=%s extraction_failed=%s",
            stats["pdf_count"],
            stats["indexed_count"],
            stats["extraction_failed_count"],
        )
        return {
            "books": books,
            "stats": stats,
            "legacy_concept_to_books": dict(concept_to_books),
        }

    def _score_book(
        self,
        concept_name: str,
        query_tokens: set[str],
        legacy_book_paths: set[str],
        book: dict[str, Any],
    ) -> tuple[float, str]:
        book_tokens = set(book.get("token_set", []))
        overlap = 0.0
        if query_tokens and book_tokens:
            overlap_count = len(query_tokens.intersection(book_tokens))
            query_coverage = overlap_count / len(query_tokens)
            book_density = overlap_count / max(1, min(len(book_tokens), 160))
            overlap = 0.8 * query_coverage + 0.2 * book_density
        else:
            overlap = token_overlap_score(query_tokens, book_tokens)
        concept_key = normalize_key(concept_name)

        alias_candidates = [normalize_key(item) for item in (book.get("aliases") or [])]
        alias_sim = 0.0
        for alias in alias_candidates:
            alias_sim = max(alias_sim, self._similarity(concept_key, alias))

        title_key = normalize_key(str(book.get("title", "")))
        title_sim = self._similarity(concept_key, title_key)
        score = 0.70 * overlap + 0.22 * alias_sim + 0.08 * title_sim
        method = "token_overlap"

        if concept_key and concept_key in set(book.get("alias_keys", [])):
            score = max(score, 0.95)
            method = "legacy_exact"
        elif str(book.get("relative_path", "")) in legacy_book_paths:
            score = max(score, 0.88)
            method = "legacy_hint"

        return min(1.0, score), method

    def match(
        self,
        graph: dict[str, Any],
        legacy_graph_path: Path | str | None = None,
    ) -> dict[str, Any]:
        index_payload = self.index(legacy_graph_path=legacy_graph_path)
        books = index_payload.get("books", [])
        legacy_concept_to_books = index_payload.get("legacy_concept_to_books", {})

        updated_nodes: list[dict[str, Any]] = [dict(node) for node in graph.get("nodes", []) or []]
        updated_graph = dict(graph)
        updated_graph["nodes"] = updated_nodes

        contexts = build_concept_context(updated_graph)
        concept_nodes = [node for node in updated_nodes if str(node.get("node_type", "")) == "concept"]

        match_records: list[dict[str, Any]] = []
        fallback_count = 0
        low_confidence_count = 0
        matched_count = 0
        score_values: list[float] = []

        for node in concept_nodes:
            concept_id = str(node.get("node_id", "")).strip()
            context = contexts.get(concept_id, {})
            concept_name = str(node.get("name", "")).strip()
            query_tokens = set(context.get("query_tokens", set()))
            legacy_book_paths = set(
                legacy_concept_to_books.get(normalize_key(concept_name), [])
                + legacy_concept_to_books.get(str(context.get("concept_key", "")), [])
            )

            selected_book: dict[str, Any] | None = None
            selected_score = 0.0
            selected_method = ""

            for book in books:
                score, method = self._score_book(concept_name, query_tokens, legacy_book_paths, book)
                if selected_book is None or score > selected_score:
                    selected_book = book
                    selected_score = score
                    selected_method = method

            if selected_book is None and books:
                selected_book = books[stable_index(concept_id or concept_name, len(books))]
                selected_score = 0.0
                selected_method = "fallback_hash"

            if selected_book is not None and selected_score < self.min_score and books:
                selected_book = books[stable_index(concept_id or concept_name, len(books))]
                selected_score = max(selected_score, 0.05)
                selected_method = "fallback_hash"
                fallback_count += 1

            if selected_book is None:
                node["resources"] = self._strip_text_resources(node)
                node["resource_refs"] = rebuild_resource_refs(node["resources"])
                match_records.append(
                    {
                        "concept_id": concept_id,
                        "concept_name": concept_name,
                        "book_path": "",
                        "score": 0.0,
                        "method": "unmatched",
                    }
                )
                continue

            resource = self._build_text_resource(selected_book, selected_score, selected_method)
            resources = self._strip_text_resources(node)
            resources.append(resource)
            node["resources"] = resources
            node["resource_refs"] = rebuild_resource_refs(resources)

            matched_count += 1
            score_values.append(selected_score)
            if selected_score < 0.2:
                low_confidence_count += 1
            match_records.append(
                {
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "book_path": resource["path"],
                    "score": round(selected_score, 4),
                    "method": selected_method,
                }
            )

        concept_count = len(concept_nodes)
        coverage = round((matched_count / concept_count * 100.0), 2) if concept_count else 0.0
        average_score = round(sum(score_values) / len(score_values), 4) if score_values else 0.0
        stats = {
            "concept_count": concept_count,
            "matched_concept_count": matched_count,
            "text_coverage_pct": coverage,
            "average_match_score": average_score,
            "fallback_count": fallback_count,
            "low_confidence_count": low_confidence_count,
            "book_count": len(books),
            "min_score_threshold": self.min_score,
            "book_index_stats": index_payload.get("stats", {}),
        }

        meta = dict(updated_graph.get("meta", {}) or {})
        resource_meta = dict(meta.get("resource_match", {}) or {})
        resource_meta["book"] = stats
        meta["resource_match"] = resource_meta
        updated_graph["meta"] = meta

        self._log(
            "info",
            "Book matching finished: concepts=%s matched=%s coverage=%.2f%% fallback=%s",
            concept_count,
            matched_count,
            coverage,
            fallback_count,
        )
        return {
            "graph": updated_graph,
            "stats": stats,
            "book_index": index_payload,
            "matches": match_records,
        }
