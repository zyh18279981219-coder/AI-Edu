from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from KnowledgeGraph.src.pipeline import KGPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KnowledgeGraph pipeline runner")
    parser.add_argument(
        "--stage",
        type=int,
        default=0,
        choices=[0, 1, 2, 3, 4],
        help=(
            "Pipeline stage to execute. "
            "0: skeleton checks, 1: text cleaning, 2: triple extraction, "
            "3: pedagogy graph build, 4: resource matching."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run selected stage in dry-run mode.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Backup data/course/big_data.json before running.",
    )
    parser.add_argument(
        "--kggen-doc-limit",
        type=int,
        default=5,
        help="Stage 2 only: number of documents to attempt kg-gen extraction before fallback.",
    )
    parser.add_argument(
        "--max-chars-per-doc",
        type=int,
        default=1200,
        help="Stage 2 only: max text length per document passed to extractor.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pipeline = KGPipeline()

    backup_path = None
    if args.backup:
        backup_path = pipeline.backup_course_graph()

    report = pipeline.run(
        stage=args.stage,
        dry_run=args.dry_run,
        kggen_doc_limit=args.kggen_doc_limit,
        max_chars_per_doc=args.max_chars_per_doc,
    )
    if backup_path is not None:
        report["backup_path"] = str(backup_path)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
