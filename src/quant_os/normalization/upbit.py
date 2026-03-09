from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ValidationError

from quant_os.domain.models import MarketBar
from quant_os.domain.types import ZERO, to_decimal


@dataclass(frozen=True)
class ValidationIssue:
    record_index: int
    code: str
    message: str
    raw_payload: dict[str, object]

    def to_payload(self) -> dict[str, object]:
        return {
            "record_index": self.record_index,
            "code": self.code,
            "message": self.message,
            "raw_payload": self.raw_payload,
        }


@dataclass(frozen=True)
class ValidationReport:
    source: str
    expected_symbol: str
    fetched_at: datetime
    request_params: dict[str, str]
    total_records: int
    valid_records: int
    invalid_records: int

    @property
    def status(self) -> str:
        return "ok" if self.invalid_records == 0 else "quarantined"

    def to_payload(self) -> dict[str, object]:
        return {
            "source": self.source,
            "expected_symbol": self.expected_symbol,
            "fetched_at": self.fetched_at.isoformat(),
            "request_params": self.request_params,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "status": self.status,
        }


@dataclass(frozen=True)
class UpbitNormalizationResult:
    bars: tuple[MarketBar, ...]
    report: ValidationReport
    quarantine_records: tuple[ValidationIssue, ...]


def normalize_upbit_daily_payload(
    payload: list[dict[str, object]],
    *,
    expected_symbol: str,
    fetched_at: datetime,
    request_params: dict[str, str],
    source: str = "upbit_quotation",
) -> UpbitNormalizationResult:
    issues: list[ValidationIssue] = []
    bars: list[MarketBar] = []
    seen: set[tuple[str, datetime]] = set()

    for index, item in enumerate(payload):
        try:
            bar = _normalize_record(item, expected_symbol=expected_symbol)
        except _NormalizationError as exc:
            issues.append(
                ValidationIssue(
                    record_index=index,
                    code=exc.code,
                    message=exc.message,
                    raw_payload=item,
                )
            )
            continue

        dedupe_key = (bar.symbol, bar.timestamp)
        if dedupe_key in seen:
            issues.append(
                ValidationIssue(
                    record_index=index,
                    code="duplicate_timestamp",
                    message=f"duplicate bar detected for {bar.symbol} at {bar.timestamp.isoformat()}",
                    raw_payload=item,
                )
            )
            continue
        seen.add(dedupe_key)
        bars.append(bar)

    report = ValidationReport(
        source=source,
        expected_symbol=expected_symbol,
        fetched_at=fetched_at.astimezone(timezone.utc),
        request_params=request_params,
        total_records=len(payload),
        valid_records=len(bars),
        invalid_records=len(issues),
    )
    return UpbitNormalizationResult(
        bars=tuple(sorted(bars, key=lambda bar: bar.timestamp)),
        report=report,
        quarantine_records=tuple(issues),
    )


class _NormalizationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _normalize_record(payload: dict[str, object], *, expected_symbol: str) -> MarketBar:
    required_fields = (
        "market",
        "candle_date_time_utc",
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "candle_acc_trade_volume",
    )
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise _NormalizationError("missing_field", f"missing required fields: {', '.join(sorted(missing))}")

    market = str(payload["market"]).strip().upper()
    if market != expected_symbol:
        raise _NormalizationError("symbol_mismatch", f"expected {expected_symbol}, got {market}")

    try:
        timestamp = datetime.fromisoformat(str(payload["candle_date_time_utc"])).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise _NormalizationError("invalid_timestamp", f"invalid candle_date_time_utc: {payload['candle_date_time_utc']}") from exc

    open_price = _to_positive_decimal(payload["opening_price"], field_name="opening_price")
    high_price = _to_positive_decimal(payload["high_price"], field_name="high_price")
    low_price = _to_positive_decimal(payload["low_price"], field_name="low_price")
    close_price = _to_positive_decimal(payload["trade_price"], field_name="trade_price")
    volume = _to_non_negative_decimal(payload["candle_acc_trade_volume"], field_name="candle_acc_trade_volume")

    if high_price < max(open_price, close_price, low_price):
        raise _NormalizationError("invalid_price_range", "high_price must be >= open, low, and close")
    if low_price > min(open_price, close_price, high_price):
        raise _NormalizationError("invalid_price_range", "low_price must be <= open, high, and close")

    try:
        return MarketBar(
            symbol=market,
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )
    except ValidationError as exc:
        raise _NormalizationError("model_validation_failed", str(exc)) from exc


def _to_positive_decimal(value: object, *, field_name: str) -> Decimal:
    normalized = to_decimal(value)
    if normalized <= ZERO:
        raise _NormalizationError("non_positive_value", f"{field_name} must be positive")
    return normalized


def _to_non_negative_decimal(value: object, *, field_name: str) -> Decimal:
    normalized = to_decimal(value)
    if normalized < ZERO:
        raise _NormalizationError("negative_value", f"{field_name} must be non-negative")
    return normalized
