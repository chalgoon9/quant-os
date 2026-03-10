from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import yaml
from pydantic import Field

from quant_os.domain.models import BacktestSettings, ImmutableModel


class BacktestProfile(ImmutableModel):
    profile_id: str
    description: str
    commission_bps: Decimal = Field(ge=0, default=Decimal("0"))
    slippage_bps: Decimal = Field(ge=0, default=Decimal("0"))
    initial_cash: Decimal | None = Field(default=None, gt=0)

    def to_backtest_settings(self, fallback: BacktestSettings) -> BacktestSettings:
        return BacktestSettings(
            initial_cash=self.initial_cash or fallback.initial_cash,
            commission_bps=self.commission_bps,
            slippage_bps=self.slippage_bps,
        )


def default_backtest_profiles_root() -> Path:
    return Path(__file__).resolve().parents[3] / "conf" / "backtests"


def load_backtest_profile(path: Path) -> BacktestProfile:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return BacktestProfile.model_validate(payload)


def load_backtest_profiles(root: Path | None = None) -> dict[str, BacktestProfile]:
    profiles_root = root or default_backtest_profiles_root()
    profiles: dict[str, BacktestProfile] = {}
    for path in sorted(profiles_root.glob("*.yaml")):
        profile = load_backtest_profile(path)
        profiles[profile.profile_id] = profile
    return profiles
