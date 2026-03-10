from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def _build_history(symbols: tuple[str, ...]) -> dict[str, list]:
    from quant_os.domain.models import MarketBar

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history: dict[str, list[MarketBar]] = {symbol: [] for symbol in symbols}
    for index in range(140):
        ts = start + timedelta(days=index)
        for offset, symbol in enumerate(symbols, start=1):
            base = Decimal("100") + (index * Decimal(str(offset)))
            history[symbol].append(
                MarketBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=base,
                    high=base + Decimal("1"),
                    low=base - Decimal("1"),
                    close=base + Decimal("0.5"),
                    volume=Decimal("1000"),
                )
            )
    return history


def test_strategy_registry_loads_multiple_specs_and_builds_target_only_strategy() -> None:
    from quant_os.domain.models import TargetExposure
    from quant_os.strategy import load_strategy_specs, strategy_registry

    specs = load_strategy_specs()

    assert "kr_etf_momo_20_60_v1" in specs
    assert "kr_etf_momo_30_90_v1" in specs

    spec = specs["kr_etf_momo_20_60_v1"]
    history = _build_history(spec.universe)
    strategy = strategy_registry.build(spec, history)
    targets = strategy.generate_targets(history[spec.universe[0]][-1].timestamp)

    assert all(isinstance(item, TargetExposure) for item in targets)
    assert all(hasattr(item, "target_weight") for item in targets)
    assert strategy_registry.kinds() == ("daily_momentum",)
