from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import yaml

from quant_os.config.loader import load_settings
from quant_os.domain.enums import KillSwitchReason, OrderEventType, OrderSide, OrderStatus, OrderType, ReconciliationStatus
from quant_os.domain.models import (
    CashLedgerEntry,
    FillEvent,
    KillSwitchEvent,
    LedgerSnapshot,
    OrderEvent,
    OrderProjection,
    Position,
    ReconciliationIssue,
    ReconciliationResult,
)
from quant_os.services.wiring import build_app_runtime


def write_test_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "base.yaml"
    payload = {
        "app": {"system_name": "quant-os-mvp"},
        "trading": {"mode": "paper", "base_currency": "KRW", "venue": "upbit"},
        "strategy": {
            "name": "daily_momentum",
            "universe": ["KRW-BTC"],
            "rebalance_calendar": "daily",
            "max_names": 1,
            "target_gross_exposure_limit": "0.95",
            "fast_lookback": 20,
            "slow_lookback": 60,
            "trend_lookback": 40,
        },
        "risk": {
            "max_single_name_weight": "0.20",
            "min_cash_buffer": "0.05",
            "daily_loss_limit": "0.03",
            "max_turnover": "0.25",
            "fail_closed": True,
        },
        "research": {
            "duckdb_path": "./research/quant_os.duckdb",
            "market_data_dataset": "krx_etf_daily",
        },
        "intent": {
            "lot_size": "1",
            "min_trade_notional": "1000",
            "default_order_type": "market",
            "time_in_force": "day",
        },
        "backtest": {
            "initial_cash": "10000000",
            "commission_bps": "5",
            "slippage_bps": "5",
        },
        "controls": {
            "reconciliation_cash_tolerance": "1",
            "reconciliation_position_tolerance": "0.001",
            "stale_market_data_seconds": 86400,
        },
        "storage": {
            "operational_db_url": f"sqlite:///{tmp_path / 'var' / 'quant_os.db'}",
            "data_root": "./data",
            "research_root": "./research",
            "artifacts_root": "./data/artifacts",
        },
    }
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return config_path


def build_seeded_runtime(tmp_path: Path):
    config_path = write_test_config(tmp_path)
    settings = load_settings(config_path)
    runtime = build_app_runtime(settings)
    runtime.operational_store.create_schema()
    return config_path, runtime


def seed_ops_snapshot(runtime) -> None:
    as_of = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)
    runtime.operational_store.append_cash_ledger_entry(
        CashLedgerEntry(
            entry_id="cash_1",
            occurred_at=as_of,
            currency="KRW",
            amount=Decimal("0"),
            balance_after=Decimal("99425"),
            reference_type="seed",
            reference_id="seed_1",
            notes="seed cash",
        )
    )
    runtime.operational_store.append_ledger_snapshot(
        LedgerSnapshot(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("99425"),
            positions={
                "AAA": Position(
                    symbol="AAA",
                    quantity=Decimal("6"),
                    average_cost=Decimal("101"),
                    market_price=Decimal("120"),
                )
            },
            realized_pnl=Decimal("31"),
            unrealized_pnl=Decimal("114"),
            total_pnl=Decimal("145"),
            nav=Decimal("100145"),
        ),
        source="paper",
    )
    runtime.operational_store.append_reconciliation_result(
        ReconciliationResult(
            reconciliation_id="recon_1",
            occurred_at=as_of,
            status=ReconciliationStatus.MATCHED,
            mismatch_count=0,
            requires_manual_intervention=False,
            summary="reconciliation matched",
            issues=(),
        )
    )


def seed_active_kill_switch(runtime) -> None:
    runtime.operational_store.save_kill_switch_event(
        KillSwitchEvent(
            event_id="killsw_1",
            reason=KillSwitchReason.RECONCILIATION_FAILURE,
            triggered_at=datetime(2026, 3, 10, 0, 5, tzinfo=timezone.utc),
            trigger_value=Decimal("1"),
            threshold_value=Decimal("0"),
            details={"summary": "cash mismatch"},
            is_active=True,
        )
    )


def seed_order(runtime) -> str:
    start = datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc)
    event = OrderEvent(
        event_id="ordevt_1",
        order_id="order_1",
        intent_id="intent_1",
        strategy_run_id="run_1",
        symbol="AAA",
        status=OrderStatus.ACKNOWLEDGED,
        event_type=OrderEventType.STATE_TRANSITION,
        occurred_at=start,
        broker_order_id="paper-order_1",
    )
    projection = OrderProjection(
        order_id="order_1",
        intent_id="intent_1",
        strategy_run_id="run_1",
        symbol="AAA",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        time_in_force="day",
        quantity=Decimal("10"),
        status=OrderStatus.PARTIALLY_FILLED,
        created_at=start,
        updated_at=start + timedelta(seconds=10),
        filled_quantity=Decimal("5"),
        broker_order_id="paper-order_1",
        last_event_at=start + timedelta(seconds=10),
    )
    fill = FillEvent(
        fill_id="fill_1",
        order_id="order_1",
        intent_id="intent_1",
        strategy_run_id="run_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("5"),
        price=Decimal("100"),
        fee=Decimal("0"),
        tax=Decimal("0"),
        occurred_at=start + timedelta(seconds=9),
    )
    runtime.operational_store.append_order_event(event)
    runtime.operational_store.upsert_order_projection(projection, projection_source_event_id=event.event_id)
    runtime.operational_store.append_fill(fill)
    return projection.order_id


def seed_reconciliation_mismatch(runtime) -> None:
    runtime.operational_store.append_reconciliation_result(
        ReconciliationResult(
            reconciliation_id="recon_2",
            occurred_at=datetime(2026, 3, 10, 0, 10, tzinfo=timezone.utc),
            status=ReconciliationStatus.MISMATCH,
            mismatch_count=1,
            requires_manual_intervention=True,
            summary="1 mismatch(es): cash_balance_mismatch",
            issues=(
                ReconciliationIssue(
                    code="cash_balance_mismatch",
                    message="cash balance mismatch",
                    details={"local": "100.0000", "external": "99.0000"},
                ),
            ),
        )
    )
