from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from quant_os.domain.models import MarketBar
from quant_os.strategy.momentum import DailyMomentumStrategy
from quant_os.strategy.specs import StrategySpec


StrategyBuilder = Callable[[StrategySpec, Mapping[str, Sequence[MarketBar]]], object]


class StrategyRegistry:
    def __init__(self) -> None:
        self._builders: dict[str, StrategyBuilder] = {}

    def register(self, kind: str, builder: StrategyBuilder) -> None:
        self._builders[kind] = builder

    def build(self, spec: StrategySpec, bars_by_symbol: Mapping[str, Sequence[MarketBar]]) -> object:
        try:
            builder = self._builders[spec.kind]
        except KeyError as exc:
            raise KeyError(f"unknown strategy kind: {spec.kind}") from exc
        return builder(spec, bars_by_symbol)

    def kinds(self) -> tuple[str, ...]:
        return tuple(sorted(self._builders))


def _build_daily_momentum(spec: StrategySpec, bars_by_symbol: Mapping[str, Sequence[MarketBar]]) -> DailyMomentumStrategy:
    return DailyMomentumStrategy(spec.to_strategy_definition(), bars_by_symbol)


strategy_registry = StrategyRegistry()
strategy_registry.register("daily_momentum", _build_daily_momentum)
