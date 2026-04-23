from __future__ import annotations

import re
from collections import Counter
from typing import Any

from KnowledgeGraph.src.course_profile import CourseProfile
from KnowledgeGraph.src.kg_text_rules import analyze_candidate, is_noise_keyword, normalize_token


class TextCleaner:
    """Normalize and segment parsed script text for downstream KG extraction."""

    def __init__(
        self,
        logger=None,
        min_segment_len: int = 8,
        course_profile: CourseProfile | None = None,
    ) -> None:
        self.logger = logger
        self.min_segment_len = min_segment_len
        self.course_profile = course_profile or CourseProfile.default()

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    @staticmethod
    def _normalize_text(text: str) -> str:
        cleaned = text.replace("\u3000", " ")
        cleaned = cleaned.replace("\t", " ")
        cleaned = re.sub(r"\r\n?", "\n", cleaned)
        cleaned = re.sub(r"[ ]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{2,}", "\n", cleaned)
        return cleaned.strip()

    def _segment_text(self, text: str) -> list[str]:
        if not text:
            return []

        text = re.sub(r"([。！？!?；;])", r"\1\n", text)
        candidates = [part.strip() for part in text.split("\n") if part.strip()]

        segments: list[str] = []
        buffer = ""
        for piece in candidates:
            if len(piece) >= self.min_segment_len:
                if buffer:
                    segments.append(buffer)
                    buffer = ""
                segments.append(piece)
            else:
                buffer = f"{buffer} {piece}".strip()
                if len(buffer) >= self.min_segment_len:
                    segments.append(buffer)
                    buffer = ""
        if buffer:
            segments.append(buffer)

        return segments

    def _extract_keywords(self, text: str, limit: int = 12) -> list[str]:
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
            "然后",
            "就是",
            "可以",
            "进行",
            "由于",
            "因此",
            "主要",
            "其中",
            "如果",
            "通过",
            "如下",
            "如上",
            "本次",
            "课程",
            "讲稿",
        }
        stop_words_lower = {word.lower() for word in stop_words}

        counter: Counter[str] = Counter()
        for token in tokens:
            normalized = normalize_token(token)
            if not normalized:
                continue
            if normalized.lower() in stop_words_lower:
                continue
            if is_noise_keyword(normalized, self.course_profile):
                continue
            analysis = analyze_candidate(
                normalized,
                self.course_profile,
                evidence_count=1,
                occurs_as_subject=False,
                occurs_as_object=False,
            )
            if analysis.rejected and analysis.reject_reason in {
                "hard_block_term",
                "abstract_term",
                "action_term",
                "relation_term",
                "sentence_fragment",
                "measure_fragment",
                "identifier_fragment",
            }:
                continue
            counter[normalized] += 1

        return [token for token, _ in counter.most_common(limit)]

    @staticmethod
    def _chapter_tag(lesson_no: int | None, section_no: int | None) -> str:
        if lesson_no is None or section_no is None:
            return "unknown"
        return f"{lesson_no}-{section_no}"

    def clean(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        cleaned_documents: list[dict[str, Any]] = []
        segment_records: list[dict[str, Any]] = []

        for document in documents:
            raw_text = str(document.get("raw_text", ""))
            normalized = self._normalize_text(raw_text)
            segments = self._segment_text(normalized)
            if not segments and normalized:
                segments = [normalized]

            lesson_no = document.get("lesson_no")
            section_no = document.get("section_no")
            chapter_tag = self._chapter_tag(lesson_no, section_no)
            keywords = self._extract_keywords(normalized)

            cleaned_doc = {
                "doc_id": document.get("doc_id"),
                "source_file": document.get("source_file"),
                "source_path": document.get("source_path"),
                "title": document.get("title"),
                "topic": document.get("topic"),
                "lesson_no": lesson_no,
                "section_no": section_no,
                "chapter_tag": chapter_tag,
                "char_count": len(normalized),
                "segment_count": len(segments),
                "keywords": keywords,
                "cleaned_text": normalized,
            }
            cleaned_documents.append(cleaned_doc)

            for idx, text in enumerate(segments, start=1):
                segment_records.append(
                    {
                        "segment_id": f"{document.get('doc_id')}_seg_{idx:03d}",
                        "doc_id": document.get("doc_id"),
                        "source_file": document.get("source_file"),
                        "title": document.get("title"),
                        "topic": document.get("topic"),
                        "lesson_no": lesson_no,
                        "section_no": section_no,
                        "chapter_tag": chapter_tag,
                        "segment_index": idx,
                        "text": text,
                        "char_count": len(text),
                    }
                )

        stats = {
            "document_count": len(cleaned_documents),
            "segment_count": len(segment_records),
            "avg_segments_per_doc": round(
                (len(segment_records) / len(cleaned_documents)), 2
            )
            if cleaned_documents
            else 0.0,
        }
        self._log(
            "info",
            "Text cleaning finished. docs=%s segments=%s avg_segments_per_doc=%s",
            stats["document_count"],
            stats["segment_count"],
            stats["avg_segments_per_doc"],
        )
        return {
            "documents": cleaned_documents,
            "segments": segment_records,
            "stats": stats,
        }
