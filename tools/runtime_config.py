from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_CONFIG_PATH = PROJECT_ROOT / "config" / "app_runtime.json"


def load_runtime_config() -> Dict[str, Any]:
    """Load runtime config JSON; return empty dict when file is missing/invalid."""
    if not RUNTIME_CONFIG_PATH.exists():
        return {}
    try:
        raw = RUNTIME_CONFIG_PATH.read_text(encoding="utf-8")
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
