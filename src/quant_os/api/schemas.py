from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from quant_os.backtest.results import StoredBacktestResult
from pydantic import BaseModel, ConfigDict, Field

from quant_os.domain.models import DailyReport, FillEvent, KillSwitchEvent, MarketBar, OrderEvent, OrderProjection, ReconciliationResult
from quant_os.domain.types import quantize


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ErrorResponse(ApiModel):
    error: str
    code: str


class RuntimeResponse(ApiModel):
    mode: str
    venue: str
    strategy: str
    execution_adapter: str
    base_currency: str
    research_dataset: str


class DoctorResponse(ApiModel):
    system_name: str
    mode: str
    strategy: str
    research_dataset: str
    intent_lot_size: str
    execution_adapter: str
    required_tables: list[str]


class OpsSummaryResponse(ApiModel):
    nav: str
    cash_balance: str
    realized_pnl: str
    unrealized_pnl: str
    total_pnl: str
    reconciliation_status: str
    reconciliation_summary: str
    active_kill_switch_reasons: list[str]


class OrderListItem(ApiModel):
    order_id: str
    symbol: str
    side: str
    status: str
    quantity: str
    filled_quantity: str
    updated_at: str


class OrdersResponse(ApiModel):
    items: list[OrderListItem]


class OrderProjectionResponse(ApiModel):
    order_id: str
    intent_id: str
    strategy_run_id: str
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    quantity: str
    status: str
    created_at: str
    updated_at: str
    filled_quantity: str
    broker_order_id: str | None = None
    last_event_at: str | None = None


class OrderEventResponse(ApiModel):
    event_id: str
    order_id: str
    intent_id: str
    strategy_run_id: str
    symbol: str
    status: str
    event_type: str
    occurred_at: str
    broker_order_id: str | None = None
    reason: str | None = None
    raw_payload: dict[str, object] | None = None


class FillEventResponse(ApiModel):
    fill_id: str
    order_id: str
    intent_id: str
    strategy_run_id: str
    symbol: str
    side: str
    quantity: str
    price: str
    fee: str
    tax: str
    occurred_at: str
    broker_fill_id: str | None = None
    raw_payload: dict[str, object] | None = None


class OrderDetailResponse(ApiModel):
    projection: OrderProjectionResponse
    events: list[OrderEventResponse]
    fills: list[FillEventResponse]


class ReconciliationIssueResponse(ApiModel):
    code: str
    message: str
    severity: str
    recommended_action: str | None = None
    details: dict[str, object] | None = None


class ReconciliationResponse(ApiModel):
    reconciliation_id: str
    occurred_at: str
    status: str
    mismatch_count: int
    requires_manual_intervention: bool
    summary: str
    issues: list[ReconciliationIssueResponse]


class KillSwitchEventResponse(ApiModel):
    event_id: str
    reason: str
    triggered_at: str
    trigger_value: str | None = None
    threshold_value: str | None = None
    details: dict[str, object] | None = None
    is_active: bool
    cleared_at: str | None = None


class KillSwitchEventsResponse(ApiModel):
    items: list[KillSwitchEventResponse]


class DatasetSummaryResponse(ApiModel):
    dataset: str
    row_count: int
    latest_timestamp: str | None = None


class DatasetListResponse(ApiModel):
    items: list[DatasetSummaryResponse]


class MarketBarResponse(ApiModel):
    symbol: str
    timestamp: str
    open: str
    high: str
    low: str
    close: str
    volume: str


class DatasetBarsResponse(ApiModel):
    dataset: str
    symbol: str | None = None
    items: list[MarketBarResponse]


class UpbitDailyIngestionRequest(ApiModel):
    market: str = Field(min_length=3)
    count: int = Field(default=200, gt=0, le=1000)
    dataset: str | None = None


class UpbitDailyIngestionResponse(ApiModel):
    source: str
    market: str
    dataset: str
    path: str


class DailyReportResponse(ApiModel):
    as_of: str
    base_currency: str
    nav: str
    cash_balance: str
    realized_pnl: str
    unrealized_pnl: str
    total_pnl: str
    reconciliation_status: str
    active_kill_switch_reasons: list[str]
    body_markdown: str


class BacktestSummaryResponse(ApiModel):
    run_id: str
    strategy_id: str
    strategy_name: str
    strategy_kind: str
    strategy_version: str
    dataset: str
    profile_id: str
    generated_at: str
    as_of: str
    initial_cash: str
    final_nav: str
    total_return: str
    max_drawdown: str
    trade_count: int
    loaded_symbols: list[str]
    missing_symbols: list[str]


class BacktestRunListItemResponse(ApiModel):
    run_id: str
    strategy_id: str | None = None
    strategy_name: str
    strategy_kind: str | None = None
    strategy_version: str | None = None
    dataset: str | None = None
    profile_id: str | None = None
    status: str
    started_at: str
    finished_at: str | None = None
    final_nav: str | None = None
    total_return: str | None = None
    max_drawdown: str | None = None
    trade_count: int | None = None


class BacktestRunListResponse(ApiModel):
    items: list[BacktestRunListItemResponse]


class BacktestEquityPointResponse(ApiModel):
    timestamp: str
    nav: str
    cash: str


class BacktestTradeResponse(ApiModel):
    timestamp: str
    symbol: str
    side: str
    quantity: str
    price: str
    notional: str


class BacktestDetailResponse(ApiModel):
    summary: BacktestSummaryResponse
    equity_curve: list[BacktestEquityPointResponse]
    trades: list[BacktestTradeResponse]


class BacktestCompareRequest(ApiModel):
    run_ids: list[str] = Field(min_length=2, max_length=5)


class BacktestCompareResponse(ApiModel):
    items: list[BacktestSummaryResponse]


class StrategyCatalogItemResponse(ApiModel):
    strategy_id: str
    kind: str
    version: str
    description: str
    dataset_default: str
    tags: list[str]


class StrategyCatalogResponse(ApiModel):
    items: list[StrategyCatalogItemResponse]


def order_list_item_from_domain(projection: OrderProjection) -> OrderListItem:
    return OrderListItem(
        order_id=projection.order_id,
        symbol=projection.symbol,
        side=projection.side.value,
        status=projection.status.value,
        quantity=_decimal_string(projection.quantity, digits="0.0000"),
        filled_quantity=_decimal_string(projection.filled_quantity, digits="0.0000"),
        updated_at=_iso_datetime(projection.updated_at),
    )


def order_projection_from_domain(projection: OrderProjection) -> OrderProjectionResponse:
    return OrderProjectionResponse(
        order_id=projection.order_id,
        intent_id=projection.intent_id,
        strategy_run_id=projection.strategy_run_id,
        symbol=projection.symbol,
        side=projection.side.value,
        order_type=projection.order_type.value,
        time_in_force=projection.time_in_force.value,
        quantity=_decimal_string(projection.quantity, digits="0.0000"),
        status=projection.status.value,
        created_at=_iso_datetime(projection.created_at),
        updated_at=_iso_datetime(projection.updated_at),
        filled_quantity=_decimal_string(projection.filled_quantity, digits="0.0000"),
        broker_order_id=projection.broker_order_id,
        last_event_at=_iso_datetime(projection.last_event_at) if projection.last_event_at is not None else None,
    )


def order_event_from_domain(event: OrderEvent) -> OrderEventResponse:
    return OrderEventResponse(
        event_id=event.event_id,
        order_id=event.order_id,
        intent_id=event.intent_id,
        strategy_run_id=event.strategy_run_id,
        symbol=event.symbol,
        status=event.status.value,
        event_type=event.event_type.value,
        occurred_at=_iso_datetime(event.occurred_at),
        broker_order_id=event.broker_order_id,
        reason=event.reason,
        raw_payload=event.raw_payload,
    )


def fill_event_from_domain(fill: FillEvent) -> FillEventResponse:
    return FillEventResponse(
        fill_id=fill.fill_id,
        order_id=fill.order_id,
        intent_id=fill.intent_id,
        strategy_run_id=fill.strategy_run_id,
        symbol=fill.symbol,
        side=fill.side.value,
        quantity=_decimal_string(fill.quantity, digits="0.0000"),
        price=_decimal_string(fill.price, digits="0.0000"),
        fee=_decimal_string(fill.fee, digits="0.0000"),
        tax=_decimal_string(fill.tax, digits="0.0000"),
        occurred_at=_iso_datetime(fill.occurred_at),
        broker_fill_id=fill.broker_fill_id,
        raw_payload=fill.raw_payload,
    )


def reconciliation_from_domain(result: ReconciliationResult) -> ReconciliationResponse:
    return ReconciliationResponse(
        reconciliation_id=result.reconciliation_id,
        occurred_at=_iso_datetime(result.occurred_at),
        status=result.status.value,
        mismatch_count=result.mismatch_count,
        requires_manual_intervention=result.requires_manual_intervention,
        summary=result.summary,
        issues=[
            ReconciliationIssueResponse(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
                recommended_action=issue.recommended_action,
                details=issue.details,
            )
            for issue in result.issues
        ],
    )


def kill_switch_event_from_domain(event: KillSwitchEvent) -> KillSwitchEventResponse:
    return KillSwitchEventResponse(
        event_id=event.event_id,
        reason=event.reason.value,
        triggered_at=_iso_datetime(event.triggered_at),
        trigger_value=_decimal_string(event.trigger_value, digits="0.000000") if event.trigger_value is not None else None,
        threshold_value=_decimal_string(event.threshold_value, digits="0.000000") if event.threshold_value is not None else None,
        details=event.details,
        is_active=event.is_active,
        cleared_at=_iso_datetime(event.cleared_at) if event.cleared_at is not None else None,
    )


def market_bar_from_domain(bar: MarketBar) -> MarketBarResponse:
    return MarketBarResponse(
        symbol=bar.symbol,
        timestamp=_iso_datetime(bar.timestamp),
        open=_decimal_string(bar.open, digits="0.0000"),
        high=_decimal_string(bar.high, digits="0.0000"),
        low=_decimal_string(bar.low, digits="0.0000"),
        close=_decimal_string(bar.close, digits="0.0000"),
        volume=_decimal_string(bar.volume, digits="0.0000"),
    )


def daily_report_from_domain(report: DailyReport) -> DailyReportResponse:
    return DailyReportResponse(
        as_of=_iso_datetime(report.as_of),
        base_currency=report.base_currency,
        nav=_decimal_string(report.nav, digits="0.0000"),
        cash_balance=_decimal_string(report.cash_balance, digits="0.0000"),
        realized_pnl=_decimal_string(report.realized_pnl, digits="0.0000"),
        unrealized_pnl=_decimal_string(report.unrealized_pnl, digits="0.0000"),
        total_pnl=_decimal_string(report.total_pnl, digits="0.0000"),
        reconciliation_status=report.reconciliation_status.value,
        active_kill_switch_reasons=[reason.value for reason in report.active_kill_switch_reasons],
        body_markdown=report.body_markdown,
    )


def backtest_detail_from_domain(result: StoredBacktestResult) -> BacktestDetailResponse:
    return BacktestDetailResponse(
        summary=backtest_summary_from_domain(result),
        equity_curve=[
            BacktestEquityPointResponse(
                timestamp=_iso_datetime(point.timestamp),
                nav=_decimal_string(point.nav, digits="0.0000"),
                cash=_decimal_string(point.cash, digits="0.0000"),
            )
            for point in result.equity_curve
        ],
        trades=[
            BacktestTradeResponse(
                timestamp=_iso_datetime(trade.timestamp),
                symbol=trade.symbol,
                side=trade.side.value,
                quantity=_decimal_string(trade.quantity, digits="0.0000"),
                price=_decimal_string(trade.price, digits="0.0000"),
                notional=_decimal_string(trade.notional, digits="0.0000"),
            )
            for trade in result.trades
        ],
    )


def backtest_summary_from_domain(result: StoredBacktestResult) -> BacktestSummaryResponse:
    return BacktestSummaryResponse(
        run_id=result.run_id,
        strategy_id=result.strategy_id,
        strategy_name=result.strategy_name,
        strategy_kind=result.strategy_kind,
        strategy_version=result.strategy_version,
        dataset=result.dataset,
        profile_id=result.profile_id,
        generated_at=_iso_datetime(result.generated_at),
        as_of=_iso_datetime(result.as_of),
        initial_cash=_decimal_string(result.initial_cash, digits="0.0000"),
        final_nav=_decimal_string(result.final_nav, digits="0.0000"),
        total_return=_decimal_string(result.total_return, digits="0.0000"),
        max_drawdown=_decimal_string(result.max_drawdown, digits="0.0000"),
        trade_count=result.trade_count,
        loaded_symbols=list(result.loaded_symbols),
        missing_symbols=list(result.missing_symbols),
    )


def _decimal_string(value: Decimal, *, digits: str) -> str:
    return format(quantize(value, digits), "f")


def _iso_datetime(value: datetime) -> str:
    return value.isoformat()
