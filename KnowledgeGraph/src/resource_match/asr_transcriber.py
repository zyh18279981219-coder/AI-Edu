from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from KnowledgeGraph.src.resource_match.settings import ASRSettings


class ASRTranscriber:
    """Optional ASR fallback for videos without subtitles."""

    def __init__(self, settings: ASRSettings, logger=None) -> None:
        self.settings = settings
        self.logger = logger
        self._model = None

    def _log(self, level: str, message: str, *args: Any) -> None:
        if self.logger is None:
            return
        log_func = getattr(self.logger, level, None)
        if callable(log_func):
            log_func(message, *args)

    def _load_model(self):
        if self._model is not None:
            return self._model

        hf_endpoint = str(self.settings.hf_endpoint or "").strip()
        if hf_endpoint:
            os.environ["HF_ENDPOINT"] = hf_endpoint

        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"faster-whisper unavailable: {exc}") from exc

        model_kwargs: dict[str, Any] = {}
        download_root = str(self.settings.download_root or "").strip()
        if download_root:
            model_kwargs["download_root"] = download_root

        self._model = WhisperModel(
            self.settings.model_size,
            device=self.settings.device,
            compute_type=self.settings.compute_type,
            **model_kwargs,
        )
        return self._model

    @staticmethod
    def _to_https_url(url: str) -> str:
        parsed = urlparse(str(url or ""))
        if parsed.scheme.lower() != "http":
            return str(url or "")
        return urlunparse(parsed._replace(scheme="https"))

    def _iter_source_urls(self, url: str) -> list[str]:
        original = str(url or "").strip()
        https_url = self._to_https_url(original)

        ordered: list[str] = []
        if original.lower().startswith("http://"):
            candidates = [https_url, original]
        else:
            candidates = [original, https_url]

        for candidate in candidates:
            value = str(candidate or "").strip()
            if not value or value in ordered:
                continue
            ordered.append(value)
        return ordered

    @staticmethod
    def _resolve_ffmpeg_executable() -> str:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        try:
            import imageio_ffmpeg  # type: ignore

            embedded_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            if embedded_ffmpeg and Path(embedded_ffmpeg).exists():
                return str(embedded_ffmpeg)
        except Exception:
            pass
        return ""

    def _extract_audio(self, url: str, target_wav: Path) -> None:
        ffmpeg_exe = self._resolve_ffmpeg_executable()
        if not ffmpeg_exe:
            raise RuntimeError("ffmpeg unavailable (system PATH and imageio-ffmpeg not found)")

        def run_once(input_url: str) -> tuple[int, str]:
            cmd = [
                ffmpeg_exe,
                "-y",
                "-user_agent",
                "Mozilla/5.0 AI-Edu-KG/1.0",
                "-i",
                input_url,
                "-t",
                str(max(60, int(self.settings.max_audio_seconds))),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(target_wav),
            ]
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            return process.returncode, (process.stderr or "").strip()

        stderr = ""
        for candidate in self._iter_source_urls(url):
            code, stderr = run_once(candidate)
            if code == 0:
                return

        raise RuntimeError(f"ffmpeg failed: {stderr[:500]}")

    def transcribe(self, url: str) -> dict[str, Any]:
        if not self.settings.enabled:
            return {
                "ok": False,
                "error": "asr_disabled",
                "text": "",
                "segments": [],
            }

        model = self._load_model()
        with tempfile.TemporaryDirectory(prefix="kg_video_asr_") as temp_dir:
            wav_path = Path(temp_dir) / "audio.wav"
            self._extract_audio(url, wav_path)

            segments, info = model.transcribe(
                str(wav_path),
                beam_size=3,
                vad_filter=True,
            )
            chunk_records: list[dict[str, Any]] = []
            texts: list[str] = []
            for segment in segments:
                text = str(segment.text or "").strip()
                if not text:
                    continue
                chunk_records.append(
                    {
                        "start": round(float(segment.start), 3),
                        "end": round(float(segment.end), 3),
                        "text": text,
                    }
                )
                texts.append(text)

        language = ""
        try:
            language = str(getattr(info, "language", "") or "")
        except Exception:
            language = ""

        payload = {
            "ok": bool(texts),
            "error": "" if texts else "asr_empty",
            "text": "\n".join(texts),
            "segments": chunk_records,
            "meta": {
                "method": "asr_faster_whisper",
                "language": language,
                "segment_count": len(chunk_records),
                "asr_settings": {
                    "model_size": self.settings.model_size,
                    "device": self.settings.device,
                    "compute_type": self.settings.compute_type,
                    "max_audio_seconds": self.settings.max_audio_seconds,
                },
            },
        }
        self._log(
            "info",
            "ASR transcription finished. language=%s segments=%s",
            language,
            len(chunk_records),
        )
        return payload

    @staticmethod
    def to_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, indent=2)
