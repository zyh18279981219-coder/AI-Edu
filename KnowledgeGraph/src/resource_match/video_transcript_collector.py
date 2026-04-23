from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import requests

from KnowledgeGraph.src.resource_match.asr_transcriber import ASRTranscriber
from KnowledgeGraph.src.resource_match.settings import VideoMatchSettings

_TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}(?:[.,]\d{1,3})?)"
)


class VideoTranscriptCollector:
    """Collect subtitle/transcript text from video URLs."""

    def __init__(
        self,
        settings: VideoMatchSettings,
        cache_dir: Path | str,
        logger=None,
    ) -> None:
        self.settings = settings
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self._session = requests.Session()
        self._asr = ASRTranscriber(settings.asr, logger=logger)
        self._asr_lock = Lock()
        self._prefer_https_domains = self._normalize_domain_list(settings.prefer_https_domains)

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    def _cache_path(self, video_id: str) -> Path:
        return self.cache_dir / f"{video_id}.json"

    @staticmethod
    def _normalize_domain_list(domains: list[str] | None) -> tuple[str, ...]:
        if not domains:
            return tuple()
        normalized: list[str] = []
        seen: set[str] = set()
        for item in domains:
            value = str(item or "").strip().lower().strip(".")
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return tuple(normalized)

    def _should_prefer_https(self, host: str) -> bool:
        host_lower = str(host or "").strip().lower().strip(".")
        if not host_lower:
            return False
        for domain in self._prefer_https_domains:
            if host_lower == domain or host_lower.endswith(f".{domain}"):
                return True
        return False

    def _normalize_video_url(self, url: str) -> str:
        parsed = urlparse(str(url or ""))
        if parsed.scheme.lower() != "http":
            return str(url or "")
        host = str(parsed.hostname or "").strip().lower()
        if not self._should_prefer_https(host):
            return str(url or "")
        return urlunparse(parsed._replace(scheme="https"))

    def _read_cache(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    @staticmethod
    def _should_reuse_failed_cache(payload: dict[str, Any]) -> bool:
        if payload.get("ok"):
            return True
        error_text = str(payload.get("error", "")).strip().lower()
        if not error_text:
            return False
        non_retryable_tags = {
            "empty_url",
            "transcript_too_short",
        }
        return any(tag in error_text for tag in non_retryable_tags)

    def _write_cache(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _http_get_text(self, url: str) -> str:
        timeout = max(2, int(self.settings.request_timeout_sec))
        headers = {"User-Agent": "Mozilla/5.0 AI-Edu-KG/1.0"}
        last_exc: Exception | None = None
        for candidate in self._iter_fetch_candidates(url):
            try:
                response = self._session.get(
                    candidate,
                    timeout=timeout,
                    headers=headers,
                )
                response.raise_for_status()
                response.encoding = response.encoding or "utf-8"
                return response.text
            except Exception as exc:
                last_exc = exc
                continue

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("no_fetch_candidate_url")

    @staticmethod
    def _to_https_url(url: str) -> str:
        parsed = urlparse(str(url or ""))
        if parsed.scheme.lower() != "http":
            return str(url or "")
        https_parsed = parsed._replace(scheme="https")
        return urlunparse(https_parsed)

    def _iter_fetch_candidates(self, url: str) -> list[str]:
        original = str(url or "").strip()
        normalized = self._normalize_video_url(original)
        https_url = self._to_https_url(original)

        ordered: list[str] = []
        for candidate in (normalized, original, https_url):
            value = str(candidate or "").strip()
            if not value or value in ordered:
                continue
            ordered.append(value)
        return ordered

    @staticmethod
    def _canonicalize_url(url: str) -> str:
        parsed = urlparse(str(url or ""))
        normalized = parsed._replace(
            scheme=str(parsed.scheme or "").lower(),
            netloc=str(parsed.netloc or "").lower(),
        )
        return urlunparse(normalized)

    def _dedupe_urls(self, urls: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for item in urls:
            canonical = self._canonicalize_url(item)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            ordered.append(item)
        return ordered

    @staticmethod
    def _extract_attribute(line: str, key: str) -> str:
        pattern = re.compile(rf'{re.escape(key)}="([^"]+)"')
        matched = pattern.search(line)
        if not matched:
            return ""
        return matched.group(1).strip()

    def _parse_m3u8_for_candidates(self, playlist_text: str, base_url: str) -> list[str]:
        candidates: list[str] = []
        for raw in playlist_text.splitlines():
            line = raw.strip()
            if not line:
                continue

            if line.startswith("#EXT-X-MEDIA") and "TYPE=SUBTITLES" in line:
                uri = self._extract_attribute(line, "URI")
                if uri:
                    candidates.append(urljoin(base_url, uri))
                continue

            if line.startswith("#"):
                continue

            lowered = line.lower()
            if lowered.endswith(".vtt") or lowered.endswith(".srt") or lowered.endswith(".m3u8"):
                candidates.append(urljoin(base_url, line))
        return candidates

    @staticmethod
    def _parse_timestamp(value: str) -> float:
        text = value.strip().replace(",", ".")
        items = text.split(":")
        if len(items) != 3:
            return 0.0
        try:
            hours = float(items[0])
            minutes = float(items[1])
            seconds = float(items[2])
        except ValueError:
            return 0.0
        return hours * 3600.0 + minutes * 60.0 + seconds

    def _parse_subtitle_text(self, text: str) -> dict[str, Any]:
        lines = [line.rstrip("\n\r") for line in text.splitlines()]
        cues: list[dict[str, Any]] = []
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            if not line:
                index += 1
                continue

            timestamp_match = _TIMESTAMP_RE.search(line)
            if not timestamp_match:
                index += 1
                continue

            start = self._parse_timestamp(timestamp_match.group("start"))
            end = self._parse_timestamp(timestamp_match.group("end"))
            index += 1

            parts: list[str] = []
            while index < len(lines):
                current = lines[index].strip()
                if not current:
                    break
                if _TIMESTAMP_RE.search(current):
                    break
                if current.isdigit():
                    index += 1
                    continue
                parts.append(current)
                index += 1

            merged = re.sub(r"<[^>]+>", " ", " ".join(parts)).strip()
            if merged:
                cues.append(
                    {
                        "start": round(start, 3),
                        "end": round(end, 3),
                        "text": merged,
                    }
                )
            index += 1

        transcript_text = "\n".join(item["text"] for item in cues).strip()
        return {
            "ok": bool(transcript_text),
            "text": transcript_text,
            "segments": cues,
        }

    def _fetch_subtitle_transcript(self, video_url: str) -> dict[str, Any]:
        root_url = self._normalize_video_url(video_url)
        root_text = self._http_get_text(root_url)
        subtitle_candidates = self._dedupe_urls(self._parse_m3u8_for_candidates(root_text, root_url))

        visited: set[str] = set()
        pending: list[str] = subtitle_candidates[:]
        if root_url.lower().endswith(".vtt") or root_url.lower().endswith(".srt"):
            pending.insert(0, root_url)

        while pending:
            candidate = pending.pop(0)
            candidate_key = self._canonicalize_url(candidate)
            if candidate_key in visited:
                continue
            visited.add(candidate_key)

            try:
                body = self._http_get_text(candidate)
            except Exception:
                continue

            lowered = candidate.lower()
            if lowered.endswith(".m3u8"):
                nested = self._dedupe_urls(self._parse_m3u8_for_candidates(body, candidate))
                pending.extend(nested)
                continue

            parsed = self._parse_subtitle_text(body)
            if parsed["ok"]:
                return {
                    "ok": True,
                    "error": "",
                    "text": parsed["text"],
                    "segments": parsed["segments"],
                    "meta": {
                        "method": "subtitle",
                        "subtitle_url": candidate,
                        "segment_count": len(parsed["segments"]),
                    },
                }

        return {
            "ok": False,
            "error": "subtitle_not_found_or_empty",
            "text": "",
            "segments": [],
            "meta": {"method": "subtitle"},
        }

    def _collect_one(self, item: dict[str, Any]) -> dict[str, Any]:
        video_id = str(item.get("video_id", "")).strip()
        url = str(item.get("url", "")).strip()
        normalized_url = self._normalize_video_url(url)
        title = str(item.get("title", "")).strip()
        cache_path = self._cache_path(video_id or "unknown")

        if not self.settings.force_refresh:
            cached = self._read_cache(cache_path)
            if cached is not None and str(cached.get("url", "")).strip() == url:
                cached.setdefault("meta", {})
                if str(cached.get("meta", {}).get("normalized_url", "")).strip() != normalized_url:
                    cached["meta"]["normalized_url"] = normalized_url
                    self._write_cache(cache_path, cached)
                if self._should_reuse_failed_cache(cached):
                    return cached
                self._log(
                    "info",
                    "Retry transcript collection for cached failed item: video_id=%s error=%s",
                    video_id,
                    str(cached.get("error", "")),
                )

        payload: dict[str, Any] = {
            "video_id": video_id,
            "url": url,
            "title": title,
            "ok": False,
            "error": "",
            "transcript_text": "",
            "segments": [],
            "meta": {"method": "", "generated_at": datetime.now().isoformat()},
        }

        if not url:
            payload["error"] = "empty_url"
            payload["meta"]["normalized_url"] = normalized_url
            self._write_cache(cache_path, payload)
            return payload

        try:
            subtitle_result = self._fetch_subtitle_transcript(normalized_url)
            if subtitle_result.get("ok"):
                payload["ok"] = True
                payload["transcript_text"] = str(subtitle_result.get("text", "")).strip()
                payload["segments"] = subtitle_result.get("segments", []) or []
                payload["meta"] = subtitle_result.get("meta", {})
            else:
                payload["error"] = str(subtitle_result.get("error", "subtitle_unavailable"))
        except Exception as exc:
            payload["error"] = f"subtitle_fetch_failed:{exc}"

        if not payload["ok"] and self.settings.asr.enabled:
            try:
                with self._asr_lock:
                    asr_result = self._asr.transcribe(normalized_url)
                if asr_result.get("ok"):
                    payload["ok"] = True
                    payload["transcript_text"] = str(asr_result.get("text", "")).strip()
                    payload["segments"] = asr_result.get("segments", []) or []
                    payload["meta"] = asr_result.get("meta", {})
                    payload["error"] = ""
                else:
                    payload["error"] = str(asr_result.get("error", payload["error"] or "asr_failed"))
            except Exception as exc:
                payload["error"] = f"asr_failed:{exc}"

        text_len = len(str(payload.get("transcript_text", "")))
        if text_len < int(self.settings.min_transcript_chars):
            payload["ok"] = False
            if not payload.get("error"):
                payload["error"] = "transcript_too_short"

        payload.setdefault("meta", {})
        payload["meta"]["normalized_url"] = normalized_url

        self._write_cache(cache_path, payload)
        return payload

    def collect(self, videos: list[dict[str, Any]]) -> dict[str, Any]:
        if not videos:
            return {"transcripts": [], "stats": {"video_count": 0, "ok_count": 0}}

        records: list[dict[str, Any]] = []
        max_workers = max(1, int(self.settings.max_workers))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._collect_one, item) for item in videos]
            for future in as_completed(futures):
                try:
                    record = future.result()
                except Exception as exc:
                    record = {
                        "video_id": "",
                        "url": "",
                        "title": "",
                        "ok": False,
                        "error": f"collector_exception:{exc}",
                        "transcript_text": "",
                        "segments": [],
                        "meta": {"method": "failed"},
                    }
                records.append(record)

        records.sort(key=lambda item: str(item.get("video_id", "")))
        ok_count = sum(1 for item in records if item.get("ok"))
        subtitle_count = sum(
            1 for item in records if str(item.get("meta", {}).get("method", "")).startswith("subtitle")
        )
        asr_count = sum(
            1 for item in records if str(item.get("meta", {}).get("method", "")).startswith("asr")
        )

        stats = {
            "video_count": len(videos),
            "ok_count": ok_count,
            "failed_count": max(0, len(videos) - ok_count),
            "subtitle_success_count": subtitle_count,
            "asr_success_count": asr_count,
            "transcript_coverage_pct": round(ok_count / len(videos) * 100.0, 2) if videos else 0.0,
            "min_transcript_chars": int(self.settings.min_transcript_chars),
            "cache_dir": str(self.cache_dir),
        }
        self._log(
            "info",
            "Video transcript collection done. videos=%s ok=%s subtitle=%s asr=%s coverage=%.2f%%",
            stats["video_count"],
            stats["ok_count"],
            stats["subtitle_success_count"],
            stats["asr_success_count"],
            stats["transcript_coverage_pct"],
        )
        return {"transcripts": records, "stats": stats}
