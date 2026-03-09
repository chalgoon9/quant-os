from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest


def test_simulation_timeout_maps_to_reconcile_pending() -> None:
    from quant_os.adapters.paper import PaperAdapter, PaperExecutionPolicy
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    adapter = PaperAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        ),
        execution_policy=PaperExecutionPolicy(uncertain_submit=True),
    )
    intent = OrderIntent(
        intent_id="intent_timeout",
        strategy_run_id="run_timeout",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)

    assert result.status is OrderStatus.RECONCILE_PENDING


def test_simulation_rejects_duplicate_fill_ids() -> None:
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import FillEvent, OrderIntent
    from quant_os.execution.state_machine import OrderStateMachine

    start = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    machine = OrderStateMachine()
    intent = OrderIntent(
        intent_id="intent_dup_fill",
        strategy_run_id="run_dup_fill",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )
    machine.plan(intent, order_id="order_dup", occurred_at=start)
    machine.transition("order_dup", OrderStatus.APPROVED, occurred_at=start + timedelta(seconds=1))
    machine.transition("order_dup", OrderStatus.SUBMITTING, occurred_at=start + timedelta(seconds=2))
    machine.transition("order_dup", OrderStatus.ACKNOWLEDGED, occurred_at=start + timedelta(seconds=3))
    machine.transition("order_dup", OrderStatus.WORKING, occurred_at=start + timedelta(seconds=4))

    fill = FillEvent(
        fill_id="fill_dup",
        order_id="order_dup",
        intent_id="intent_dup_fill",
        strategy_run_id="run_dup_fill",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("5"),
        price=Decimal("100"),
        occurred_at=start + timedelta(seconds=5),
    )
    machine.record_fill(fill)

    with pytest.raises(ValueError):
        machine.record_fill(fill)


def test_simulation_rejects_out_of_order_events() -> None:
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import FillEvent, OrderIntent
    from quant_os.execution.state_machine import OrderStateMachine

    start = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    machine = OrderStateMachine()
    intent = OrderIntent(
        intent_id="intent_ooo",
        strategy_run_id="run_ooo",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )
    machine.plan(intent, order_id="order_ooo", occurred_at=start)
    machine.transition("order_ooo", OrderStatus.APPROVED, occurred_at=start + timedelta(seconds=2))

    with pytest.raises(ValueError):
        machine.transition("order_ooo", OrderStatus.SUBMITTING, occurred_at=start + timedelta(seconds=1))

    machine.transition("order_ooo", OrderStatus.SUBMITTING, occurred_at=start + timedelta(seconds=3))
    machine.transition("order_ooo", OrderStatus.ACKNOWLEDGED, occurred_at=start + timedelta(seconds=4))
    machine.transition("order_ooo", OrderStatus.WORKING, occurred_at=start + timedelta(seconds=5))

    with pytest.raises(ValueError):
        machine.record_fill(
            FillEvent(
                fill_id="fill_ooo",
                order_id="order_ooo",
                intent_id="intent_ooo",
                strategy_run_id="run_ooo",
                symbol="AAA",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                price=Decimal("100"),
                occurred_at=start + timedelta(seconds=4),
            )
        )


def test_simulation_restart_recovery_reads_projection_and_snapshot(tmp_path) -> None:
    from quant_os.adapters.paper import PaperAdapter, PaperExecutionPolicy
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    db_path = tmp_path / "recovery.db"
    store = OperationalStore(f"sqlite:///{db_path}")
    store.create_schema()
    adapter = PaperAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        ),
        execution_policy=PaperExecutionPolicy(fill_ratio=Decimal("0.5")),
        store=store,
    )
    intent = OrderIntent(
        intent_id="intent_restart",
        strategy_run_id="run_restart",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)
    recovered_store = OperationalStore(f"sqlite:///{db_path}")
    recovered_order = recovered_store.get_order_projection(result.order_id)
    recovered_snapshot = recovered_store.latest_pnl_snapshot()

    assert recovered_order.status is OrderStatus.PARTIALLY_FILLED
    assert recovered_order.filled_quantity == Decimal("5.0000")
    assert recovered_snapshot.positions["AAA"].quantity == Decimal("5.0000")


def test_simulation_kill_switch_trigger_covers_operational_failure() -> None:
    from quant_os.domain.enums import KillSwitchReason
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    kill_switch = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
    )

    event = kill_switch.evaluate_event_write_failure(
        triggered_at=as_of,
        component="order_events",
        error_message="disk full",
    )

    assert event is not None
    assert event.reason is KillSwitchReason.EVENT_WRITE_FAILURE
    assert kill_switch.can_submit_orders() is False
