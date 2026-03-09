from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from statistics import fmean

from quant_os.domain.models import MarketBar, StrategyDefinition, TargetExposure
from quant_os.domain.types import ZERO, quantize


class DailyMomentumStrategy:
    def __init__(self, config: StrategyDefinition, bars_by_symbol: Mapping[str, Sequence[MarketBar]]) -> None:
        self.config = config
        self.bars_by_symbol = {symbol: sorted(list(bars), key=lambda bar: bar.timestamp) for symbol, bars in bars_by_symbol.items()}

    def generate_targets(self, as_of) -> list[TargetExposure]:
        candidates: list[tuple[str, Decimal]] = []
        for symbol in self.config.universe:
            bars = [bar for bar in self.bars_by_symbol.get(symbol, ()) if bar.timestamp <= as_of]
            if len(bars) < self.config.required_history_window():
                continue
            signal = _compute_signal(
                bars=bars,
                fast_lookback=self.config.fast_lookback,
                slow_lookback=self.config.slow_lookback,
                trend_lookback=self.config.trend_lookback,
            )
            if signal > ZERO:
                candidates.append((symbol, signal))

        if not candidates:
            return []

        selected = sorted(candidates, key=lambda item: item[1], reverse=True)[: self.config.max_names]
        weight = quantize(self.config.target_gross_exposure_limit / Decimal(len(selected)), "0.0001")
        return [
            TargetExposure(symbol=symbol, target_weight=weight, rationale=f"momentum:{signal}")
            for symbol, signal in selected
        ]


def _compute_signal(
    bars: Sequence[MarketBar],
    fast_lookback: int,
    slow_lookback: int,
    trend_lookback: int,
) -> Decimal:
    latest = bars[-1].close
    fast_reference = bars[-fast_lookback].close
    slow_reference = bars[-slow_lookback].close
    trend_mean = Decimal(str(fmean(float(bar.close) for bar in bars[-trend_lookback:])))

    fast_momentum = (latest / fast_reference) - Decimal("1")
    slow_momentum = (latest / slow_reference) - Decimal("1")
    trend_ok = latest >= trend_mean

    if fast_momentum <= ZERO or slow_momentum <= ZERO or not trend_ok:
        return ZERO
    return quantize(fast_momentum + slow_momentum, "0.0001")
