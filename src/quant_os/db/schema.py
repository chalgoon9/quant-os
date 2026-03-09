from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from quant_os.db.base import Base


AMOUNT_TYPE = Numeric(24, 8)
PRICE_TYPE = Numeric(24, 8)
WEIGHT_TYPE = Numeric(12, 6)

REQUIRED_TABLES = {
    "strategy_runs",
    "orders",
    "order_events",
    "fills",
    "positions_snapshot",
    "cash_ledger",
    "pnl_snapshot",
    "reconciliation_log",
    "kill_switch_events",
}


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class StrategyRunRecord(Base):
    __tablename__ = "strategy_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)


class OrderRecord(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("intent_id"),
        UniqueConstraint("broker_order_id"),
        Index("ix_orders_status_updated_at", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_run_id: Mapped[str] = mapped_column(ForeignKey("strategy_runs.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    time_in_force: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, default=Decimal("0"), nullable=False)
    limit_price: Mapped[Decimal | None] = mapped_column(PRICE_TYPE)
    broker_order_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    projection_source_event_id: Mapped[str | None] = mapped_column(String(64))


class OrderEventRecord(Base):
    __tablename__ = "order_events"
    __table_args__ = (
        Index("ix_order_events_order_id_occurred_at", "order_id", "occurred_at"),
        Index("ix_order_events_broker_order_id", "broker_order_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_run_id: Mapped[str] = mapped_column(ForeignKey("strategy_runs.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String(128))
    reason: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON)


class FillRecord(Base):
    __tablename__ = "fills"
    __table_args__ = (
        UniqueConstraint("broker_fill_id"),
        Index("ix_fills_order_id_occurred_at", "order_id", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_run_id: Mapped[str] = mapped_column(ForeignKey("strategy_runs.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    price: Mapped[Decimal] = mapped_column(PRICE_TYPE, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    fee: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, default=Decimal("0"), nullable=False)
    tax: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, default=Decimal("0"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    broker_fill_id: Mapped[str | None] = mapped_column(String(128))
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(JSON)


class PositionSnapshotRecord(Base):
    __tablename__ = "positions_snapshot"
    __table_args__ = (Index("ix_positions_snapshot_symbol_snapshot_at", "symbol", "snapshot_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    average_cost: Mapped[Decimal] = mapped_column(PRICE_TYPE, nullable=False)
    market_price: Mapped[Decimal | None] = mapped_column(PRICE_TYPE)
    market_value: Mapped[Decimal | None] = mapped_column(AMOUNT_TYPE)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(AMOUNT_TYPE)
    source: Mapped[str] = mapped_column(String(32), nullable=False)


class CashLedgerRecord(Base):
    __tablename__ = "cash_ledger"
    __table_args__ = (Index("ix_cash_ledger_occurred_at", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    balance_after: Mapped[Decimal | None] = mapped_column(AMOUNT_TYPE)
    reference_type: Mapped[str | None] = mapped_column(String(32))
    reference_id: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)


class PnlSnapshotRecord(Base):
    __tablename__ = "pnl_snapshot"
    __table_args__ = (Index("ix_pnl_snapshot_snapshot_at", "snapshot_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, default=Decimal("0"), nullable=False)
    unrealized_pnl: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, default=Decimal("0"), nullable=False)
    total_pnl: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, default=Decimal("0"), nullable=False)
    nav: Mapped[Decimal] = mapped_column(AMOUNT_TYPE, nullable=False)
    gross_exposure: Mapped[Decimal] = mapped_column(WEIGHT_TYPE, nullable=False)
    net_exposure: Mapped[Decimal] = mapped_column(WEIGHT_TYPE, nullable=False)


class ReconciliationLogRecord(Base):
    __tablename__ = "reconciliation_log"
    __table_args__ = (Index("ix_reconciliation_log_occurred_at", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    mismatch_count: Mapped[int] = mapped_column(nullable=False, default=0)
    requires_manual_intervention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON)


class KillSwitchEventRecord(Base):
    __tablename__ = "kill_switch_events"
    __table_args__ = (Index("ix_kill_switch_events_triggered_at", "triggered_at"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trigger_value: Mapped[Decimal | None] = mapped_column(WEIGHT_TYPE)
    threshold_value: Mapped[Decimal | None] = mapped_column(WEIGHT_TYPE)
    details: Mapped[dict[str, object] | None] = mapped_column(JSON)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
