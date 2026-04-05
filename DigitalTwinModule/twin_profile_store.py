from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from DatabaseModule.sqlite_store import get_sqlite_store
from DigitalTwinModule.models import TrendPoint, TwinProfile, TwinProfileParseError

logger = logging.getLogger(__name__)

BASE_DIR = Path("data/digital_twins")
HISTORY_DIR = Path("data/digital_twins/history")

_REQUIRED_FIELDS = ("username", "last_updated", "knowledge_nodes")


class TwinProfileStore:
    BASE_DIR = BASE_DIR
    HISTORY_DIR = HISTORY_DIR

    def __init__(self):
        self.store = get_sqlite_store()

    def _profile_path(self, username: str) -> Path:
        return self.BASE_DIR / f"{username}.json"

    def _history_path(self, username: str) -> Path:
        return self.HISTORY_DIR / f"{username}.json"

    def save(self, profile: TwinProfile) -> None:
        try:
            self.store.save_twin_profile(profile.username, profile.model_dump())
            logger.info("TwinProfileStore: wrote profile SQLite for %s", profile.username)
        except Exception:
            logger.exception("TwinProfileStore: failed writing profile SQLite for %s", profile.username)

    def load(self, username: str) -> TwinProfile:
        try:
            raw = self.store.get_twin_profile(username)
            if raw is not None:
                logger.info("TwinProfileStore: read profile from SQLite for %s", username)
            else:
                raise FileNotFoundError(f"TwinProfile for user '{username}' not found in SQLite")
        except Exception:
            logger.exception("TwinProfileStore: failed reading profile from SQLite for %s", username)
            raise

        missing = [field for field in _REQUIRED_FIELDS if field not in raw]
        if missing:
            raise TwinProfileParseError(
                f"TwinProfile for '{username}' is missing required fields: {missing}"
            )

        return TwinProfile.model_validate(raw)

    def load_or_create(self, username: str) -> TwinProfile:
        try:
            return self.load(username)
        except FileNotFoundError:
            return TwinProfile(
                username=username,
                last_updated=datetime.now().isoformat(),
                knowledge_nodes=[],
                overall_mastery=0.0,
            )

    def exists(self, username: str) -> bool:
        try:
            if self.store.get_twin_profile(username) is not None:
                logger.info("TwinProfileStore: exists(%s) resolved from SQLite", username)
                return True
        except Exception:
            logger.exception("TwinProfileStore: exists(%s) failed reading SQLite", username)
        return False

    def save_daily_snapshot(self, profile: TwinProfile) -> None:
        today = date.today().isoformat()
        new_point = TrendPoint(date=today, overall_mastery=profile.overall_mastery)

        try:
            self.store.save_twin_history(profile.username, today, new_point.model_dump())
            logger.info("TwinProfileStore: wrote history SQLite for %s on %s", profile.username, today)
        except Exception:
            logger.exception("TwinProfileStore: failed writing history SQLite for %s on %s", profile.username, today)
