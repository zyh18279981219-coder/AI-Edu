"""后台孪生采集开关的行为。

开关放在随代码提交的 config/app_runtime.json 里（不是 .env，.env 不进版本库，
线上部署拉不到，会出现"本地关了、线上还开着"）。这里锁住读取与覆盖逻辑。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))


def _import_app():
    import app as app_module

    return app_module


def test_schedule_config_reads_committed_runtime_file():
    app_module = _import_app()
    from tools.runtime_config import load_runtime_config

    cfg = load_runtime_config().get("twin") or {}
    enabled, interval = app_module._twin_schedule_config()

    # 与随代码提交的配置保持一致：线上拉代码后行为相同
    assert enabled is bool(cfg.get("scheduled_collection_enabled", True))
    assert interval == int(cfg.get("scheduled_collection_interval_seconds", 600))


def test_demo_data_is_frozen_by_default():
    """演示期间应关闭定时采集，否则后台会重算画像与当天趋势点。"""
    app_module = _import_app()
    enabled, _ = app_module._twin_schedule_config()
    assert enabled is False, "config/app_runtime.json 里应保持 scheduled_collection_enabled=false"


def test_env_var_overrides_config(monkeypatch):
    app_module = _import_app()

    monkeypatch.setenv("TWIN_SCHEDULED_COLLECTION_ENABLED", "true")
    assert app_module._twin_schedule_config()[0] is True

    monkeypatch.setenv("TWIN_SCHEDULED_COLLECTION_ENABLED", "0")
    assert app_module._twin_schedule_config()[0] is False


def test_interval_has_a_sane_floor(monkeypatch):
    """间隔过小会让后台任务几乎连轴转，必须兜底。"""
    app_module = _import_app()
    app_module.runtime_config["twin"] = {
        "scheduled_collection_enabled": True,
        "scheduled_collection_interval_seconds": 5,
    }
    try:
        _, interval = app_module._twin_schedule_config()
        assert interval >= 60
    finally:
        from tools.runtime_config import load_runtime_config

        app_module.runtime_config.clear()
        app_module.runtime_config.update(load_runtime_config())
