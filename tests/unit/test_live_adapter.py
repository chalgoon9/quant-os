from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


def test_stub_live_adapter_fails_closed_and_keeps_interface() -> None:
    from quant_os.adapters.live import StubLiveAdapter
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    adapter = StubLiveAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        )
    )
    intent = OrderIntent(
        intent_id="intent_live_1",
        strategy_run_id="run_live_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)
    events = list(adapter.sync_events(None))
    portfolio = adapter.get_portfolio_state()

    assert result.accepted is False
    assert result.status is OrderStatus.PRECHECK_REJECTED
    assert result.message == "live adapter not configured"
    assert [event.status for event in events] == [
        OrderStatus.PLANNED,
        OrderStatus.PRECHECK_REJECTED,
    ]
    assert portfolio.cash_balance == Decimal("100000")
    assert portfolio.positions == ()
