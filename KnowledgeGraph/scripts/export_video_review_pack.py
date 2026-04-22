from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import imageio_ffmpeg  # type: ignore

_UA = "Mozilla/5.0 AI-Edu-KG/1.0"
_TS_PATTERN = re.compile(
    r"^\s*(\d{1,2}:\d{2}:\d{2})\s*-\s*(\d{1,2}:\d{2}:\d{2})\s*$"
)


@dataclass
class EvidenceWindow:
    start_sec: float
    end_sec: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


def _to_seconds(hms: str) -> float:
    chunks = hms.strip().split(":")
    if len(chunks) != 3:
        return 0.0
    try:
        hour = float(chunks[0])
        minute = float(chunks[1])
        second = float(chunks[2])
    except ValueError:
        return 0.0
    return hour * 3600.0 + minute * 60.0 + second


def _normalize_https(url: str) -> str:
    parsed = urlparse(str(url or ""))
    if parsed.scheme.lower() != "http":
        return str(url or "")
    return urlunparse(parsed._replace(scheme="https"))


def _iter_source_urls(url: str) -> list[str]:
    original = str(url or "").strip()
    https_url = _normalize_https(original)

    ordered: list[str] = []
    if original.lower().startswith("http://"):
        candidates = [https_url, original]
    else:
        candidates = [original, https_url]

    for item in candidates:
        value = str(item or "").strip()
        if not value or value in ordered:
            continue
        ordered.append(value)
    return ordered


def _parse_timestamp_window(item: dict[str, Any]) -> EvidenceWindow | None:
    text = str(item.get("selected_evidence_timestamp", "")).strip()
    if text:
        matched = _TS_PATTERN.match(text)
        if matched:
            start = _to_seconds(matched.group(1))
            end = _to_seconds(matched.group(2))
            if end > start:
                return EvidenceWindow(start_sec=start, end_sec=end)

    candidates = item.get("candidates") or []
    if isinstance(candidates, list) and candidates:
        top_candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        start = float(top_candidate.get("evidence_start", 0.0) or 0.0)
        end = float(top_candidate.get("evidence_end", 0.0) or 0.0)
        if end > start:
            return EvidenceWindow(start_sec=start, end_sec=end)
    return None


def _run_ffmpeg_clip(
    url: str,
    output_wav: Path,
    start_sec: float,
    duration_sec: float,
) -> dict[str, Any]:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    last_error = ""

    for source_url in _iter_source_urls(url):
        cmd = [
            ffmpeg_exe,
            "-y",
            "-user_agent",
            _UA,
            "-ss",
            f"{max(0.0, start_sec):.3f}",
            "-i",
            source_url,
            "-t",
            f"{max(1.0, duration_sec):.3f}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_wav),
        ]
        process = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if process.returncode == 0 and output_wav.exists():
            return {
                "ok": True,
                "used_url": source_url,
                "stderr_tail": (process.stderr or "")[-400:],
            }
        last_error = (process.stderr or "")[-800:]

    return {
        "ok": False,
        "used_url": "",
        "stderr_tail": last_error,
    }


def _choose_records(
    report: dict[str, Any],
    decision: str,
    top_n: int,
    concept_id: str,
) -> list[dict[str, Any]]:
    matches = report.get("matches") or []
    if not isinstance(matches, list):
        return []

    selected: list[dict[str, Any]] = []
    for item in matches:
        if not isinstance(item, dict):
            continue
        current_id = str(item.get("concept_id", "")).strip()
        current_decision = str(item.get("decision", "")).strip()
        if concept_id and current_id != concept_id:
            continue
        if decision != "all" and current_decision != decision:
            continue
        selected.append(item)

    selected.sort(key=lambda x: float(x.get("top_score", 0.0) or 0.0), reverse=True)
    return selected[: max(1, top_n)] if not concept_id else selected


def build_review_pack(args: argparse.Namespace) -> dict[str, Any]:
    report_path = Path(args.report)
    output_dir = Path(args.output_dir)
    clips_dir = output_dir / "clips"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_clips:
        clips_dir.mkdir(parents=True, exist_ok=True)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    records = _choose_records(
        report=report,
        decision=args.decision,
        top_n=int(args.top_n),
        concept_id=str(args.concept_id or "").strip(),
    )

    result_items: list[dict[str, Any]] = []
    for index, item in enumerate(records, start=1):
        evidence_window = _parse_timestamp_window(item)
        evidence_start = float(evidence_window.start_sec if evidence_window else 0.0)
        evidence_duration = float(
            max(1.0, min(float(args.clip_seconds), evidence_window.duration))
            if evidence_window
            else float(args.clip_seconds)
        )

        selected_url = str(item.get("selected_video_url", "")).strip()
        top_candidate = (item.get("candidates") or [{}])[0]
        if not selected_url and isinstance(top_candidate, dict):
            selected_url = str(top_candidate.get("video_url", "")).strip()

        snippet = ""
        if isinstance(top_candidate, dict):
            snippet = str(top_candidate.get("evidence_snippet", "")).strip()

        clip_name = f"{index:03d}_{str(item.get('concept_id', 'unknown')).strip()}.wav"
        clip_path = clips_dir / clip_name

        clip_status: dict[str, Any] = {"ok": False, "used_url": "", "stderr_tail": ""}
        if not args.skip_clips and selected_url:
            clip_status = _run_ffmpeg_clip(
                url=selected_url,
                output_wav=clip_path,
                start_sec=evidence_start,
                duration_sec=evidence_duration,
            )

        result_items.append(
            {
                "index": index,
                "concept_id": str(item.get("concept_id", "")),
                "concept_name": str(item.get("concept_name", "")),
                "decision": str(item.get("decision", "")),
                "top_score": float(item.get("top_score", 0.0) or 0.0),
                "selected_video_title": str(item.get("selected_video_title", "")),
                "selected_video_url": selected_url,
                "selected_evidence_timestamp": str(item.get("selected_evidence_timestamp", "")),
                "evidence_snippet": snippet,
                "clip_start_sec": round(evidence_start, 3),
                "clip_duration_sec": round(evidence_duration, 3),
                "clip_ok": bool(clip_status.get("ok")),
                "clip_file": str(clip_path) if clip_status.get("ok") else "",
                "clip_used_url": str(clip_status.get("used_url", "")),
                "clip_error_tail": str(clip_status.get("stderr_tail", "")),
            }
        )

    json_path = output_dir / "review_pack.json"
    csv_path = output_dir / "review_pack.csv"
    payload = {
        "report_source": str(report_path),
        "decision_filter": args.decision,
        "top_n": int(args.top_n),
        "concept_id": str(args.concept_id or ""),
        "clip_seconds": int(args.clip_seconds),
        "skip_clips": bool(args.skip_clips),
        "item_count": len(result_items),
        "items": result_items,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "index",
                "concept_id",
                "concept_name",
                "decision",
                "top_score",
                "selected_video_title",
                "selected_video_url",
                "selected_evidence_timestamp",
                "clip_start_sec",
                "clip_duration_sec",
                "clip_ok",
                "clip_file",
                "clip_used_url",
            ],
        )
        writer.writeheader()
        for item in result_items:
            writer.writerow({k: item.get(k, "") for k in writer.fieldnames})

    success_count = sum(1 for item in result_items if item.get("clip_ok"))
    return {
        "json_path": str(json_path),
        "csv_path": str(csv_path),
        "clips_dir": str(clips_dir),
        "item_count": len(result_items),
        "clip_success_count": success_count,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a review pack for video-match verification without direct m3u8 playback."
    )
    parser.add_argument(
        "--report",
        default="KnowledgeGraph/data/output/video_match_report.json",
        help="Path to video_match_report.json",
    )
    parser.add_argument(
        "--output-dir",
        default="KnowledgeGraph/data/output/video_review_pack",
        help="Directory for exported review package",
    )
    parser.add_argument(
        "--decision",
        default="matched",
        choices=["matched", "needs_review", "unmatched", "all"],
        help="Decision filter for selected concepts",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Maximum number of records to export",
    )
    parser.add_argument(
        "--concept-id",
        default="",
        help="Export only one concept by concept_id",
    )
    parser.add_argument(
        "--clip-seconds",
        type=int,
        default=15,
        help="Max clip duration in seconds for each evidence sample",
    )
    parser.add_argument(
        "--skip-clips",
        action="store_true",
        help="Only export JSON/CSV evidence table, skip media clip extraction",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    summary = build_review_pack(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
