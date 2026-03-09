from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from quant_os.domain.enums import (
    InstrumentType,
    KillSwitchReason,
    OrderEventType,
    OrderSide,
    OrderStatus,
    OrderType,
    ReconciliationStatus,
    StrategyRunStatus,
    TimeInForce,
    TradingMode,
)
from quant_os.domain.types import ONE, ZERO, quantize, to_decimal


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ImmutableModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class TargetExposure(ImmutableModel):
    symbol: str
    target_weight: Decimal = Field(ge=Decimal("-1"), le=ONE)
    instrument_type: InstrumentType = InstrumentType.ETF
    rationale: str | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("symbol must not be empty")
        return normalized


class MarketBar(ImmutableModel):
    symbol: str
    timestamp: datetime
    open: Decimal = Field(gt=ZERO)
    high: Decimal = Field(gt=ZERO)
    low: Decimal = Field(gt=ZERO)
    close: Decimal = Field(gt=ZERO)
    volume: Decimal = Field(ge=ZERO)

    @field_validator("symbol")
    @classmethod
    def normalize_market_bar_symbol(cls, value: str) -> str:
        return TargetExposure.normalize_symbol(value)


class OrderIntent(ImmutableModel):
    intent_id: str
    strategy_run_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal = Field(gt=ZERO)
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Decimal | None = Field(default=None, gt=ZERO)
    created_at: datetime = Field(default_factory=utc_now)
    rationale: str | None = None


class SubmitResult(ImmutableModel):
    accepted: bool
    order_id: str | None = None
    status: OrderStatus
    message: str | None = None


class OrderEvent(ImmutableModel):
    event_id: str
    order_id: str
    intent_id: str
    strategy_run_id: str
    symbol: str
    status: OrderStatus
    event_type: OrderEventType
    occurred_at: datetime
    broker_order_id: str | None = None
    reason: str | None = None
    raw_payload: dict[str, object] | None = None


class FillEvent(ImmutableModel):
    fill_id: str
    order_id: str
    intent_id: str
    strategy_run_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal = Field(gt=ZERO)
    price: Decimal = Field(gt=ZERO)
    fee: Decimal = Field(default=ZERO, ge=ZERO)
    tax: Decimal = Field(default=ZERO, ge=ZERO)
    occurred_at: datetime
    broker_fill_id: str | None = None
    raw_payload: dict[str, object] | None = None


class Position(ImmutableModel):
    symbol: str
    quantity: Decimal
    average_cost: Decimal = Field(ge=ZERO)
    market_price: Decimal | None = Field(default=None, gt=ZERO)

    @property
    def market_value(self) -> Decimal | None:
        if self.market_price is None:
            return None
        return quantize(self.quantity * self.market_price, "0.00000001")


class PortfolioState(ImmutableModel):
    as_of: datetime
    base_currency: str
    cash_balance: Decimal
    net_asset_value: Decimal = Field(gt=ZERO)
    positions: tuple[Position, ...] = ()
    market_prices: dict[str, Decimal] = Field(default_factory=dict)


class OrderProjection(ImmutableModel):
    order_id: str
    intent_id: str
    strategy_run_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Decimal = Field(gt=ZERO)
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    filled_quantity: Decimal = Field(default=ZERO, ge=ZERO)
    broker_order_id: str | None = None
    last_event_at: datetime | None = None


class CashLedgerEntry(ImmutableModel):
    entry_id: str
    occurred_at: datetime
    currency: str
    amount: Decimal
    balance_after: Decimal
    reference_type: str
    reference_id: str
    notes: str | None = None


class PositionLot(ImmutableModel):
    lot_id: str
    symbol: str
    opened_at: datetime
    quantity: Decimal = Field(gt=ZERO)
    unit_cost: Decimal = Field(gt=ZERO)


class LedgerSnapshot(ImmutableModel):
    as_of: datetime
    base_currency: str
    cash_balance: Decimal
    positions: dict[str, Position]
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    nav: Decimal


class ExternalStateSnapshot(ImmutableModel):
    as_of: datetime
    base_currency: str
    cash_balance: Decimal
    positions: tuple[Position, ...] = ()
    open_orders: tuple[OrderProjection, ...] = ()


class ReconciliationIssue(ImmutableModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class ReconciliationResult(ImmutableModel):
    reconciliation_id: str
    occurred_at: datetime
    status: ReconciliationStatus
    mismatch_count: int = Field(ge=0)
    requires_manual_intervention: bool
    summary: str
    issues: tuple[ReconciliationIssue, ...] = ()


class RiskPolicy(ImmutableModel):
    max_single_name_weight: Decimal = Field(gt=ZERO, le=ONE)
    min_cash_buffer: Decimal = Field(ge=ZERO, le=ONE)
    daily_loss_limit: Decimal = Field(gt=ZERO, le=ONE)
    max_turnover: Decimal = Field(gt=ZERO, le=ONE)
    fail_closed: bool = True


class StrategyDefinition(ImmutableModel):
    name: str
    universe: tuple[str, ...]
    rebalance_calendar: str
    max_names: int = Field(gt=0)
    target_gross_exposure_limit: Decimal = Field(gt=ZERO, le=ONE)
    fast_lookback: int = Field(default=20, ge=2)
    slow_lookback: int = Field(default=60, ge=3)
    trend_lookback: int = Field(default=120, ge=5)
    seed_weights: dict[str, Decimal] | None = None

    @model_validator(mode="after")
    def validate_seed_weights(self) -> "StrategyDefinition":
        if self.max_names > len(self.universe):
            raise ValueError("max_names cannot exceed universe size")
        if self.fast_lookback >= self.slow_lookback:
            raise ValueError("fast_lookback must be smaller than slow_lookback")
        if not self.seed_weights:
            return self
        missing = set(self.seed_weights) - set(self.universe)
        if missing:
            raise ValueError(f"seed_weights contains unknown symbols: {sorted(missing)}")
        gross = sum(abs(weight) for weight in self.seed_weights.values())
        if gross > self.target_gross_exposure_limit:
            raise ValueError("seed_weights exceed target_gross_exposure_limit")
        return self

    def seed_targets(self) -> list[TargetExposure]:
        if self.seed_weights:
            return [
                TargetExposure(symbol=symbol, target_weight=weight, rationale="config-seed")
                for symbol, weight in self.seed_weights.items()
                if weight != ZERO
            ]
        equal_weight = quantize(
            to_decimal(self.target_gross_exposure_limit) / Decimal(self.max_names),
            "0.0001",
        )
        return [
            TargetExposure(symbol=symbol, target_weight=equal_weight, rationale="equal-weight-seed")
            for symbol in self.universe[: self.max_names]
        ]

    def required_history_window(self) -> int:
        return max(self.slow_lookback, self.trend_lookback)


class StorageSettings(ImmutableModel):
    operational_db_url: str
    data_root: Path
    research_root: Path
    artifacts_root: Path


class ResearchSettings(ImmutableModel):
    duckdb_path: Path
    market_data_dataset: str = "krx_etf_daily"


class IntentPolicy(ImmutableModel):
    lot_size: Decimal = Field(gt=ZERO)
    min_trade_notional: Decimal = Field(ge=ZERO, default=ZERO)
    default_order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY


class BacktestSettings(ImmutableModel):
    initial_cash: Decimal = Field(gt=ZERO)
    commission_bps: Decimal = Field(ge=ZERO, default=ZERO)
    slippage_bps: Decimal = Field(ge=ZERO, default=ZERO)


class ControlSettings(ImmutableModel):
    reconciliation_cash_tolerance: Decimal = Field(ge=ZERO, default=ZERO)
    reconciliation_position_tolerance: Decimal = Field(ge=ZERO, default=ZERO)
    stale_market_data_seconds: int = Field(gt=0)


class SystemConfig(ImmutableModel):
    system_name: str
    mode: TradingMode
    base_currency: str
    venue: str
    strategy: StrategyDefinition
    risk: RiskPolicy
    research: ResearchSettings
    intent: IntentPolicy
    backtest: BacktestSettings
    controls: ControlSettings
    storage: StorageSettings


class StrategyRun(ImmutableModel):
    strategy_run_id: str
    strategy_name: str
    mode: TradingMode
    status: StrategyRunStatus
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None


class KillSwitchEvent(ImmutableModel):
    event_id: str
    reason: KillSwitchReason
    triggered_at: datetime
    trigger_value: Decimal | None = None
    threshold_value: Decimal | None = None
    details: dict[str, object] | None = None
    is_active: bool = True
    cleared_at: datetime | None = None


class DailyReport(ImmutableModel):
    as_of: datetime
    base_currency: str
    nav: Decimal
    cash_balance: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    reconciliation_status: ReconciliationStatus
    active_kill_switch_reasons: tuple[KillSwitchReason, ...] = ()
    body_markdown: str
