from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from HomeworkModule.service import HomeworkService


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed OJ smoke assignments")
    parser.add_argument("--teacher", default="teacher", help="Teacher username")
    args = parser.parse_args()

    service = HomeworkService()
    result = service.create_teacher_owned_oj_smoke_assignments(args.teacher)
    print("owner=", result.get("owner"))
    print("created_count=", result.get("created_count", 0))
    for item in result.get("created_assignments", []) or []:
        print("-", item.get("id"), item.get("title"), item.get("status"))


if __name__ == "__main__":
    main()
