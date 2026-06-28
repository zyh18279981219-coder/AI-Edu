"""Shared environment loading helpers."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    """Load default .env, then optionally override with DB_ENV_FILE."""
    project_root = Path(__file__).resolve().parents[2]
    backend_root = project_root / "backend"

    for env_path in (project_root / ".env", backend_root / ".env", Path.cwd() / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)

    env_file = os.getenv("DB_ENV_FILE")
    if env_file:
        load_dotenv(env_file, override=True)
