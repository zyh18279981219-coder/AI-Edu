"""Preview or save a local demo trend for zyh; never write the shared database."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymysql
from dotenv import set_key

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from DatabaseModule.database_factory import DatabaseFactory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Save demo JSON locally and enable its local configuration")
    args = parser.parse_args()
    config = DatabaseFactory.get_config()
    if (config["host"], config["port"], config["database"]) != ("113.44.141.150", 3306, "dev20261008"):
        raise SystemExit("Unexpected database target; no changes made")
    now = datetime.now(timezone(timedelta(hours=8)))
    today = now.date()
    start = today - timedelta(days=29)
    conn = pymysql.connect(
        host=config["host"], port=config["port"], user=config["user"],
        password=config["password"], database=config["database"],
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10, read_timeout=20, autocommit=False,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM twin_profiles WHERE username=%s AND course_id=%s", ("zyh", "course_big_data"))
            profiles = cur.fetchall()
            if len(profiles) != 1:
                raise RuntimeError("Expected exactly one zyh course profile")
            profile = profiles[0]
            end_score = float(profile["overall_mastery"])
            if not 20 <= end_score <= 100:
                raise RuntimeError("Current mastery is outside the supported demo range")
            cur.execute("SELECT * FROM twin_history WHERE username=%s ORDER BY snapshot_date", ("zyh",))
            original = cur.fetchall()
            # Uneven increments show progress at different rates, ending at the real current score.
            weights = [0.7, 1.1, 0.8, 1.4, 0.5, 1.0, 1.3, 0.6, 0.9, 1.2, 0.8, 1.5, 0.6, 1.1,
                       0.7, 1.3, 0.9, 0.5, 1.4, 0.8, 1.0, 1.2, 0.6, 1.1, 0.9, 1.3, 0.7, 1.0, 0.8]
            baseline = max(5.0, end_score - 20.0)
            points = []
            cumulative = 0.0
            for index in range(30):
                if index:
                    cumulative += weights[index - 1]
                score = round(baseline + (end_score - baseline) * cumulative / sum(weights), 2)
                points.append({"date": (start + timedelta(days=index)).isoformat(), "overall_mastery": score,
                               "is_demo": True, "seed_tag": "zyh_demo_trend_20261008",
                               "source": "synthetic_demo", "note": "Presentation history; not measured learning evidence"})
            print(json.dumps({"target": config["host"], "username": "zyh", "days": len(points),
                              "first": points[0], "last": points[-1], "apply": args.apply}, ensure_ascii=False))
            if not args.apply:
                return
            local_file = PROJECT_ROOT / "tmp" / "zyh_local_demo_trend.json"
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_text(json.dumps({"username": "zyh", "points": points}, ensure_ascii=False, indent=2), encoding="utf-8")
            for name in (".env", ".env.local.mysql"):
                env_path = PROJECT_ROOT / name
                if env_path.exists():
                    set_key(str(env_path), "TWIN_DEMO_TREND_FILE", local_file.as_posix())
            print("Local demo file:", local_file)
            print("Shared database unchanged; restart local backend to enable the demo")
    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    main()
