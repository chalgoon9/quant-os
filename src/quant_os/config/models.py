from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_os.domain.enums import OrderType, TimeInForce, TradingMode
from quant_os.domain.models import (
    BacktestSettings,
    ControlSettings,
    IntentPolicy,
    LiveSettings,
    ResearchSettings,
    RiskPolicy,
    StorageSettings,
    StrategyDefinition,
    SystemConfig,
)


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AppSection(ConfigModel):
    system_name: str


class TradingSection(ConfigModel):
    mode: TradingMode
    base_currency: str
    venue: str


class StrategySection(ConfigModel):
    name: str
    universe: tuple[str, ...]
    rebalance_calendar: str
    max_names: int = Field(gt=0)
    target_gross_exposure_limit: Decimal = Field(gt=0, le=1)
    fast_lookback: int = Field(default=20, ge=2)
    slow_lookback: int = Field(default=60, ge=3)
    trend_lookback: int = Field(default=120, ge=5)
    seed_weights: dict[str, Decimal] | None = None


class RiskSection(ConfigModel):
    max_single_name_weight: Decimal = Field(gt=0, le=1)
    min_cash_buffer: Decimal = Field(ge=0, le=1)
    daily_loss_limit: Decimal = Field(gt=0, le=1)
    max_turnover: Decimal = Field(gt=0, le=1)
    fail_closed: bool = True


class StorageSection(ConfigModel):
    operational_db_url: str
    data_root: Path
    research_root: Path
    artifacts_root: Path

    def resolve(self, base_dir: Path) -> "StorageSection":
        return self.model_copy(
            update={
                "data_root": _resolve_path(self.data_root, base_dir),
                "research_root": _resolve_path(self.research_root, base_dir),
                "artifacts_root": _resolve_path(self.artifacts_root, base_dir),
            },
        )


class ResearchSection(ConfigModel):
    duckdb_path: Path
    market_data_dataset: str = "krx_etf_daily"

    def resolve(self, base_dir: Path) -> "ResearchSection":
        return self.model_copy(update={"duckdb_path": _resolve_path(self.duckdb_path, base_dir)})


class IntentSection(ConfigModel):
    lot_size: Decimal = Field(gt=0)
    min_trade_notional: Decimal = Field(ge=0, default=0)
    default_order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY


class BacktestSection(ConfigModel):
    initial_cash: Decimal = Field(gt=0)
    commission_bps: Decimal = Field(ge=0, default=0)
    slippage_bps: Decimal = Field(ge=0, default=0)
    sell_tax_bps: Decimal = Field(ge=0, default=0)
    max_bar_volume_share: Decimal = Field(gt=0, le=1, default=1)


class ControlsSection(ConfigModel):
    reconciliation_cash_tolerance: Decimal = Field(ge=0, default=0)
    reconciliation_position_tolerance: Decimal = Field(ge=0, default=0)
    stale_market_data_seconds: int = Field(gt=0)
    reject_rate_window: int = Field(gt=0, default=20)
    reject_rate_threshold: Decimal = Field(gt=0, le=1, default=Decimal("0.50"))
    max_gross_exposure: Decimal = Field(gt=0, default=Decimal("1.00"))


class LiveSection(ConfigModel):
    upbit_access_key_env: str = "UPBIT_ACCESS_KEY"
    upbit_secret_key_env: str = "UPBIT_SECRET_KEY"
    upbit_api_base_url: str = "https://api.upbit.com"


class AppSettings(ConfigModel):
    app: AppSection
    trading: TradingSection
    strategy: StrategySection
    risk: RiskSection
    research: ResearchSection
    intent: IntentSection
    backtest: BacktestSection
    controls: ControlsSection
    live: LiveSection = LiveSection()
    storage: StorageSection

    @model_validator(mode="after")
    def validate_risk_vs_strategy(self) -> "AppSettings":
        if self.risk.max_single_name_weight > self.strategy.target_gross_exposure_limit:
            raise ValueError("risk.max_single_name_weight cannot exceed target_gross_exposure_limit")
        return self

    def resolve_paths(self, base_dir: Path) -> "AppSettings":
        return self.model_copy(
            update={
                "storage": self.storage.resolve(base_dir),
                "research": self.research.resolve(base_dir),
            }
        )

    def to_domain_model(self) -> SystemConfig:
        return SystemConfig(
            system_name=self.app.system_name,
            mode=self.trading.mode,
            base_currency=self.trading.base_currency,
            venue=self.trading.venue,
            strategy=StrategyDefinition(
                name=self.strategy.name,
                universe=self.strategy.universe,
                rebalance_calendar=self.strategy.rebalance_calendar,
                max_names=self.strategy.max_names,
                target_gross_exposure_limit=self.strategy.target_gross_exposure_limit,
                fast_lookback=self.strategy.fast_lookback,
                slow_lookback=self.strategy.slow_lookback,
                trend_lookback=self.strategy.trend_lookback,
                seed_weights=self.strategy.seed_weights,
            ),
            risk=RiskPolicy(
                max_single_name_weight=self.risk.max_single_name_weight,
                min_cash_buffer=self.risk.min_cash_buffer,
                daily_loss_limit=self.risk.daily_loss_limit,
                max_turnover=self.risk.max_turnover,
                fail_closed=self.risk.fail_closed,
            ),
            research=ResearchSettings(
                duckdb_path=self.research.duckdb_path,
                market_data_dataset=self.research.market_data_dataset,
            ),
            intent=IntentPolicy(
                lot_size=self.intent.lot_size,
                min_trade_notional=self.intent.min_trade_notional,
                default_order_type=self.intent.default_order_type,
                time_in_force=self.intent.time_in_force,
            ),
            backtest=BacktestSettings(
                initial_cash=self.backtest.initial_cash,
                commission_bps=self.backtest.commission_bps,
                slippage_bps=self.backtest.slippage_bps,
                sell_tax_bps=self.backtest.sell_tax_bps,
                max_bar_volume_share=self.backtest.max_bar_volume_share,
            ),
            controls=ControlSettings(
                reconciliation_cash_tolerance=self.controls.reconciliation_cash_tolerance,
                reconciliation_position_tolerance=self.controls.reconciliation_position_tolerance,
                stale_market_data_seconds=self.controls.stale_market_data_seconds,
                reject_rate_window=self.controls.reject_rate_window,
                reject_rate_threshold=self.controls.reject_rate_threshold,
                max_gross_exposure=self.controls.max_gross_exposure,
            ),
            live=LiveSettings(
                upbit_access_key_env=self.live.upbit_access_key_env,
                upbit_secret_key_env=self.live.upbit_secret_key_env,
                upbit_api_base_url=self.live.upbit_api_base_url,
            ),
            storage=StorageSettings(
                operational_db_url=self.storage.operational_db_url,
                data_root=self.storage.data_root,
                research_root=self.storage.research_root,
                artifacts_root=self.storage.artifacts_root,
            ),
        )


def _resolve_path(path: Path, base_dir: Path) -> Path:
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()
