from __future__ import annotations

from pathlib import Path


def test_base_config_loads_into_domain_model() -> None:
    from quant_os.config.loader import load_settings
    from quant_os.domain.enums import TradingMode
    from quant_os.domain.models import SystemConfig

    config_path = Path(__file__).resolve().parents[2] / "conf" / "base.yaml"
    settings = load_settings(config_path)
    system_config = settings.to_domain_model()

    assert isinstance(system_config, SystemConfig)
    assert system_config.mode is TradingMode.PAPER
    assert system_config.strategy.universe
    assert system_config.strategy.target_gross_exposure_limit <= 1


def test_strategy_config_exposes_targets_not_order_intents() -> None:
    from quant_os.config.loader import load_settings
    from quant_os.domain.models import OrderIntent, TargetExposure

    config_path = Path(__file__).resolve().parents[2] / "conf" / "base.yaml"
    settings = load_settings(config_path)
    exposures = settings.to_domain_model().strategy.seed_targets()

    assert exposures
    assert all(isinstance(exposure, TargetExposure) for exposure in exposures)
    assert not any(isinstance(exposure, OrderIntent) for exposure in exposures)
