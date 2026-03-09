from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def test_ledger_projector_tracks_cash_positions_and_pnl() -> None:
    from quant_os.domain.enums import OrderEventType, OrderSide, OrderStatus
    from quant_os.domain.models import FillEvent, OrderEvent
    from quant_os.ledger.projector import LedgerProjector

    start = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    projector = LedgerProjector(base_currency="KRW", initial_cash=Decimal("100000"))

    projector.apply_order_event(
        OrderEvent(
            event_id="event_1",
            order_id="order_1",
            intent_id="intent_1",
            strategy_run_id="run_1",
            symbol="AAA",
            status=OrderStatus.FILLED,
            event_type=OrderEventType.STATE_TRANSITION,
            occurred_at=start,
        )
    )
    projector.apply_fill_event(
        FillEvent(
            fill_id="fill_buy",
            order_id="order_1",
            intent_id="intent_1",
            strategy_run_id="run_1",
            symbol="AAA",
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            price=Decimal("100"),
            fee=Decimal("10"),
            tax=Decimal("0"),
            occurred_at=start + timedelta(seconds=1),
        )
    )
    projector.apply_fill_event(
        FillEvent(
            fill_id="fill_sell",
            order_id="order_2",
            intent_id="intent_2",
            strategy_run_id="run_1",
            symbol="AAA",
            side=OrderSide.SELL,
            quantity=Decimal("4"),
            price=Decimal("110"),
            fee=Decimal("5"),
            tax=Decimal("0"),
            occurred_at=start + timedelta(seconds=2),
        )
    )

    snapshot = projector.snapshot(start + timedelta(days=1), {"AAA": Decimal("120")})

    assert projector.cash_ledger_entries()[0].amount == Decimal("-1010.0000")
    assert projector.cash_ledger_entries()[1].amount == Decimal("435.0000")
    assert snapshot.cash_balance == Decimal("99425.0000")
    assert snapshot.positions["AAA"].quantity == Decimal("6.0000")
    assert snapshot.realized_pnl == Decimal("31.0000")
    assert snapshot.unrealized_pnl == Decimal("114.0000")
    assert snapshot.total_pnl == Decimal("145.0000")
    assert snapshot.nav == Decimal("100145.0000")
