from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from KnowledgeGraph.src.resource_match.settings import ResourceMatchSettings
from KnowledgeGraph.src.resource_match.utils import build_concept_context, rebuild_resource_refs, tokenize
from KnowledgeGraph.src.resource_match.video_indexer import VideoIndexer
from KnowledgeGraph.src.resource_match.video_transcript_collector import VideoTranscriptCollector

try:  # pragma: no cover - optional dependency path
    from rank_bm25 import BM25Okapi  # type: ignore
except Exception:  # pragma: no cover
    BM25Okapi = None


class VideoMatcher:
    """Match optional videos from transcript semantics without legacy graph dependency."""

    def __init__(
        self,
        video_url_path: Path | str,
        logger=None,
        settings_path: Path | str | None = None,
        transcript_cache_dir: Path | str | None = None,
    ) -> None:
        self.video_url_path = Path(video_url_path)
        self.logger = logger
        self.settings = ResourceMatchSettings.from_path(settings_path).video
        self.transcript_cache_dir = Path(transcript_cache_dir) if transcript_cache_dir else None
        if self.transcript_cache_dir is None:
            self.transcript_cache_dir = (
                Path("KnowledgeGraph")
                / "data"
                / "intermediate"
                / self.settings.transcript_cache_subdir
            )

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    def _load_video_urls(self) -> list[dict[str, Any]]:
        if not self.video_url_path.exists():
            return []

        try:
            payload = json.loads(self.video_url_path.read_text(encoding="utf-8"))
        except Exception:
            return []

        records: list[dict[str, Any]] = []
        if isinstance(payload, list):
            for index, item in enumerate(payload, start=1):
                if isinstance(item, str):
                    url = item.strip()
                    title = ""
                    video_id = f"video_{index:03d}"
                elif isinstance(item, dict):
                    url = str(item.get("url", "")).strip()
                    title = str(item.get("title", "")).strip()
                    video_id = str(item.get("video_id", "")).strip() or f"video_{index:03d}"
                else:
                    continue
                if not url:
                    continue
                records.append(
                    {
                        "video_id": video_id,
                        "url": url,
                        "title": title,
                    }
                )
        return records

    @staticmethod
    def _strip_video_resources(node: dict[str, Any]) -> list[dict[str, Any]]:
        resources = node.get("resources", [])
        if not isinstance(resources, list):
            return []
        return [
            item
            for item in resources
            if str(item.get("resource_type", "")).lower() not in {"video", "m3u8"}
        ]

    @staticmethod
    def _video_title(video_entry: dict[str, Any], concept_name: str) -> str:
        title = str(video_entry.get("title", "")).strip()
        if title:
            return title
        if concept_name:
            return f"{concept_name} - 课程视频"
        return str(video_entry.get("video_id", "课程视频"))

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        value = max(0.0, float(seconds))
        total = int(value)
        hours = total // 3600
        minutes = (total % 3600) // 60
        secs = total % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _format_timestamp_range(self, start: float, end: float) -> str:
        left = self._format_timestamp(start)
        right = self._format_timestamp(end if end > start else start)
        return f"{left} - {right}"

    def _build_chunk_catalog(self, indexed_videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        catalog: list[dict[str, Any]] = []
        for video in indexed_videos:
            video_id = str(video.get("video_id", ""))
            for chunk in video.get("chunks", []) or []:
                token_list = [str(item) for item in (chunk.get("token_list", []) or []) if str(item)]
                token_set = set(str(item) for item in (chunk.get("tokens", []) or []) if str(item))
                if not token_set:
                    token_set = set(token_list)
                catalog.append(
                    {
                        "video_id": video_id,
                        "text": str(chunk.get("text", "")),
                        "start": float(chunk.get("start", 0.0)),
                        "end": float(chunk.get("end", 0.0)),
                        "token_list": token_list,
                        "token_set": token_set,
                        "tfidf_vector": chunk.get("tfidf_vector", {}),
                        "tfidf_norm": float(chunk.get("tfidf_norm", 0.0)),
                    }
                )
        return catalog

    def _expand_query_tokens(
        self,
        query_tokens: set[str],
        key_tokens: set[str],
        topic_tokens: set[str],
        chapter_tokens: set[str],
    ) -> set[str]:
        expanded: set[str] = set(query_tokens).union(key_tokens)

        if self.settings.query_expansion.include_topic_chapter_terms:
            expanded.update(topic_tokens)
            expanded.update(chapter_tokens)

        if not self.settings.query_expansion.enabled:
            return expanded

        synonym_map = self.settings.query_expansion.synonym_map or {}
        seed_tokens = list(expanded)
        for token in seed_tokens:
            mapped_terms = synonym_map.get(token.lower(), [])
            for term in mapped_terms:
                expanded.update(tokenize(term))
                if term.strip():
                    expanded.add(term.strip().lower())
        if len(expanded) > 128:
            return set(sorted(expanded)[:128])
        return expanded

    @staticmethod
    def _keyword_recall(
        keyword_tokens: set[str],
        chunk_catalog: list[dict[str, Any]],
        top_k: int,
    ) -> list[int]:
        if not keyword_tokens or not chunk_catalog:
            return []
        scored_indices: list[tuple[int, int]] = []
        for index, chunk in enumerate(chunk_catalog):
            overlap = len(keyword_tokens.intersection(chunk.get("token_set", set())))
            if overlap <= 0:
                continue
            scored_indices.append((index, overlap))
        scored_indices.sort(key=lambda item: item[1], reverse=True)
        return [index for index, _ in scored_indices[: max(1, top_k)]]

    def _bm25_recall(
        self,
        query_tokens: set[str],
        chunk_catalog: list[dict[str, Any]],
    ) -> tuple[list[int], bool]:
        if not query_tokens or not chunk_catalog or BM25Okapi is None:
            return [], False

        corpus = [chunk.get("token_list", []) for chunk in chunk_catalog]
        if not corpus:
            return [], True

        try:
            bm25 = BM25Okapi(corpus)
            scores = bm25.get_scores(list(query_tokens))
        except Exception:
            return [], True

        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda item: item[1], reverse=True)
        indices: list[int] = []
        for chunk_index, score in indexed_scores:
            if score < float(self.settings.recall.min_bm25_score):
                continue
            indices.append(chunk_index)
            if len(indices) >= max(1, int(self.settings.recall.bm25_top_k)):
                break
        return indices, True

    def _recall_video_ids(
        self,
        query_tokens: set[str],
        keyword_tokens: set[str],
        chunk_catalog: list[dict[str, Any]],
    ) -> tuple[list[str], dict[str, Any]]:
        bm25_indices, bm25_attempted = self._bm25_recall(query_tokens, chunk_catalog)
        keyword_indices = self._keyword_recall(
            keyword_tokens=keyword_tokens,
            chunk_catalog=chunk_catalog,
            top_k=max(1, int(self.settings.recall.keyword_top_k)),
        )

        bm25_index_set = set(bm25_indices)
        merged_indices = bm25_indices + [item for item in keyword_indices if item not in bm25_index_set]
        if not merged_indices:
            return [], {
                "bm25_attempted": bm25_attempted,
                "bm25_hit_count": 0,
                "keyword_hit_count": 0,
                "merged_hit_count": 0,
            }

        candidate_pool = max(
            int(self.settings.recall.rerank_top_k) * 3,
            int(self.settings.report_candidate_count) * 3,
            20,
        )

        video_ids: list[str] = []
        seen: set[str] = set()
        for chunk_index in merged_indices:
            video_id = str(chunk_catalog[chunk_index].get("video_id", "")).strip()
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            video_ids.append(video_id)
            if len(video_ids) >= candidate_pool:
                break

        return video_ids, {
            "bm25_attempted": bm25_attempted,
            "bm25_hit_count": len(bm25_indices),
            "keyword_hit_count": len(keyword_indices),
            "merged_hit_count": len(merged_indices),
        }

    def _score_video(
        self,
        indexer: VideoIndexer,
        video_entry: dict[str, Any],
        query_vector: dict[str, float],
        query_norm: float,
        query_tokens: set[str],
        key_tokens: set[str],
        topic_tokens: set[str],
        chapter_tokens: set[str],
    ) -> dict[str, Any]:
        weights = self.settings.score_weights.normalized()
        video_tokens = set(video_entry.get("tokens", []))

        best_chunk: dict[str, Any] | None = None
        best_chunk_score = -1.0
        best_semantic = 0.0
        best_keyword = 0.0
        best_hierarchy = 0.0

        for chunk in video_entry.get("chunks", []) or []:
            chunk_tokens = set(chunk.get("tokens", []))
            semantic_cosine = indexer.cosine_similarity(
                query_vector=query_vector,
                query_norm=query_norm,
                doc_vector=chunk.get("tfidf_vector", {}),
                doc_norm=float(chunk.get("tfidf_norm", 0.0)),
            )
            semantic_overlap = indexer.keyword_coverage_score(query_tokens, chunk_tokens)
            semantic_score = max(semantic_cosine, semantic_overlap * 0.92)

            keyword_score = indexer.keyword_coverage_score(key_tokens, chunk_tokens)
            hierarchy_score = indexer.hierarchy_consistency_score(
                topic_tokens=topic_tokens,
                chapter_tokens=chapter_tokens,
                doc_tokens=chunk_tokens,
            )
            blended = (
                weights.semantic * semantic_score
                + weights.keyword * keyword_score
                + weights.hierarchy * hierarchy_score
            )
            if blended > best_chunk_score:
                best_chunk_score = blended
                best_chunk = chunk
                best_semantic = semantic_score
                best_keyword = keyword_score
                best_hierarchy = hierarchy_score

        if best_chunk is None:
            best_chunk = {
                "text": str(video_entry.get("text", "")),
                "start": 0.0,
                "end": 0.0,
            }
            best_chunk_score = 0.0

        global_semantic = indexer.keyword_coverage_score(query_tokens, video_tokens)
        global_keyword = indexer.keyword_coverage_score(key_tokens, video_tokens)
        global_hierarchy = indexer.hierarchy_consistency_score(
            topic_tokens=topic_tokens,
            chapter_tokens=chapter_tokens,
            doc_tokens=video_tokens,
        )

        semantic_score = max(best_semantic, global_semantic)
        keyword_score = max(best_keyword, global_keyword)
        hierarchy_score = max(best_hierarchy, global_hierarchy)
        total_score = (
            weights.semantic * semantic_score
            + weights.keyword * keyword_score
            + weights.hierarchy * hierarchy_score
        )

        snippet = str(best_chunk.get("text", "")).strip()
        max_chars = max(80, int(self.settings.evidence_max_chars))
        snippet = snippet[:max_chars]
        start = float(best_chunk.get("start", 0.0))
        end = float(best_chunk.get("end", 0.0))

        return {
            "score": round(total_score, 4),
            "semantic_score": round(semantic_score, 4),
            "keyword_score": round(keyword_score, 4),
            "hierarchy_score": round(hierarchy_score, 4),
            "snippet": snippet,
            "start": round(start, 3),
            "end": round(end, 3),
            "timestamp": self._format_timestamp_range(start, end),
        }

    def _decide_match_status(self, score: float) -> str:
        high = float(self.settings.confidence.high_threshold)
        medium = float(self.settings.confidence.medium_threshold)
        if score >= high:
            return "matched"
        if score >= medium:
            return "needs_review"
        return "unmatched"

    def match(
        self,
        graph: dict[str, Any],
        legacy_graph_path: Path | str | None = None,  # compatibility parameter (unused)
    ) -> dict[str, Any]:
        _ = legacy_graph_path

        video_records = self._load_video_urls()
        collector = VideoTranscriptCollector(
            settings=self.settings,
            cache_dir=self.transcript_cache_dir,
            logger=self.logger,
        )
        collect_result = collector.collect(video_records)
        transcripts = collect_result.get("transcripts", [])

        indexer = VideoIndexer(max_chunk_chars=self.settings.max_chunk_chars)
        index_result = indexer.build(transcripts)
        indexed_videos = index_result.get("videos", [])
        video_by_id = {str(item.get("video_id", "")): item for item in indexed_videos}
        chunk_catalog = self._build_chunk_catalog(indexed_videos)

        updated_nodes: list[dict[str, Any]] = [dict(node) for node in graph.get("nodes", []) or []]
        updated_graph = dict(graph)
        updated_graph["nodes"] = updated_nodes

        contexts = build_concept_context(updated_graph)
        concept_nodes = [node for node in updated_nodes if str(node.get("node_type", "")) == "concept"]

        idf = index_result.get("idf", {})
        matched_count = 0
        needs_review_count = 0
        unmatched_count = 0
        matched_scores: list[float] = []
        top_scores: list[float] = []
        match_records: list[dict[str, Any]] = []

        bm25_enabled = BM25Okapi is not None
        bm25_used = 0
        keyword_recall_hits = 0
        bm25_recall_hits = 0

        for node in concept_nodes:
            concept_id = str(node.get("node_id", "")).strip()
            concept_name = str(node.get("name", "")).strip()
            context = contexts.get(concept_id, {})

            query_tokens = set(context.get("query_tokens", set()))
            keyword_tokens = set()
            for keyword in node.get("keywords", []) or []:
                keyword_tokens.update(tokenize(str(keyword)))
            keyword_tokens = keyword_tokens or set(query_tokens)

            topic_tokens = tokenize(str(context.get("topic_name", "")))
            chapter_tokens = tokenize(str(context.get("chapter_name", "")))
            expanded_tokens = self._expand_query_tokens(
                query_tokens=query_tokens,
                key_tokens=keyword_tokens,
                topic_tokens=topic_tokens,
                chapter_tokens=chapter_tokens,
            )

            recalled_video_ids, recall_stats = self._recall_video_ids(
                query_tokens=expanded_tokens,
                keyword_tokens=keyword_tokens,
                chunk_catalog=chunk_catalog,
            )
            if recall_stats.get("bm25_attempted"):
                bm25_used += 1
            bm25_recall_hits += int(recall_stats.get("bm25_hit_count", 0))
            keyword_recall_hits += int(recall_stats.get("keyword_hit_count", 0))

            if not recalled_video_ids:
                recalled_video_ids = list(video_by_id.keys())

            query_vector, query_norm = indexer.build_query_vector(expanded_tokens, idf)
            candidates: list[dict[str, Any]] = []
            for video_id in recalled_video_ids:
                video_entry = video_by_id.get(video_id)
                if video_entry is None:
                    continue
                score_result = self._score_video(
                    indexer=indexer,
                    video_entry=video_entry,
                    query_vector=query_vector,
                    query_norm=query_norm,
                    query_tokens=expanded_tokens,
                    key_tokens=keyword_tokens,
                    topic_tokens=topic_tokens,
                    chapter_tokens=chapter_tokens,
                )
                if score_result["score"] <= 0:
                    continue
                candidates.append(
                    {
                        "video_id": video_id,
                        "video_url": str(video_entry.get("url", "")),
                        "video_title": self._video_title(video_entry, concept_name),
                        "score": score_result["score"],
                        "semantic_score": score_result["semantic_score"],
                        "keyword_score": score_result["keyword_score"],
                        "hierarchy_score": score_result["hierarchy_score"],
                        "evidence_snippet": score_result["snippet"],
                        "evidence_start": score_result["start"],
                        "evidence_end": score_result["end"],
                        "evidence_timestamp": score_result["timestamp"],
                    }
                )

            candidates.sort(key=lambda item: item["score"], reverse=True)
            report_top_k = max(1, int(self.settings.report_candidate_count))
            rerank_top_k = max(1, int(self.settings.recall.rerank_top_k))
            selected_candidates = candidates[: max(report_top_k, rerank_top_k)]
            report_candidates = selected_candidates[:report_top_k]

            top_score = float(report_candidates[0]["score"]) if report_candidates else 0.0
            if top_score > 0:
                top_scores.append(top_score)
            decision = self._decide_match_status(top_score)

            resources = self._strip_video_resources(node)
            if decision == "matched" and report_candidates:
                best = report_candidates[0]
                resources.append(
                    {
                        "resource_id": str(best.get("video_id", "")) or f"video_{matched_count + 1:03d}",
                        "resource_type": "video",
                        "title": str(best.get("video_title", "")),
                        "url": str(best.get("video_url", "")),
                        "score": round(float(best.get("score", 0.0)), 3),
                        "match_method": "transcript_semantic_v2",
                        "provider": "video_url_transcript",
                        "confidence_level": "high",
                        "evidence_snippet": str(best.get("evidence_snippet", "")),
                        "evidence_start": float(best.get("evidence_start", 0.0)),
                        "evidence_end": float(best.get("evidence_end", 0.0)),
                        "evidence_timestamp": str(best.get("evidence_timestamp", "")),
                        "sub_scores": {
                            "semantic": float(best.get("semantic_score", 0.0)),
                            "keyword": float(best.get("keyword_score", 0.0)),
                            "hierarchy": float(best.get("hierarchy_score", 0.0)),
                        },
                    }
                )
                matched_count += 1
                matched_scores.append(top_score)
            elif decision == "needs_review":
                needs_review_count += 1
            else:
                unmatched_count += 1

            node["resources"] = resources
            node["resource_refs"] = rebuild_resource_refs(resources)

            match_records.append(
                {
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "topic_name": str(context.get("topic_name", "")),
                    "chapter_name": str(context.get("chapter_name", "")),
                    "decision": decision,
                    "top_score": round(top_score, 4),
                    "query_token_count": len(expanded_tokens),
                    "candidate_count": len(candidates),
                    "selected_video_url": str(report_candidates[0].get("video_url", "")) if report_candidates else "",
                    "selected_video_title": str(report_candidates[0].get("video_title", "")) if report_candidates else "",
                    "selected_evidence_timestamp": str(report_candidates[0].get("evidence_timestamp", "")) if report_candidates else "",
                    "candidates": report_candidates,
                }
            )

        concept_count = len(concept_nodes)
        match_rate = round((matched_count / concept_count * 100.0), 2) if concept_count else 0.0
        average_score = round(sum(matched_scores) / len(matched_scores), 4) if matched_scores else 0.0
        average_top_score = round(sum(top_scores) / len(top_scores), 4) if top_scores else 0.0

        transcript_stats = collect_result.get("stats", {})
        index_stats = index_result.get("stats", {})
        stats = {
            "concept_count": concept_count,
            "matched_concept_count": matched_count,
            "needs_review_count": needs_review_count,
            "unmatched_concept_count": unmatched_count,
            "video_match_rate_pct": match_rate,
            "avg_video_match_score": average_score,
            "avg_top_candidate_score": average_top_score,
            "video_url_count": len(video_records),
            "transcript_coverage_pct": float(transcript_stats.get("transcript_coverage_pct", 0.0)),
            "transcript_ok_count": int(transcript_stats.get("ok_count", 0)),
            "transcript_failed_count": int(transcript_stats.get("failed_count", 0)),
            "subtitle_success_count": int(transcript_stats.get("subtitle_success_count", 0)),
            "asr_success_count": int(transcript_stats.get("asr_success_count", 0)),
            "indexed_video_count": int(index_stats.get("indexed_video_count", 0)),
            "index_chunk_count": int(index_stats.get("chunk_count", 0)),
            "bm25_enabled": bm25_enabled,
            "bm25_used_for_concepts": bm25_used,
            "bm25_recall_hit_count": bm25_recall_hits,
            "keyword_recall_hit_count": keyword_recall_hits,
            "high_confidence_threshold": float(self.settings.confidence.high_threshold),
            "medium_confidence_threshold": float(self.settings.confidence.medium_threshold),
            "score_weights": {
                "semantic": float(self.settings.score_weights.semantic),
                "keyword": float(self.settings.score_weights.keyword),
                "hierarchy": float(self.settings.score_weights.hierarchy),
            },
            "settings_snapshot": ResourceMatchSettings(video=self.settings).to_snapshot(),
        }

        meta = dict(updated_graph.get("meta", {}) or {})
        resource_meta = dict(meta.get("resource_match", {}) or {})
        resource_meta["video"] = stats
        meta["resource_match"] = resource_meta
        updated_graph["meta"] = meta

        self._log(
            "info",
            "Video matching finished. transcript_coverage=%.2f%% match_rate=%.2f%% matched=%s/%s review=%s",
            stats["transcript_coverage_pct"],
            stats["video_match_rate_pct"],
            matched_count,
            concept_count,
            needs_review_count,
        )
        return {
            "graph": updated_graph,
            "stats": stats,
            "transcripts": transcripts,
            "index_stats": index_stats,
            "matches": match_records,
        }
