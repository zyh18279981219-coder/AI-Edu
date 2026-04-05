from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from DatabaseModule.sqlite_store import get_sqlite_store
from DigitalTwinModule.models import TrendPoint

HISTORY_DIR = Path("data/digital_twins/history")


class TrendTracker:
    HISTORY_DIR = HISTORY_DIR

    def __init__(self):
        self.store = get_sqlite_store()

    def _history_path(self, username: str) -> Path:
        return self.HISTORY_DIR / f"{username}.json"

    def record_daily_snapshot(self, username: str, overall_mastery: float) -> None:
        today = date.today().isoformat()
        point = TrendPoint(date=today, overall_mastery=overall_mastery).model_dump()

        try:
            self.store.save_twin_history(username, today, point)
        except Exception:
            pass

    def get_trend(self, username: str, days: int = 30) -> list[TrendPoint]:
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        raw_list: list[dict] = []
        try:
            raw_list = self.store.get_twin_history(username)
        except Exception:
            raw_list = []

        filtered = [entry for entry in raw_list if entry.get("date", "") >= cutoff]
        filtered.sort(key=lambda item: item["date"])
        return [TrendPoint(**entry) for entry in filtered]
