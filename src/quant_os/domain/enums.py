from __future__ import annotations

from enum import StrEnum


class TradingMode(StrEnum):
    PAPER = "paper"
    SHADOW = "shadow"
    LIVE = "live"


class InstrumentType(StrEnum):
    ETF = "etf"
    EQUITY = "equity"
    CRYPTO_SPOT = "crypto_spot"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(StrEnum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class StrategyRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


class OrderStatus(StrEnum):
    PLANNED = "planned"
    PRECHECK_REJECTED = "precheck_rejected"
    APPROVED = "approved"
    SUBMITTING = "submitting"
    ACKNOWLEDGED = "acknowledged"
    WORKING = "working"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    CANCELLED_PARTIAL = "cancelled_partial"
    EXPIRED = "expired"
    BROKER_REJECTED = "broker_rejected"
    RECONCILE_PENDING = "reconcile_pending"
    MANUAL_INTERVENTION = "manual_intervention"
    BUSTED = "busted"


class OrderEventType(StrEnum):
    STATE_TRANSITION = "state_transition"
    SUBMIT_ACK = "submit_ack"
    SUBMIT_REJECT = "submit_reject"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    RECONCILIATION = "reconciliation"
    MANUAL_NOTE = "manual_note"


class ReconciliationStatus(StrEnum):
    MATCHED = "matched"
    MISMATCH = "mismatch"
    ERROR = "error"


class KillSwitchReason(StrEnum):
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    UNEXPECTED_EXPOSURE = "unexpected_exposure"
    STALE_MARKET_DATA = "stale_market_data"
    RECONCILIATION_FAILURE = "reconciliation_failure"
    EVENT_WRITE_FAILURE = "event_write_failure"
    DUPLICATE_INTENT = "duplicate_intent"
    REJECT_RATE_SPIKE = "reject_rate_spike"
    UNKNOWN_OPEN_ORDER = "unknown_open_order"
