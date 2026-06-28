"""MySQL-only database factory."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .database_store import DatabaseStore
from tools.env_loader import load_project_env

logger = logging.getLogger(__name__)


class DatabaseFactory:
    """Create and cache the configured MySQL application store."""

    _instance: Optional[DatabaseStore] = None
    _config_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def create_store(cls, config: Optional[Dict[str, Any]] = None) -> DatabaseStore:
        if config is None:
            config = cls._load_config_from_env()
        cls._validate_config(config)

        from .mysql_store import MySQLStore

        return MySQLStore(
            host=config["host"],
            port=config.get("port", 3306),
            user=config["user"],
            password=config["password"],
            database=config["database"],
            charset=config.get("charset", "utf8mb4"),
            pool_size=config.get("pool_size", 10),
            max_overflow=config.get("max_overflow", 5),
            pool_recycle=config.get("pool_recycle", 3600),
            pool_pre_ping=config.get("pool_pre_ping", True),
            pool_timeout=config.get("pool_timeout", 30),
            pool_warmup=config.get("pool_warmup", True),
            **config.get("extra_params", {}),
        )

    @classmethod
    def get_store(cls) -> DatabaseStore:
        if cls._instance is None:
            cls._instance = cls.create_store()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        if cls._instance is not None and hasattr(cls._instance, "close"):
            try:
                cls._instance.close()
            except Exception as exc:
                logger.warning("Failed to close database store: %s", exc)
        cls._instance = None
        cls._config_cache = None

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        return cls._load_config_from_env()

    @classmethod
    def test_connection(cls, config: Optional[Dict[str, Any]] = None) -> bool:
        try:
            store = cls.create_store(config)
            with store.connection():
                pass
            if hasattr(store, "close"):
                store.close()
            return True
        except Exception as exc:
            logger.error("Database connection test failed: %s", exc)
            return False

    @classmethod
    def _load_config_from_env(cls) -> Dict[str, Any]:
        if cls._config_cache is not None:
            return cls._config_cache

        cls._load_env_file()

        db_type = os.getenv("DB_TYPE", "mysql").lower()
        if db_type != "mysql":
            raise ValueError(f"Unsupported DB_TYPE={db_type!r}; only mysql is supported")

        config: Dict[str, Any] = {
            "type": "mysql",
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "ai_education"),
            "charset": os.getenv("DB_CHARSET", "utf8mb4"),
            "pool_size": cls._get_env_int("DB_POOL_SIZE", 10),
            "max_overflow": cls._get_env_int("DB_MAX_OVERFLOW", 5),
            "pool_recycle": cls._get_env_int("DB_POOL_RECYCLE", 3600),
            "pool_pre_ping": cls._get_env_bool("DB_POOL_PRE_PING", True),
            "pool_timeout": cls._get_env_int("DB_POOL_TIMEOUT", 30),
            "pool_warmup": cls._get_env_bool("DB_POOL_WARMUP", True),
        }

        ssl_ca = os.getenv("DB_SSL_CA")
        ssl_cert = os.getenv("DB_SSL_CERT")
        ssl_key = os.getenv("DB_SSL_KEY")
        if ssl_ca or ssl_cert or ssl_key:
            config["extra_params"] = {
                "ssl_ca": ssl_ca,
                "ssl_cert": ssl_cert,
                "ssl_key": ssl_key,
                "ssl_verify_cert": os.getenv("DB_SSL_VERIFY", "true").lower() == "true",
            }

        cls._config_cache = config
        logger.info("Loaded database config: type=mysql host=%s database=%s", config["host"], config["database"])
        return config

    @classmethod
    def _load_env_file(cls) -> None:
        try:
            load_project_env()
        except Exception as exc:
            logger.warning("Failed to load environment files: %s", exc)

    @classmethod
    def _validate_config(cls, config: Dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise ValueError("Database config must be a dictionary")

        db_type = str(config.get("type", "mysql")).lower()
        if db_type != "mysql":
            raise ValueError(f"Unsupported database type: {db_type}; only mysql is supported")

        required_fields = ["host", "user", "password", "database"]
        missing_fields = [field for field in required_fields if not config.get(field)]
        if missing_fields:
            raise ValueError(f"MySQL configuration missing required fields: {', '.join(missing_fields)}")

        port = config.get("port", 3306)
        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValueError(f"Invalid MySQL port: {port}")

        for field in ("pool_size", "max_overflow", "pool_recycle", "pool_timeout"):
            value = config.get(field)
            if value is not None and (not isinstance(value, int) or value < 0):
                raise ValueError(f"Invalid MySQL {field}: {value}")

    @staticmethod
    def _get_env_int(name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None or value == "":
            return default
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"Invalid integer value for {name}: {value}") from exc

    @staticmethod
    def _get_env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None or value == "":
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}
