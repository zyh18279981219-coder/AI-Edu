"""Prepare or apply a backed-up demo trend for zyh; leave current scores intact."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pymysql

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from DatabaseModule.database_factory import DatabaseFactory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write the preview after backing up history")
    args = parser.parse_args()
    config = DatabaseFactory.get_config()
    if (config["host"], config["port"], config["database"]) != ("113.44.141.150", 3306, "dev20260912"):
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
            # Lock the current profile to prevent ending at a stale value during a concurrent refresh.
            cur.execute("SELECT overall_mastery FROM twin_profiles WHERE profile_id=%s FOR UPDATE", (profile["profile_id"],))
            if float(cur.fetchone()["overall_mastery"]) != end_score:
                raise RuntimeError("Profile changed during preview; rerun the script")
            cur.execute("SELECT * FROM twin_history WHERE username=%s ORDER BY snapshot_date FOR UPDATE", ("zyh",))
            original = cur.fetchall()
            backup_dir = PROJECT_ROOT / "tmp" / ("zyh_demo_trend_backup_" + now.strftime("%Y%m%d_%H%M%S_%f"))
            backup_dir.mkdir(parents=True)
            backup = backup_dir / "history_before.json"
            backup.write_text(json.dumps({"database": config["database"], "host": config["host"],
                                          "username": "zyh", "range_start": start.isoformat(), "range_end": today.isoformat(),
                                          "profiles": profiles, "history": original}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            (backup_dir / "demo_points.json").write_text(json.dumps(points, ensure_ascii=False, indent=2), encoding="utf-8")
            for point in points:
                cur.execute("""INSERT INTO twin_history
                    (username,user_id,course_id,snapshot_date,overall_mastery,payload_json,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE overall_mastery=VALUES(overall_mastery),
                    payload_json=VALUES(payload_json),updated_at=VALUES(updated_at)""",
                    ("zyh", profile["user_id"], "course_big_data", point["date"], point["overall_mastery"],
                     json.dumps(point, ensure_ascii=False), now.replace(tzinfo=None)))
            cur.execute("SELECT COUNT(*) AS total FROM twin_history WHERE username=%s AND course_id=%s AND snapshot_date BETWEEN %s AND %s",
                        ("zyh", "course_big_data", start, today))
            if cur.fetchone()["total"] != 30:
                raise RuntimeError("Unexpected snapshot count; transaction will roll back")
            conn.commit()
            print("backup:", backup)
            print("Applied 30 demo snapshots; profile, quiz attempts, progress and 5E data unchanged")
    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    main()
