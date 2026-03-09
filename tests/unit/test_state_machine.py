from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest


def test_order_state_machine_projects_from_append_only_events() -> None:
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import FillEvent, OrderIntent
    from quant_os.execution.state_machine import OrderStateMachine

    start = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    intent = OrderIntent(
        intent_id="intent_1",
        strategy_run_id="run_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
        rationale="unit-test",
    )
    machine = OrderStateMachine()

    machine.plan(intent, order_id="order_1", occurred_at=start)
    machine.transition("order_1", OrderStatus.APPROVED, occurred_at=start + timedelta(seconds=1))
    machine.transition("order_1", OrderStatus.SUBMITTING, occurred_at=start + timedelta(seconds=2))
    machine.transition(
        "order_1",
        OrderStatus.ACKNOWLEDGED,
        occurred_at=start + timedelta(seconds=3),
        broker_order_id="broker_1",
    )
    machine.transition("order_1", OrderStatus.WORKING, occurred_at=start + timedelta(seconds=4))
    machine.record_fill(
        FillEvent(
            fill_id="fill_1",
            order_id="order_1",
            intent_id="intent_1",
            strategy_run_id="run_1",
            symbol="AAA",
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            occurred_at=start + timedelta(seconds=5),
        )
    )
    machine.transition("order_1", OrderStatus.FILLED, occurred_at=start + timedelta(seconds=6))

    projection = machine.get_projection("order_1")

    assert projection.status is OrderStatus.FILLED
    assert projection.filled_quantity == Decimal("10")
    assert projection.broker_order_id == "broker_1"
    assert [event.status for event in machine.order_events("order_1")] == [
        OrderStatus.PLANNED,
        OrderStatus.APPROVED,
        OrderStatus.SUBMITTING,
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.WORKING,
        OrderStatus.FILLED,
    ]


def test_order_state_machine_rejects_invalid_transition() -> None:
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent
    from quant_os.execution.state_machine import OrderStateMachine

    start = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    intent = OrderIntent(
        intent_id="intent_2",
        strategy_run_id="run_2",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.MARKET,
    )
    machine = OrderStateMachine()

    machine.plan(intent, order_id="order_2", occurred_at=start)
    machine.transition("order_2", OrderStatus.APPROVED, occurred_at=start + timedelta(seconds=1))

    with pytest.raises(ValueError):
        machine.transition("order_2", OrderStatus.FILLED, occurred_at=start + timedelta(seconds=2))
