#!/usr/bin/env python3
"""Repair course PDF bindings by matching existing PDF content to knowledge nodes.

The script keeps already-good bindings, reuses clearly matching existing PDFs for
other nodes, and assigns unused PDF paths to nodes that need regeneration.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

ROOT = Path(__file__).resolve().parents[1]
COURSE_JSON = ROOT / "data" / "course" / "big_data.json"
BOOK_DIR = ROOT / "data" / "Book"
OUTPUT_DIR = ROOT / "output"

MARKER = "\u8bfe\u7a0b\u5185\u5bb9"
PUNCTUATION = set(
    " \t\r\n-_/,.;:()[]{}<>\"'`~!@#$%^&*=+|\\?"
    "\uff0c\u3002\uff1b\uff1a\u3001\uff08\uff09\u201c\u201d\u3010\u3011\u300a\u300b\u2022\u00b7"
)


@dataclass
class NodeRef:
    path: list[str]
    node: dict[str, Any]
    current_pdf: str

    @property
    def label(self) -> str:
        return self.path[-1]

    @property
    def path_text(self) -> str:
        return " > ".join(self.path)


@dataclass
class PdfInfo:
    path: str
    title: str
    text: str


def key(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch not in PUNCTUATION and not ch.isdigit())


def normalize_resources(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def is_pdf_resource(value: str) -> bool:
    return "data/Book/" in value and value.lower().endswith(".pdf")


def is_video_resource(value: str) -> bool:
    return value.startswith("http") and ".m3u8" in value.lower()


def collect_nodes(course_data: dict[str, Any]) -> list[NodeRef]:
    nodes: list[NodeRef] = []

    def walk(node: dict[str, Any], lineage: list[str]) -> None:
        name = str(node.get("name") or "")
        path = lineage + [name]
        pdfs = [item for item in normalize_resources(node.get("resource_path")) if is_pdf_resource(item)]
        if pdfs:
            nodes.append(NodeRef(path=path, node=node, current_pdf=pdfs[0]))
        for child_key in ("children", "grandchildren", "great-grandchildren"):
            for child in node.get(child_key, []) or []:
                walk(child, path)

    for child in course_data.get("children", []) or []:
        walk(child, [])
    return nodes


def extract_pdf_info(pdf_path: str) -> PdfInfo:
    full_path = ROOT / pdf_path
    doc = fitz.open(str(full_path))
    text_parts: list[str] = []
    for page_index in range(min(doc.page_count, 2)):
        text_parts.append(doc[page_index].get_text("text"))
    doc.close()
    lines = [line.strip() for line in "\n".join(text_parts).splitlines() if line.strip()]

    title = ""
    for index, line in enumerate(lines[:20]):
        if MARKER in line:
            rest = line.replace(MARKER, "").strip(" :-\uff1a")
            title = rest or (lines[index + 1] if index + 1 < len(lines) else "")
            break
    if not title and lines:
        title = lines[0]

    return PdfInfo(path=pdf_path, title=title.strip(" \u2022"), text=" ".join(lines[:100]))


def pdf_number(pdf_path: str) -> int:
    match = re.search(r"(\d+)\.pdf$", pdf_path, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Cannot parse PDF number: {pdf_path}")
    return int(match.group(1))


def canonical_pdf_path(pdf_path: str) -> str:
    return f"data/Book/{pdf_number(pdf_path)}.PDF"


def pdf_key(pdf_path: str) -> str:
    return canonical_pdf_path(pdf_path).lower()


def current_binding_is_good(node: NodeRef, pdf: PdfInfo) -> bool:
    node_key = key(node.label)
    title_key = key(pdf.title)
    text_key = key(pdf.text[:900])
    if not node_key:
        return False
    return node_key == title_key or node_key in title_key or title_key in node_key or node_key in text_key


def title_tail_key(title: str) -> str:
    parts = re.split(r"\s+-\s+|[-/>\uff1a:]\s*", title)
    parts = [part.strip(" \u2022") for part in parts if part.strip(" \u2022")]
    return key(parts[-1]) if parts else key(title)


def candidate_score(node: NodeRef, pdf: PdfInfo) -> int:
    node_key = key(node.label)
    title_key = key(pdf.title)
    tail_key = title_tail_key(pdf.title)
    if not node_key:
        return 0
    if node_key == title_key:
        return 1000
    if node_key == tail_key:
        return 950
    return 0


def set_pdf_resource(node: dict[str, Any], pdf_path: str) -> None:
    resources = normalize_resources(node.get("resource_path"))
    others = [item for item in resources if not is_pdf_resource(item)]
    videos = [item for item in others if is_video_resource(item)]
    non_videos = [item for item in others if not is_video_resource(item)]
    new_resources = [pdf_path, *videos, *non_videos]
    node["resource_path"] = new_resources if len(new_resources) > 1 else new_resources[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair PDF bindings for the big data course.")
    parser.add_argument("--apply", action="store_true", help="Write repaired course JSON")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    course_data = json.loads(COURSE_JSON.read_text(encoding="utf-8"))
    nodes = collect_nodes(course_data)
    pdf_infos = {
        pdf_key(str(path.relative_to(ROOT)).replace("\\", "/")): extract_pdf_info(
            canonical_pdf_path(str(path.relative_to(ROOT)).replace("\\", "/"))
        )
        for path in sorted(BOOK_DIR.glob("*.PDF"), key=lambda item: int(re.search(r"\d+", item.name).group(0)))
    }

    assigned: dict[str, str] = {}
    used_pdfs: set[str] = set()
    rows: list[dict[str, Any]] = []

    for node in nodes:
        pdf = pdf_infos.get(pdf_key(node.current_pdf))
        if pdf and current_binding_is_good(node, pdf):
            assigned[node.path_text] = node.current_pdf
            used_pdfs.add(pdf_key(node.current_pdf))
            rows.append(
                {
                    "node_path": node.path_text,
                    "old_pdf": node.current_pdf,
                    "new_pdf": node.current_pdf,
                    "action": "keep",
                    "pdf_title": pdf.title,
                    "score": candidate_score(node, pdf),
                }
            )

    for node in nodes:
        if node.path_text in assigned:
            continue
        candidates = [
            (candidate_score(node, pdf), pdf)
            for pdf_path_key, pdf in pdf_infos.items()
            if pdf_path_key not in used_pdfs
        ]
        candidates.sort(key=lambda item: (item[0], -pdf_number(item[1].path)), reverse=True)
        if candidates and candidates[0][0] >= 850:
            score, pdf = candidates[0]
            assigned[node.path_text] = pdf.path
            used_pdfs.add(pdf_key(pdf.path))
            rows.append(
                {
                    "node_path": node.path_text,
                    "old_pdf": node.current_pdf,
                    "new_pdf": pdf.path,
                    "action": "remap_existing",
                    "pdf_title": pdf.title,
                    "score": score,
                }
            )

    unused_pdfs = sorted(
        [pdf.path for path_key, pdf in pdf_infos.items() if path_key not in used_pdfs],
        key=pdf_number,
    )
    regenerate_numbers: list[int] = []
    for node in nodes:
        if node.path_text in assigned:
            continue
        preferred = node.current_pdf if node.current_pdf in unused_pdfs else unused_pdfs[0]
        unused_pdfs.remove(preferred)
        assigned[node.path_text] = preferred
        regenerate_numbers.append(pdf_number(preferred))
        old_info = pdf_infos.get(pdf_key(node.current_pdf))
        rows.append(
            {
                "node_path": node.path_text,
                "old_pdf": node.current_pdf,
                "new_pdf": preferred,
                "action": "regenerate",
                "pdf_title": old_info.title if old_info else "",
                "score": candidate_score(node, old_info) if old_info else 0,
            }
        )

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = OUTPUT_DIR / f"pdf_repair_plan_{stamp}.csv"
    with report_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "nodes": len(nodes),
        "pdfs": len(pdf_infos),
        "keep": sum(1 for row in rows if row["action"] == "keep"),
        "remap_existing": sum(1 for row in rows if row["action"] == "remap_existing"),
        "regenerate": sum(1 for row in rows if row["action"] == "regenerate"),
        "regenerate_numbers": sorted(regenerate_numbers),
        "report": str(report_path),
    }
    summary_path = OUTPUT_DIR / f"pdf_repair_plan_{stamp}.json"
    summary_path.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not args.apply:
        print("Dry run only. Re-run with --apply to update course JSON.")
        return

    backup_path = COURSE_JSON.with_name(f"big_data_before_pdf_repair_{stamp}.json.bak")
    shutil.copy2(COURSE_JSON, backup_path)

    nodes_by_path = {node.path_text: node for node in nodes}
    for node_path, pdf_path in assigned.items():
        set_pdf_resource(nodes_by_path[node_path].node, pdf_path)
    COURSE_JSON.write_text(json.dumps(course_data, ensure_ascii=False, indent=2), encoding="utf-8")
    numbers_path = OUTPUT_DIR / "pdf_regenerate_numbers.txt"
    numbers_path.write_text(",".join(str(number) for number in sorted(regenerate_numbers)), encoding="utf-8")
    print(f"Updated {COURSE_JSON}")
    print(f"Backup {backup_path}")
    print(f"Regenerate numbers written to {numbers_path}")


if __name__ == "__main__":
    main()
