from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ASRSettings:
    enabled: bool = False
    model_size: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    max_audio_seconds: int = 900
    hf_endpoint: str = "https://hf-mirror.com"
    download_root: str = ""


@dataclass
class VideoScoreWeights:
    semantic: float = 0.45
    keyword: float = 0.35
    hierarchy: float = 0.20

    def normalized(self) -> "VideoScoreWeights":
        values = [self.semantic, self.keyword, self.hierarchy]
        total = sum(max(0.0, float(value)) for value in values)
        if total <= 0:
            return VideoScoreWeights()
        return VideoScoreWeights(
            semantic=max(0.0, self.semantic) / total,
            keyword=max(0.0, self.keyword) / total,
            hierarchy=max(0.0, self.hierarchy) / total,
        )


@dataclass
class VideoRecallSettings:
    bm25_top_k: int = 30
    keyword_top_k: int = 30
    rerank_top_k: int = 8
    min_bm25_score: float = 0.0


@dataclass
class VideoConfidenceSettings:
    high_threshold: float = 0.48
    medium_threshold: float = 0.33


@dataclass
class VideoQueryExpansionSettings:
    enabled: bool = True
    include_topic_chapter_terms: bool = True
    synonym_map: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class VideoQualityTargets:
    transcript_coverage_pct: float = 85.0
    match_rate_pct: float = 40.0


@dataclass
class VideoMatchSettings:
    request_timeout_sec: int = 8
    max_workers: int = 8
    min_transcript_chars: int = 80
    transcript_cache_subdir: str = "video_transcripts"
    prefer_https_domains: list[str] = field(
        default_factory=lambda: [
            "mooc2vod.stu.126.net",
        ]
    )
    force_refresh: bool = False
    max_chunk_chars: int = 260
    evidence_max_chars: int = 240
    report_candidate_count: int = 5
    score_weights: VideoScoreWeights = field(default_factory=VideoScoreWeights)
    recall: VideoRecallSettings = field(default_factory=VideoRecallSettings)
    confidence: VideoConfidenceSettings = field(default_factory=VideoConfidenceSettings)
    query_expansion: VideoQueryExpansionSettings = field(default_factory=VideoQueryExpansionSettings)
    quality_targets: VideoQualityTargets = field(default_factory=VideoQualityTargets)
    asr: ASRSettings = field(default_factory=ASRSettings)


@dataclass
class ResourceMatchSettings:
    video: VideoMatchSettings = field(default_factory=VideoMatchSettings)

    @classmethod
    def from_path(cls, path: Path | str | None) -> "ResourceMatchSettings":
        settings = cls()
        if path is None:
            return settings

        file_path = Path(path)
        if not file_path.exists():
            return settings

        payload = _load_yaml(file_path)
        if not isinstance(payload, dict):
            return settings

        video_payload = payload.get("video", {})
        if not isinstance(video_payload, dict):
            return settings

        asr_payload = _as_dict(video_payload.get("asr"))
        recall_payload = _as_dict(video_payload.get("recall"))
        score_payload = _as_dict(video_payload.get("score_weights"))
        confidence_payload = _as_dict(video_payload.get("confidence"))
        expansion_payload = _as_dict(video_payload.get("query_expansion"))
        quality_payload = _as_dict(video_payload.get("quality_targets"))

        legacy_threshold = _as_float(
            video_payload.get("score_threshold"),
            settings.video.confidence.high_threshold,
        )
        legacy_top_k = _as_int(
            video_payload.get("top_k_candidates"),
            settings.video.recall.rerank_top_k,
        )

        asr = ASRSettings(
            enabled=_as_bool(asr_payload.get("enabled"), settings.video.asr.enabled),
            model_size=str(asr_payload.get("model_size", settings.video.asr.model_size)),
            device=str(asr_payload.get("device", settings.video.asr.device)),
            compute_type=str(asr_payload.get("compute_type", settings.video.asr.compute_type)),
            max_audio_seconds=_as_int(
                asr_payload.get("max_audio_seconds"),
                settings.video.asr.max_audio_seconds,
            ),
            hf_endpoint=str(asr_payload.get("hf_endpoint", settings.video.asr.hf_endpoint)),
            download_root=str(asr_payload.get("download_root", settings.video.asr.download_root)),
        )

        score_weights = VideoScoreWeights(
            semantic=_as_float(score_payload.get("semantic"), settings.video.score_weights.semantic),
            keyword=_as_float(score_payload.get("keyword"), settings.video.score_weights.keyword),
            hierarchy=_as_float(score_payload.get("hierarchy"), settings.video.score_weights.hierarchy),
        ).normalized()

        confidence = VideoConfidenceSettings(
            high_threshold=_as_float(confidence_payload.get("high_threshold"), legacy_threshold),
            medium_threshold=_as_float(
                confidence_payload.get("medium_threshold"),
                settings.video.confidence.medium_threshold,
            ),
        )
        if confidence.medium_threshold > confidence.high_threshold:
            confidence.medium_threshold = confidence.high_threshold

        query_expansion = VideoQueryExpansionSettings(
            enabled=_as_bool(expansion_payload.get("enabled"), settings.video.query_expansion.enabled),
            include_topic_chapter_terms=_as_bool(
                expansion_payload.get("include_topic_chapter_terms"),
                settings.video.query_expansion.include_topic_chapter_terms,
            ),
            synonym_map=_merge_synonym_map(
                _default_synonym_map(),
                _as_str_list_dict(expansion_payload.get("synonym_map")),
            ),
        )

        recall = VideoRecallSettings(
            bm25_top_k=_as_int(recall_payload.get("bm25_top_k"), settings.video.recall.bm25_top_k),
            keyword_top_k=_as_int(
                recall_payload.get("keyword_top_k"),
                settings.video.recall.keyword_top_k,
            ),
            rerank_top_k=_as_int(recall_payload.get("rerank_top_k"), legacy_top_k),
            min_bm25_score=_as_float(
                recall_payload.get("min_bm25_score"),
                settings.video.recall.min_bm25_score,
            ),
        )

        quality_targets = VideoQualityTargets(
            transcript_coverage_pct=_as_float(
                quality_payload.get("transcript_coverage_pct"),
                settings.video.quality_targets.transcript_coverage_pct,
            ),
            match_rate_pct=_as_float(
                quality_payload.get("match_rate_pct"),
                settings.video.quality_targets.match_rate_pct,
            ),
        )

        settings.video = VideoMatchSettings(
            request_timeout_sec=_as_int(
                video_payload.get("request_timeout_sec"),
                settings.video.request_timeout_sec,
            ),
            max_workers=_as_int(video_payload.get("max_workers"), settings.video.max_workers),
            min_transcript_chars=_as_int(
                video_payload.get("min_transcript_chars"),
                settings.video.min_transcript_chars,
            ),
            transcript_cache_subdir=str(
                video_payload.get("transcript_cache_subdir", settings.video.transcript_cache_subdir)
            ),
            prefer_https_domains=_as_str_list(
                video_payload.get("prefer_https_domains", settings.video.prefer_https_domains)
            ),
            force_refresh=_as_bool(video_payload.get("force_refresh"), settings.video.force_refresh),
            max_chunk_chars=_as_int(video_payload.get("max_chunk_chars"), settings.video.max_chunk_chars),
            evidence_max_chars=_as_int(
                video_payload.get("evidence_max_chars"),
                settings.video.evidence_max_chars,
            ),
            report_candidate_count=_as_int(
                video_payload.get("report_candidate_count"),
                settings.video.report_candidate_count,
            ),
            score_weights=score_weights,
            recall=recall,
            confidence=confidence,
            query_expansion=query_expansion,
            quality_targets=quality_targets,
            asr=asr,
        )
        return settings

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "video": {
                "request_timeout_sec": self.video.request_timeout_sec,
                "max_workers": self.video.max_workers,
                "min_transcript_chars": self.video.min_transcript_chars,
                "transcript_cache_subdir": self.video.transcript_cache_subdir,
                "prefer_https_domains": list(self.video.prefer_https_domains),
                "force_refresh": self.video.force_refresh,
                "max_chunk_chars": self.video.max_chunk_chars,
                "evidence_max_chars": self.video.evidence_max_chars,
                "report_candidate_count": self.video.report_candidate_count,
                "score_weights": {
                    "semantic": self.video.score_weights.semantic,
                    "keyword": self.video.score_weights.keyword,
                    "hierarchy": self.video.score_weights.hierarchy,
                },
                "recall": {
                    "bm25_top_k": self.video.recall.bm25_top_k,
                    "keyword_top_k": self.video.recall.keyword_top_k,
                    "rerank_top_k": self.video.recall.rerank_top_k,
                    "min_bm25_score": self.video.recall.min_bm25_score,
                },
                "confidence": {
                    "high_threshold": self.video.confidence.high_threshold,
                    "medium_threshold": self.video.confidence.medium_threshold,
                },
                "query_expansion": {
                    "enabled": self.video.query_expansion.enabled,
                    "include_topic_chapter_terms": self.video.query_expansion.include_topic_chapter_terms,
                    "synonym_map_size": len(self.video.query_expansion.synonym_map),
                },
                "quality_targets": {
                    "transcript_coverage_pct": self.video.quality_targets.transcript_coverage_pct,
                    "match_rate_pct": self.video.quality_targets.match_rate_pct,
                },
                "asr": {
                    "enabled": self.video.asr.enabled,
                    "model_size": self.video.asr.model_size,
                    "device": self.video.asr.device,
                    "compute_type": self.video.asr.compute_type,
                    "max_audio_seconds": self.video.asr.max_audio_seconds,
                    "hf_endpoint": self.video.asr.hf_endpoint,
                    "download_root": self.video.asr.download_root,
                },
            }
        }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        values = [str(item).strip() for item in value]
    else:
        values = [str(value).strip()]

    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(item)
    return deduped


def _as_str_list_dict(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    mapped: dict[str, list[str]] = {}
    for raw_key, raw_value in value.items():
        key = str(raw_key).strip().lower()
        if not key:
            continue
        values = _as_str_list(raw_value)
        if not values:
            continue
        mapped[key] = values
    return mapped


def _merge_synonym_map(
    base_map: dict[str, list[str]],
    override_map: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {key: list(values) for key, values in base_map.items()}
    for key, values in override_map.items():
        existing = set(item.lower() for item in merged.get(key, []))
        if key not in merged:
            merged[key] = []
        for item in values:
            lowered = item.lower()
            if lowered in existing:
                continue
            merged[key].append(item)
            existing.add(lowered)
    return merged


def _default_synonym_map() -> dict[str, list[str]]:
    return {
        "大数据": ["big data"],
        "数据挖掘": ["data mining"],
        "机器学习": ["machine learning"],
        "深度学习": ["deep learning"],
        "分布式": ["distributed"],
        "流计算": ["stream processing", "stream computing"],
        "图计算": ["graph processing", "graph computing"],
        "推荐系统": ["recommender system", "recommendation"],
        "nosql": ["non-relational database", "key value", "column family", "document database"],
        "hadoop": ["hdfs", "mapreduce", "yarn"],
        "hdfs": ["hadoop distributed file system", "namenode", "datanode"],
        "mapreduce": ["map reduce"],
        "spark": ["rdd", "spark sql", "spark mllib", "structured streaming"],
        "mllib": ["spark mllib", "machine learning library"],
        "rdd": ["resilient distributed dataset"],
        "etl": ["extract transform load"],
        "olap": ["online analytical processing"],
        "mpp": ["massively parallel processing"],
        "tensorflow": ["keras", "gpu", "tpu"],
        "cnn": ["convolutional neural network"],
        "rnn": ["recurrent neural network"],
        "svm": ["support vector machine"],
        "api": ["application programming interface"],
        "sql": ["structured query language"],
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = yaml.safe_load(content)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}
