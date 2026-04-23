from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from KnowledgeGraph.src.resource_match.utils import normalize_text, token_overlap_score, tokenize

_EN_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+\-]{1,31}", re.IGNORECASE)
_ZH_CHUNK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_TEXT_SPLIT_RE = re.compile(r"[。！？!?；;，,]")
_NOISE_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "课程",
    "学习",
    "知识",
    "内容",
    "目标",
    "介绍",
    "比如",
    "我们",
}


@dataclass
class VideoChunk:
    text: str
    start: float
    end: float
    token_list: list[str]
    token_set: set[str]


class VideoIndexer:
    """Build transcript index with token, BM25-ready corpus and sparse vectors."""

    def __init__(self, max_chunk_chars: int = 260, keyword_top_n: int = 12) -> None:
        self.max_chunk_chars = max(120, int(max_chunk_chars))
        self.keyword_top_n = max(4, int(keyword_top_n))

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _tokenize_list(text: str) -> list[str]:
        value = normalize_text(text)
        if not value:
            return []

        tokens: list[str] = []
        for token in _EN_TOKEN_RE.findall(value):
            lowered = token.lower()
            if len(lowered) < 2 or lowered in _NOISE_WORDS:
                continue
            tokens.append(lowered)

        for chunk in _ZH_CHUNK_RE.findall(value):
            clean_chunk = chunk.strip()
            if len(clean_chunk) < 2:
                continue
            if clean_chunk not in _NOISE_WORDS:
                tokens.append(clean_chunk)
            for size in (2, 3):
                if len(clean_chunk) < size:
                    continue
                for index in range(0, len(clean_chunk) - size + 1):
                    ngram = clean_chunk[index : index + size]
                    if ngram not in _NOISE_WORDS:
                        tokens.append(ngram)
        return tokens

    def _chunk_segments(self, segments: list[dict[str, Any]]) -> list[VideoChunk]:
        chunks: list[VideoChunk] = []
        buffer: list[str] = []
        start = 0.0
        end = 0.0

        for item in segments:
            text = str(item.get("text", "")).strip()
            if not text:
                continue

            seg_start = self._safe_float(item.get("start"), end)
            seg_end = self._safe_float(item.get("end"), seg_start)
            if not buffer:
                start = seg_start
            buffer.append(text)
            end = seg_end

            merged = " ".join(buffer).strip()
            if len(merged) < self.max_chunk_chars:
                continue

            token_list = self._tokenize_list(merged)
            token_set = set(token_list) or tokenize(merged)
            chunks.append(
                VideoChunk(
                    text=merged,
                    start=start,
                    end=end,
                    token_list=token_list,
                    token_set=token_set,
                )
            )
            buffer = []

        tail = " ".join(buffer).strip()
        if tail:
            token_list = self._tokenize_list(tail)
            token_set = set(token_list) or tokenize(tail)
            chunks.append(
                VideoChunk(
                    text=tail,
                    start=start,
                    end=end,
                    token_list=token_list,
                    token_set=token_set,
                )
            )
        return chunks

    def _chunk_plain_text(self, text: str) -> list[VideoChunk]:
        parts = [part.strip() for part in _TEXT_SPLIT_RE.split(text) if part.strip()]
        chunks: list[VideoChunk] = []
        buffer: list[str] = []

        for part in parts:
            buffer.append(part)
            merged = " ".join(buffer).strip()
            if len(merged) < self.max_chunk_chars:
                continue
            token_list = self._tokenize_list(merged)
            token_set = set(token_list) or tokenize(merged)
            chunks.append(
                VideoChunk(
                    text=merged,
                    start=0.0,
                    end=0.0,
                    token_list=token_list,
                    token_set=token_set,
                )
            )
            buffer = []

        tail = " ".join(buffer).strip()
        if tail:
            token_list = self._tokenize_list(tail)
            token_set = set(token_list) or tokenize(tail)
            chunks.append(
                VideoChunk(
                    text=tail,
                    start=0.0,
                    end=0.0,
                    token_list=token_list,
                    token_set=token_set,
                )
            )
        return chunks

    @staticmethod
    def _extract_keywords(token_list: list[str], top_n: int) -> list[str]:
        if not token_list:
            return []
        counter = Counter(token_list)
        keywords = [item for item, _ in counter.most_common(max(1, top_n))]
        return keywords

    @staticmethod
    def _compute_idf(documents: list[list[str]]) -> dict[str, float]:
        if not documents:
            return {}
        total_docs = len(documents)
        doc_freq: Counter[str] = Counter()
        for doc in documents:
            doc_freq.update(set(doc))
        idf: dict[str, float] = {}
        for token, freq in doc_freq.items():
            idf[token] = math.log((1 + total_docs) / (1 + freq)) + 1.0
        return idf

    @staticmethod
    def _build_tfidf_vector(token_list: list[str], idf: dict[str, float]) -> tuple[dict[str, float], float]:
        if not token_list:
            return {}, 0.0
        counter = Counter(token_list)
        max_tf = max(counter.values()) if counter else 1
        vector: dict[str, float] = {}
        for token, freq in counter.items():
            tf = 0.5 + 0.5 * (freq / max_tf)
            vector[token] = tf * idf.get(token, 1.0)
        norm = math.sqrt(sum(value * value for value in vector.values()))
        return vector, norm

    @staticmethod
    def build_query_vector(tokens: set[str], idf: dict[str, float]) -> tuple[dict[str, float], float]:
        if not tokens:
            return {}, 0.0
        vector = {token: idf.get(token, 1.0) for token in tokens}
        norm = math.sqrt(sum(value * value for value in vector.values()))
        return vector, norm

    @staticmethod
    def cosine_similarity(
        query_vector: dict[str, float],
        query_norm: float,
        doc_vector: dict[str, float],
        doc_norm: float,
    ) -> float:
        if not query_vector or not doc_vector or query_norm <= 0 or doc_norm <= 0:
            return 0.0
        dot = 0.0
        for token, q_value in query_vector.items():
            dot += q_value * doc_vector.get(token, 0.0)
        if dot <= 0:
            return 0.0
        return dot / (query_norm * doc_norm)

    @staticmethod
    def keyword_coverage_score(query_tokens: set[str], doc_tokens: set[str]) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        return len(query_tokens.intersection(doc_tokens)) / max(1, len(query_tokens))

    @staticmethod
    def hierarchy_consistency_score(
        topic_tokens: set[str],
        chapter_tokens: set[str],
        doc_tokens: set[str],
    ) -> float:
        topic_score = token_overlap_score(topic_tokens, doc_tokens) if topic_tokens else 0.0
        chapter_score = token_overlap_score(chapter_tokens, doc_tokens) if chapter_tokens else 0.0
        return max(topic_score, chapter_score)

    def build(self, transcripts: list[dict[str, Any]]) -> dict[str, Any]:
        videos: list[dict[str, Any]] = []
        all_chunk_docs: list[list[str]] = []
        chunk_count = 0
        chunk_char_sum = 0

        for item in transcripts:
            if not item.get("ok"):
                continue
            text = str(item.get("transcript_text", "")).strip()
            if not text:
                continue

            segments = item.get("segments", [])
            if not isinstance(segments, list):
                segments = []

            chunks = self._chunk_segments(segments) if segments else []
            if not chunks:
                chunks = self._chunk_plain_text(text)
            if not chunks:
                token_list = self._tokenize_list(text)
                token_set = set(token_list) or tokenize(text)
                chunks = [
                    VideoChunk(
                        text=text[: self.max_chunk_chars * 2],
                        start=0.0,
                        end=0.0,
                        token_list=token_list,
                        token_set=token_set,
                    )
                ]

            chunk_payloads: list[dict[str, Any]] = []
            all_video_token_list: list[str] = []
            all_video_token_set: set[str] = set()
            for index, chunk in enumerate(chunks, start=1):
                all_chunk_docs.append(chunk.token_list)
                chunk_count += 1
                chunk_char_sum += len(chunk.text)
                all_video_token_list.extend(chunk.token_list)
                all_video_token_set.update(chunk.token_set)
                chunk_payloads.append(
                    {
                        "chunk_id": f"{item.get('video_id', '')}_chunk_{index:04d}",
                        "text": chunk.text,
                        "start": round(chunk.start, 3),
                        "end": round(chunk.end, 3),
                        "token_list": list(chunk.token_list),
                        "tokens": sorted(chunk.token_set),
                    }
                )

            video_token_set = all_video_token_set or tokenize(text)
            if not all_video_token_list:
                all_video_token_list = self._tokenize_list(text)
            videos.append(
                {
                    "video_id": str(item.get("video_id", "")),
                    "url": str(item.get("url", "")),
                    "title": str(item.get("title", "")),
                    "text": text,
                    "tokens": sorted(video_token_set),
                    "token_list": list(all_video_token_list),
                    "keywords": self._extract_keywords(all_video_token_list, self.keyword_top_n),
                    "chunks": chunk_payloads,
                }
            )

        idf = self._compute_idf(all_chunk_docs)
        total_vectorized_chunks = 0
        for video in videos:
            for chunk in video.get("chunks", []):
                vector, norm = self._build_tfidf_vector(chunk.get("token_list", []), idf)
                chunk["tfidf_vector"] = vector
                chunk["tfidf_norm"] = norm
                total_vectorized_chunks += 1

        return {
            "videos": videos,
            "idf": idf,
            "stats": {
                "indexed_video_count": len(videos),
                "chunk_count": chunk_count,
                "vectorized_chunk_count": total_vectorized_chunks,
                "idf_token_count": len(idf),
                "avg_chunk_chars": round(chunk_char_sum / chunk_count, 2) if chunk_count else 0.0,
            },
        }
