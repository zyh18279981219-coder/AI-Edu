from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path
from time import monotonic

from DatabaseModule.database_factory import DatabaseFactory
from DigitalTwinModule.models import TrendPoint, TwinProfile, TwinProfileParseError

logger = logging.getLogger(__name__)

BASE_DIR = Path("data/digital_twins")
HISTORY_DIR = Path("data/digital_twins/history")

_REQUIRED_FIELDS = ("username", "last_updated", "knowledge_nodes")


class TwinProfileStore:
    BASE_DIR = BASE_DIR
    HISTORY_DIR = HISTORY_DIR
    _profile_cache: dict[str, tuple[float, TwinProfile]] = {}
    _cache_ttl_seconds = float(os.getenv("TWIN_PROFILE_CACHE_SECONDS", "60"))

    def __init__(self):
        self.store = DatabaseFactory.get_store()

    def _profile_path(self, username: str) -> Path:
        return self.BASE_DIR / f"{username}.json"

    def _history_path(self, username: str) -> Path:
        return self.HISTORY_DIR / f"{username}.json"

    def save(self, profile: TwinProfile) -> None:
        try:
            self.store.save_twin_profile(profile.username, profile.model_dump())
            self._profile_cache[profile.username] = (monotonic(), profile)
            logger.info("TwinProfileStore: wrote profile to %s for %s", type(self.store).__name__, profile.username)
        except Exception:
            logger.exception("TwinProfileStore: failed writing profile to %s for %s", type(self.store).__name__, profile.username)

    def load(self, username: str) -> TwinProfile:
        cached = self._profile_cache.get(username)
        if cached and monotonic() - cached[0] < self._cache_ttl_seconds:
            return cached[1]

        try:
            raw = self.store.get_twin_profile(username)
            if raw is not None:
                logger.info("TwinProfileStore: read profile from %s for %s", type(self.store).__name__, username)
            else:
                raise FileNotFoundError(f"TwinProfile for user '{username}' not found in {type(self.store).__name__}")
        except Exception:
            logger.exception("TwinProfileStore: failed reading profile from %s for %s", type(self.store).__name__, username)
            raise

        missing = [field for field in _REQUIRED_FIELDS if field not in raw]
        if missing:
            raise TwinProfileParseError(
                f"TwinProfile for '{username}' is missing required fields: {missing}"
            )

        profile = TwinProfile.model_validate(raw)
        self._profile_cache[username] = (monotonic(), profile)
        return profile

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
            self.load(username)
            logger.info("TwinProfileStore: exists(%s) resolved from %s", username, type(self.store).__name__)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            logger.exception("TwinProfileStore: exists(%s) failed reading %s", username, type(self.store).__name__)
            return False

    def save_daily_snapshot(self, profile: TwinProfile) -> None:
        today = date.today().isoformat()
        new_point = TrendPoint(date=today, overall_mastery=profile.overall_mastery)

        try:
            self.store.save_twin_history(profile.username, today, new_point.model_dump())
            logger.info("TwinProfileStore: wrote history to %s for %s on %s", type(self.store).__name__, profile.username, today)
        except Exception:
            logger.exception("TwinProfileStore: failed writing history to %s for %s on %s", type(self.store).__name__, profile.username, today)
