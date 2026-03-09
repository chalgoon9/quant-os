from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os

from fastapi import Request

from quant_os.config.loader import load_settings
from quant_os.config.models import AppSettings
from quant_os.domain.models import SystemConfig
from quant_os.services.wiring import AppRuntime, build_app_runtime


def resolve_config_path(config: Path | str | None = None) -> Path:
    candidate = Path(config or os.environ.get("QUANT_OS_CONFIG", "conf/base.yaml"))
    return candidate.expanduser().resolve()


@lru_cache(maxsize=8)
def _load_settings_cached(config_path: str) -> AppSettings:
    return load_settings(config_path)


@lru_cache(maxsize=8)
def _build_runtime_cached(config_path: str) -> AppRuntime:
    runtime = build_app_runtime(_load_settings_cached(config_path))
    runtime.operational_store.create_schema()
    return runtime


def get_config_path(request: Request) -> Path:
    return Path(request.app.state.config_path)


def get_settings(request: Request) -> AppSettings:
    return _load_settings_cached(str(get_config_path(request)))


def get_system(request: Request) -> SystemConfig:
    return get_settings(request).to_domain_model()


def get_runtime(request: Request) -> AppRuntime:
    return _build_runtime_cached(str(get_config_path(request)))

