from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


def test_paper_adapter_submits_and_fills_market_intent() -> None:
    from quant_os.adapters.paper import PaperAdapter
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderEvent, OrderIntent, PortfolioState

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
        commission_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )
    intent = OrderIntent(
        intent_id="intent_paper_1",
        strategy_run_id="run_paper_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)
    events = list(adapter.sync_events(None))
    order_events = [event for event in events if isinstance(event, OrderEvent)]
    fills = [event for event in events if not isinstance(event, OrderEvent)]
    portfolio = adapter.get_portfolio_state()

    assert result.accepted is True
    assert result.status is OrderStatus.ACKNOWLEDGED
    assert result.order_id is not None
    assert [event.status for event in order_events] == [
        OrderStatus.PLANNED,
        OrderStatus.APPROVED,
        OrderStatus.SUBMITTING,
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.WORKING,
        OrderStatus.FILLED,
    ]
    assert len(fills) == 1
    assert portfolio.cash_balance == Decimal("99000.0000")
    assert portfolio.positions[0].symbol == "AAA"
    assert portfolio.positions[0].quantity == Decimal("10.0000")


def test_paper_adapter_supports_partial_fill_and_persists_projection(tmp_path) -> None:
    from quant_os.adapters.paper import PaperAdapter, PaperExecutionPolicy
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderEvent, OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    store = OperationalStore(f"sqlite:///{tmp_path / 'paper_partial.db'}")
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
        commission_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        execution_policy=PaperExecutionPolicy(fill_ratio=Decimal("0.5")),
        store=store,
    )
    intent = OrderIntent(
        intent_id="intent_partial_1",
        strategy_run_id="run_partial_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)
    events = list(adapter.sync_events(None))
    order_events = [event for event in events if isinstance(event, OrderEvent)]
    portfolio = adapter.get_portfolio_state()
    stored_order = store.get_order_projection(result.order_id)

    assert result.accepted is True
    assert order_events[-1].status is OrderStatus.PARTIALLY_FILLED
    assert stored_order.status is OrderStatus.PARTIALLY_FILLED
    assert stored_order.filled_quantity == Decimal("5.0000")
    assert portfolio.cash_balance == Decimal("99500.0000")
    assert portfolio.positions[0].quantity == Decimal("5.0000")


def test_paper_adapter_marks_uncertain_submit_reconcile_pending(tmp_path) -> None:
    from quant_os.adapters.paper import PaperAdapter, PaperExecutionPolicy
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    store = OperationalStore(f"sqlite:///{tmp_path / 'paper_pending.db'}")
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
        execution_policy=PaperExecutionPolicy(uncertain_submit=True),
        store=store,
    )
    intent = OrderIntent(
        intent_id="intent_pending_1",
        strategy_run_id="run_pending_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)

    assert result.status is OrderStatus.RECONCILE_PENDING
    assert result.accepted is False
    assert store.get_order_projection(result.order_id).status is OrderStatus.RECONCILE_PENDING
    assert store.list_fills(result.order_id) == []


def test_paper_adapter_blocks_submit_when_kill_switch_is_active() -> None:
    from quant_os.adapters.paper import PaperAdapter
    from quant_os.domain.enums import KillSwitchReason, OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    kill_switch = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
    )
    kill_switch.trigger(
        reason=KillSwitchReason.RECONCILIATION_FAILURE,
        triggered_at=as_of,
        details={"summary": "mismatch"},
    )
    adapter = PaperAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        ),
        kill_switch=kill_switch,
    )
    intent = OrderIntent(
        intent_id="intent_blocked_1",
        strategy_run_id="run_blocked_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)
    events = list(adapter.sync_events(None))

    assert result.accepted is False
    assert result.status is OrderStatus.PRECHECK_REJECTED
    assert result.message == "kill switch active"
    assert [event.status for event in events if hasattr(event, "status")] == [
        OrderStatus.PLANNED,
        OrderStatus.PRECHECK_REJECTED,
    ]
