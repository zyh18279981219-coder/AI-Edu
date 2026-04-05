from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from DatabaseModule.sqlite_store import get_sqlite_store


def _read_json(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def migrate_users() -> Dict[str, int]:
    store = get_sqlite_store()
    users_dir = Path("data/Users")
    summary: Dict[str, int] = {}
    for user_type in ("student", "teacher", "admin"):
        users = _read_json(users_dir / f"{user_type}.json", [])
        if not isinstance(users, list):
            users = []
        store.replace_users(user_type, users)
        summary[user_type] = len(users)
    return summary


def migrate_twin_profiles() -> Dict[str, int]:
    store = get_sqlite_store()
    twins_dir = Path("data/digital_twins")
    history_dir = twins_dir / "history"
    profile_count = 0
    history_count = 0

    if twins_dir.exists():
        for file_path in twins_dir.glob("*.json"):
            payload = _read_json(file_path, None)
            if isinstance(payload, dict):
                store.save_twin_profile(file_path.stem, payload)
                profile_count += 1

    if history_dir.exists():
        for file_path in history_dir.glob("*.json"):
            payload = _read_json(file_path, [])
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict) or not item.get("date"):
                    continue
                store.save_twin_history(file_path.stem, item["date"], item)
                history_count += 1

    return {"profiles": profile_count, "history": history_count}


def migrate_sessions() -> Dict[str, int]:
    store = get_sqlite_store()
    session_dir = Path("data/sessions")
    user_state_dir = Path("data/user_state")
    session_count = 0
    state_count = 0

    if session_dir.exists():
        for file_path in session_dir.glob("*.json"):
            payload = _read_json(file_path, None)
            if isinstance(payload, dict):
                store.save_session(file_path.stem, payload)
                session_count += 1

    if user_state_dir.exists():
        for file_path in user_state_dir.glob("*.json"):
            payload = _read_json(file_path, None)
            if isinstance(payload, dict):
                store.save_user_state(file_path.stem, payload)
                state_count += 1

    return {"sessions": session_count, "user_states": state_count}


def migrate_llm_logs() -> Dict[str, int]:
    store = get_sqlite_store()
    log_file = Path("data/Log/llm_log.json")
    logs = _read_json(log_file, [])
    count = 0
    normalized = []
    if isinstance(logs, list):
        for item in logs:
            if isinstance(item, dict):
                normalized.append(item)
                count += 1
    store.replace_llm_logs(normalized)
    return {"llm_logs": count}


def migrate_learning_plans() -> Dict[str, int]:
    store = get_sqlite_store()
    plan_files: List[Path] = []
    global_dir = Path("data/learning_plans")
    if global_dir.exists():
        plan_files.extend(global_dir.glob("*.json"))

    user_data_dir = Path("data/user_data")
    if user_data_dir.exists():
        for plan_dir in user_data_dir.glob("*/learning_plans"):
            plan_files.extend(plan_dir.glob("*.json"))

    count = 0
    for file_path in plan_files:
        payload = _read_json(file_path, None)
        if payload is None:
            continue
        if "_path_" in file_path.name:
            username = file_path.name.split("_path_")[0]
            category = "path"
        elif "_plan_" in file_path.name:
            username = file_path.name.split("_plan_")[0]
            category = "user" if "user_data" in str(file_path) else "global"
        else:
            username = file_path.parent.parent.name if file_path.parent.name == "learning_plans" else "unknown"
            category = "user" if "user_data" in str(file_path) else "global"
        store.save_learning_plan(
            username=username,
            filename=file_path.name,
            payload=payload,
            plan_path=str(file_path),
            category=category,
        )
        count += 1
    return {"learning_plans": count}


def migrate_all() -> Dict[str, Dict[str, int]]:
    return {
        "users": migrate_users(),
        "twin_profiles": migrate_twin_profiles(),
        "sessions": migrate_sessions(),
        "llm_logs": migrate_llm_logs(),
        "learning_plans": migrate_learning_plans(),
    }


if __name__ == "__main__":
    print(json.dumps(migrate_all(), ensure_ascii=False, indent=2))
