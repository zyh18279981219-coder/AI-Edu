"""Application database store access.

The project now uses MySQL as the only supported application database.
This module provides a neutral import point for business modules.
"""

from __future__ import annotations

from .database_factory import DatabaseFactory
from .database_store import DatabaseStore


def get_database_store() -> DatabaseStore:
    """Return the configured MySQL-backed application store."""
    return DatabaseFactory.get_store()
