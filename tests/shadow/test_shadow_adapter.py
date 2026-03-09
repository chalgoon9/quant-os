from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


def test_shadow_adapter_simulates_execution_and_builds_report() -> None:
    from quant_os.adapters.shadow import ShadowAdapter
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType, TradingMode
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    adapter = ShadowAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        ),
        venue="krx",
        commission_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )
    intent = OrderIntent(
        intent_id="intent_shadow_1",
        strategy_run_id="run_shadow_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)
    report = adapter.build_shadow_report()

    assert result.accepted is True
    assert result.status is OrderStatus.ACKNOWLEDGED
    assert report.mode is TradingMode.SHADOW
    assert report.venue == "krx"
    assert report.simulated_order_count == 1
    assert report.simulated_fill_count == 1
    assert report.venue_rejection_count == 0
    assert len(report.lines) == 1
    assert report.lines[0].symbol == "AAA"
    assert report.lines[0].venue_check_passed is True
    assert report.lines[0].venue_check_reason is None
    assert report.lines[0].final_status is OrderStatus.FILLED
    assert report.lines[0].filled_quantity == Decimal("10.0000")


def test_shadow_adapter_rejects_orders_that_violate_venue_rules() -> None:
    from quant_os.adapters.shadow import ShadowAdapter
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    adapter = ShadowAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        ),
        venue="krx",
        lot_size=Decimal("5"),
        min_notional=Decimal("1000"),
        commission_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )
    bad_lot = OrderIntent(
        intent_id="intent_shadow_bad_lot",
        strategy_run_id="run_shadow_2",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("3"),
        order_type=OrderType.MARKET,
    )
    bad_notional = OrderIntent(
        intent_id="intent_shadow_bad_notional",
        strategy_run_id="run_shadow_2",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("5"),
        order_type=OrderType.MARKET,
    )

    bad_lot_result = adapter.submit_intent(bad_lot)
    adapter = ShadowAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        ),
        venue="krx",
        lot_size=Decimal("5"),
        min_notional=Decimal("1000"),
        commission_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )
    bad_notional_result = adapter.submit_intent(bad_notional)
    report = adapter.build_shadow_report()

    assert bad_lot_result.accepted is False
    assert bad_lot_result.status is OrderStatus.PRECHECK_REJECTED
    assert bad_notional_result.accepted is False
    assert bad_notional_result.status is OrderStatus.PRECHECK_REJECTED
    assert report.venue_rejection_count == 1
    assert report.lines[0].venue_check_passed is False
    assert report.lines[0].venue_check_reason == "order notional must be at least 1000.0000"
    assert report.lines[0].final_status is OrderStatus.PRECHECK_REJECTED


def test_shadow_adapter_can_compare_simulated_state_with_external_state() -> None:
    from quant_os.adapters.shadow import ShadowAdapter
    from quant_os.domain.enums import OrderSide, OrderType, ReconciliationStatus
    from quant_os.domain.models import ExternalStateSnapshot, FillEvent, OrderIntent, PortfolioState, Position

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    adapter = ShadowAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={"AAA": Decimal("100")},
        ),
        venue="krx",
        commission_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
    )
    adapter.submit_intent(
        OrderIntent(
            intent_id="intent_shadow_compare",
            strategy_run_id="run_shadow_compare",
            symbol="AAA",
            side=OrderSide.BUY,
            quantity=Decimal("10"),
            order_type=OrderType.MARKET,
        )
    )

    comparison = adapter.compare_with_external_state(
        external_state=ExternalStateSnapshot(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("99000"),
            positions=(
                Position(
                    symbol="AAA",
                    quantity=Decimal("10"),
                    average_cost=Decimal("100"),
                    market_price=Decimal("100"),
                ),
            ),
            fills=(
                FillEvent(
                    fill_id="ext_fill_1",
                    order_id="order_1",
                    intent_id="intent_shadow_compare",
                    strategy_run_id="run_shadow_compare",
                    symbol="AAA",
                    side=OrderSide.BUY,
                    quantity=Decimal("10"),
                    price=Decimal("100"),
                    fee=Decimal("0"),
                    tax=Decimal("0"),
                    occurred_at=as_of,
                    broker_fill_id="paper-fill-order",
                ),
            ),
        ),
        cash_tolerance=Decimal("0"),
        position_tolerance=Decimal("0"),
    )

    assert comparison.reconciliation.status is ReconciliationStatus.MISMATCH
    assert comparison.simulated_order_count == 1
    assert comparison.simulated_fill_count == 1
    assert comparison.venue_rejection_count == 0
    assert comparison.lines[0].venue_check_passed is True
    assert comparison.local_fill_count == 1
    assert comparison.external_fill_count == 1


def test_shadow_adapter_fails_closed_when_notional_check_lacks_market_price() -> None:
    from quant_os.adapters.shadow import ShadowAdapter
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    adapter = ShadowAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("100000"),
            net_asset_value=Decimal("100000"),
            positions=(),
            market_prices={},
        ),
        venue="krx",
        min_notional=Decimal("1000"),
    )

    result = adapter.submit_intent(
        OrderIntent(
            intent_id="intent_shadow_missing_price",
            strategy_run_id="run_shadow_missing_price",
            symbol="AAA",
            side=OrderSide.BUY,
            quantity=Decimal("5"),
            order_type=OrderType.MARKET,
        )
    )

    assert result.accepted is False
    assert result.status is OrderStatus.PRECHECK_REJECTED
    assert result.message == "missing market price for venue notional validation"
