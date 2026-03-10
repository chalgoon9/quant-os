from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field

from quant_os.domain.models import ImmutableModel, StrategyDefinition


class DailyMomentumSpecParams(ImmutableModel):
    max_names: int = Field(gt=0)
    target_gross_exposure_limit: str
    fast_lookback: int = Field(ge=2)
    slow_lookback: int = Field(ge=3)
    trend_lookback: int = Field(ge=5)
    seed_weights: dict[str, str] | None = None


class StrategySpec(ImmutableModel):
    strategy_id: str
    kind: str
    version: str
    description: str
    dataset_default: str
    universe: tuple[str, ...]
    rebalance_calendar: str
    params: dict[str, object]
    tags: tuple[str, ...] = ()

    def to_strategy_definition(self) -> StrategyDefinition:
        if self.kind != "daily_momentum":
            raise ValueError(f"unsupported strategy kind for direct definition build: {self.kind}")
        params = DailyMomentumSpecParams.model_validate(self.params)
        return StrategyDefinition(
            name=self.strategy_id,
            universe=self.universe,
            rebalance_calendar=self.rebalance_calendar,
            max_names=params.max_names,
            target_gross_exposure_limit=params.target_gross_exposure_limit,
            fast_lookback=params.fast_lookback,
            slow_lookback=params.slow_lookback,
            trend_lookback=params.trend_lookback,
            seed_weights=params.seed_weights,
        )


def default_strategy_specs_root() -> Path:
    return Path(__file__).resolve().parents[3] / "conf" / "strategies"


def load_strategy_spec(path: Path) -> StrategySpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return StrategySpec.model_validate(payload)


def load_strategy_specs(root: Path | None = None) -> dict[str, StrategySpec]:
    specs_root = root or default_strategy_specs_root()
    specs: dict[str, StrategySpec] = {}
    for path in sorted(specs_root.glob("*.yaml")):
        spec = load_strategy_spec(path)
        specs[spec.strategy_id] = spec
    return specs
