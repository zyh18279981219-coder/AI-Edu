from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from DigitalTwinModule.student_course_profile_service import get_student_course_profile


def main() -> None:
    student_id = "zyh"
    course_id = "Spark"
    data = get_student_course_profile(student_id, course_id)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
