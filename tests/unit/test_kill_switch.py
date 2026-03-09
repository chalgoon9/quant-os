from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def test_kill_switch_triggers_and_blocks_new_orders() -> None:
    from quant_os.domain.enums import KillSwitchReason, ReconciliationStatus
    from quant_os.domain.models import LedgerSnapshot, ReconciliationResult
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    snapshot = LedgerSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("95000"),
        positions={},
        realized_pnl=Decimal("-4000"),
        unrealized_pnl=Decimal("0"),
        total_pnl=Decimal("-4000"),
        nav=Decimal("96000"),
    )
    reconciliation = ReconciliationResult(
        reconciliation_id="recon_1",
        occurred_at=as_of,
        status=ReconciliationStatus.MISMATCH,
        mismatch_count=1,
        requires_manual_intervention=True,
        summary="cash mismatch",
        issues=(),
    )
    kill_switch = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
    )

    loss_event = kill_switch.evaluate_daily_loss(snapshot=snapshot, start_of_day_nav=Decimal("100000"))
    recon_event = kill_switch.evaluate_reconciliation(reconciliation)
    stale_event = kill_switch.evaluate_market_data_freshness(
        as_of=as_of,
        latest_market_data_at=as_of - timedelta(hours=2),
    )

    assert loss_event is not None
    assert recon_event is not None
    assert stale_event is not None
    assert kill_switch.can_submit_orders() is False
    assert {event.reason for event in kill_switch.active_events()} == {
        KillSwitchReason.DAILY_LOSS_LIMIT,
        KillSwitchReason.RECONCILIATION_FAILURE,
        KillSwitchReason.STALE_MARKET_DATA,
    }

    kill_switch.reset(as_of + timedelta(minutes=1))

    assert kill_switch.can_submit_orders() is True
    assert kill_switch.active_events() == ()


def test_kill_switch_supports_duplicate_intent_and_unknown_open_order_paths() -> None:
    from quant_os.domain.enums import KillSwitchReason
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    kill_switch = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
    )

    duplicate_intent_event = kill_switch.evaluate_duplicate_intent(
        intent_id="intent_dup_1",
        triggered_at=as_of,
    )
    unknown_order_event = kill_switch.evaluate_unknown_open_orders(
        triggered_at=as_of + timedelta(seconds=1),
        order_ids=("broker-123",),
    )

    assert duplicate_intent_event is not None
    assert duplicate_intent_event.reason is KillSwitchReason.DUPLICATE_INTENT
    assert unknown_order_event is not None
    assert unknown_order_event.reason is KillSwitchReason.UNKNOWN_OPEN_ORDER


def test_kill_switch_detects_unexpected_exposure_and_reject_rate_spike() -> None:
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType, TimeInForce, KillSwitchReason
    from quant_os.domain.models import LedgerSnapshot, OrderProjection, Position
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    snapshot = LedgerSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("1000"),
        positions={
            "ZZZ": Position(
                symbol="ZZZ",
                quantity=Decimal("10"),
                average_cost=Decimal("100"),
                market_price=Decimal("110"),
            )
        },
        realized_pnl=Decimal("0"),
        unrealized_pnl=Decimal("100"),
        total_pnl=Decimal("100"),
        nav=Decimal("2000"),
    )
    orders = [
        OrderProjection(
            order_id=f"order_{index}",
            intent_id=f"intent_{index}",
            strategy_run_id="run_1",
            symbol="AAA",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            quantity=Decimal("1"),
            status=OrderStatus.PRECHECK_REJECTED if index < 6 else OrderStatus.FILLED,
            created_at=as_of,
            updated_at=as_of,
            filled_quantity=Decimal("0"),
        )
        for index in range(10)
    ]
    kill_switch = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
        allowed_symbols=("AAA",),
        max_gross_exposure=Decimal("0.40"),
        reject_rate_window=10,
        reject_rate_threshold=Decimal("0.50"),
    )

    exposure_event = kill_switch.evaluate_unexpected_exposure(snapshot)
    reject_event = kill_switch.evaluate_reject_rate_spike(orders, triggered_at=as_of)

    assert exposure_event is not None
    assert exposure_event.reason is KillSwitchReason.UNEXPECTED_EXPOSURE
    assert reject_event is not None
    assert reject_event.reason is KillSwitchReason.REJECT_RATE_SPIKE


def test_kill_switch_restores_active_events_from_store(tmp_path) -> None:
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import KillSwitchReason
    from quant_os.domain.models import KillSwitchEvent
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    store = OperationalStore(f"sqlite:///{tmp_path / 'kill_switch_restore.db'}")
    store.create_schema()
    store.save_kill_switch_event(
        KillSwitchEvent(
            event_id="killsw_restore_1",
            reason=KillSwitchReason.RECONCILIATION_FAILURE,
            triggered_at=as_of,
            details={"summary": "stored mismatch"},
            is_active=True,
        )
    )

    restored = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
        store=store,
    )

    assert restored.can_submit_orders() is False
    assert restored.active_events()[0].reason is KillSwitchReason.RECONCILIATION_FAILURE
