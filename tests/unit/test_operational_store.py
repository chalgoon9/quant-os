from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def test_operational_store_persists_execution_and_ops_records(tmp_path) -> None:
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import KillSwitchReason, OrderEventType, OrderSide, OrderStatus, OrderType, ReconciliationStatus
    from quant_os.domain.models import (
        FillEvent,
        KillSwitchEvent,
        LedgerSnapshot,
        OrderEvent,
        OrderProjection,
        Position,
        ReconciliationIssue,
        ReconciliationResult,
    )

    as_of = datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc)
    store = OperationalStore(f"sqlite:///{tmp_path / 'ops.db'}")
    store.create_schema()

    order_event = OrderEvent(
        event_id="ordevt_1",
        order_id="order_1",
        intent_id="intent_1",
        strategy_run_id="run_1",
        symbol="AAA",
        status=OrderStatus.ACKNOWLEDGED,
        event_type=OrderEventType.STATE_TRANSITION,
        occurred_at=as_of,
        broker_order_id="broker_1",
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
        status=OrderStatus.ACKNOWLEDGED,
        created_at=as_of,
        updated_at=as_of,
        filled_quantity=Decimal("0"),
        broker_order_id="broker_1",
        last_event_at=as_of,
    )
    fill = FillEvent(
        fill_id="fill_1",
        order_id="order_1",
        intent_id="intent_1",
        strategy_run_id="run_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        price=Decimal("100"),
        fee=Decimal("5"),
        tax=Decimal("0"),
        occurred_at=as_of + timedelta(seconds=1),
        broker_fill_id="bf_1",
    )
    snapshot = LedgerSnapshot(
        as_of=as_of + timedelta(seconds=1),
        base_currency="KRW",
        cash_balance=Decimal("98995"),
        positions={
            "AAA": Position(
                symbol="AAA",
                quantity=Decimal("10"),
                average_cost=Decimal("100.5"),
                market_price=Decimal("101"),
            )
        },
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("5"),
        total_pnl=Decimal("5"),
        nav=Decimal("100005"),
    )
    reconciliation = ReconciliationResult(
        reconciliation_id="recon_1",
        occurred_at=as_of + timedelta(minutes=1),
        status=ReconciliationStatus.MISMATCH,
        mismatch_count=1,
        requires_manual_intervention=True,
        summary="cash mismatch",
        issues=(
            ReconciliationIssue(code="cash_balance_mismatch", message="cash mismatch"),
        ),
    )
    kill_event = KillSwitchEvent(
        event_id="ks_1",
        reason=KillSwitchReason.RECONCILIATION_FAILURE,
        triggered_at=as_of + timedelta(minutes=1),
        trigger_value=Decimal("1"),
        threshold_value=Decimal("0"),
        details={"summary": "cash mismatch"},
        is_active=True,
    )

    store.append_order_event(order_event)
    store.upsert_order_projection(projection, projection_source_event_id=order_event.event_id)
    store.append_fill(fill)
    store.append_ledger_snapshot(snapshot, source="paper")
    store.append_reconciliation_result(reconciliation)
    store.save_kill_switch_event(kill_event)

    assert store.get_order_projection("order_1").status is OrderStatus.ACKNOWLEDGED
    assert len(store.list_order_events("order_1")) == 1
    assert len(store.list_fills("order_1")) == 1
    assert store.latest_pnl_snapshot().nav == Decimal("100005.0000")
    assert store.latest_reconciliation_result().status is ReconciliationStatus.MISMATCH
    assert store.active_kill_switch_events()[0].reason is KillSwitchReason.RECONCILIATION_FAILURE


def test_operational_store_persists_catalog_strategy_run_fields(tmp_path) -> None:
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import StrategyRunStatus
    from quant_os.domain.models import StrategyRun

    as_of = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)
    store = OperationalStore(f"sqlite:///{tmp_path / 'ops.db'}")
    store.create_schema()

    store.start_strategy_run(
        StrategyRun(
            strategy_run_id="run_1",
            strategy_name="국내 ETF 일봉 20/60 모멘텀 참조 전략",
            mode="backtest",
            status=StrategyRunStatus.RUNNING,
            strategy_id="kr_etf_momo_20_60_v1",
            strategy_kind="daily_momentum",
            strategy_version="v1",
            dataset="krx_etf_daily",
            profile_id="baseline",
            artifact_path="data/artifacts/backtests/kr_etf_momo_20_60_v1/example.json",
            config_fingerprint="abc123",
            tags_json=("krx", "momentum"),
            notes="unit test run",
            started_at=as_of,
            config_payload={"seed": "x"},
        )
    )

    run = store.get_strategy_run("run_1")
    filtered = store.list_strategy_runs(limit=10, strategy_id="kr_etf_momo_20_60_v1", dataset="krx_etf_daily")

    assert run.strategy_id == "kr_etf_momo_20_60_v1"
    assert run.strategy_kind == "daily_momentum"
    assert run.profile_id == "baseline"
    assert run.artifact_path is not None
    assert run.config_fingerprint == "abc123"
    assert run.tags_json == ("krx", "momentum")
    assert run.notes == "unit test run"
    assert len(filtered) == 1


def test_operational_store_keeps_legacy_strategy_run_creation_compatible(tmp_path) -> None:
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import StrategyRunStatus
    from quant_os.domain.models import StrategyRun

    store = OperationalStore(f"sqlite:///{tmp_path / 'ops_legacy.db'}")
    store.create_schema()
    store.start_strategy_run(
        StrategyRun(
            strategy_run_id="legacy_1",
            strategy_name="daily_momentum",
            mode="backtest",
            status=StrategyRunStatus.RUNNING,
        )
    )

    run = store.get_strategy_run("legacy_1")

    assert run.strategy_id is None
    assert run.profile_id is None
    assert run.tags_json == ()
