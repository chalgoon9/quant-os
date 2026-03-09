from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from quant_os.config.models import AppSettings


def load_settings(path: str | Path) -> AppSettings:
    config_path = Path(path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"config file does not exist: {config_path}")
    payload = _read_yaml(config_path)
    settings = AppSettings.model_validate(payload)
    return settings.resolve_paths(config_path.parent)


def _read_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"config file is empty: {path}")
    if not isinstance(raw, dict):
        raise ValueError(f"config file must contain a mapping: {path}")
    return raw
