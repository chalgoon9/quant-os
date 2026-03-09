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


def test_upbit_live_adapter_submits_and_syncs_external_events() -> None:
    from quant_os.adapters.upbit_live import UpbitExchangeClient, UpbitLiveAdapter
    from quant_os.domain.enums import OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    order_uuid = "11111111-1111-1111-1111-111111111111"

    def fake_transport(method: str, url: str, headers: dict[str, str], body: bytes | None):
        if url.endswith("/v1/ticker?markets=KRW-BTC"):
            assert "Authorization" not in headers
            return [{"trade_price": "150000000"}]
        assert headers["Authorization"].startswith("Bearer ")
        if url.endswith("/v1/orders"):
            assert method == "POST"
            payload = {} if body is None else __import__("json").loads(body.decode("utf-8"))
            assert payload["market"] == "KRW-BTC"
            return {
                "uuid": order_uuid,
                "identifier": payload["identifier"],
                "market": "KRW-BTC",
                "state": "wait",
                "side": "bid",
                "created_at": "2026-03-09T09:00:00+00:00",
                "remaining_volume": "1.0000",
                "executed_volume": "0",
                "paid_fee": "0",
                "avg_price": "0",
            }
        if "/v1/orders/uuids" in url:
            return [
                {
                    "uuid": order_uuid,
                    "identifier": "ignored",
                    "market": "KRW-BTC",
                    "state": "done",
                    "side": "bid",
                    "created_at": "2026-03-09T09:00:00+00:00",
                    "remaining_volume": "0",
                    "executed_volume": "1.0000",
                    "paid_fee": "1000",
                    "avg_price": "150000000",
                    "updated_at": "2026-03-09T09:00:01+00:00",
                }
            ]
        if url.endswith("/v1/accounts"):
            return [
                {
                    "currency": "KRW",
                    "balance": "500000",
                    "locked": "0",
                    "avg_buy_price": "0",
                    "unit_currency": "KRW",
                },
                {
                    "currency": "BTC",
                    "balance": "1.0000",
                    "locked": "0",
                    "avg_buy_price": "150000000",
                    "unit_currency": "KRW",
                },
            ]
        raise AssertionError(f"unexpected request: {method} {url}")

    client = UpbitExchangeClient(
        access_key="test-access",
        secret_key="test-secret",
        transport=fake_transport,
    )
    adapter = UpbitLiveAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("650000"),
            net_asset_value=Decimal("650000"),
            positions=(),
            market_prices={},
        ),
        client=client,
    )
    intent = OrderIntent(
        intent_id="intent_upbit_live_1",
        strategy_run_id="run_upbit_live_1",
        symbol="KRW-BTC",
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.MARKET,
    )

    submit_result = adapter.submit_intent(intent)
    synced = list(adapter.sync_events(None))
    portfolio = adapter.get_portfolio_state()

    assert submit_result.accepted is True
    assert submit_result.status in {OrderStatus.WORKING, OrderStatus.ACKNOWLEDGED}
    assert any(getattr(event, "broker_order_id", None) == order_uuid for event in synced)
    assert any(getattr(event, "status", None) is OrderStatus.FILLED for event in synced if hasattr(event, "status"))
    assert any(getattr(event, "broker_fill_id", "").startswith(f"{order_uuid}:") for event in synced if hasattr(event, "broker_fill_id"))
    assert portfolio.cash_balance == Decimal("500000.0000")
    assert portfolio.positions[0].symbol == "KRW-BTC"


def test_upbit_live_adapter_fails_closed_when_portfolio_refresh_fails() -> None:
    from quant_os.adapters.upbit_live import UpbitExchangeClient, UpbitLiveAdapter
    from quant_os.domain.enums import KillSwitchReason, OrderSide, OrderStatus, OrderType
    from quant_os.domain.models import OrderIntent, PortfolioState
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 9, 0, tzinfo=timezone.utc)
    order_uuid = "22222222-2222-2222-2222-222222222222"

    def fake_transport(method: str, url: str, headers: dict[str, str], body: bytes | None):
        if url.endswith("/v1/ticker?markets=KRW-BTC"):
            return [{"trade_price": "150000000"}]
        if url.endswith("/v1/orders"):
            return {
                "uuid": order_uuid,
                "identifier": "ignored",
                "market": "KRW-BTC",
                "state": "wait",
                "side": "bid",
                "created_at": "2026-03-09T09:00:00+00:00",
                "remaining_volume": "1.0000",
                "executed_volume": "0",
                "paid_fee": "0",
                "avg_price": "0",
            }
        if url.endswith("/v1/accounts"):
            raise RuntimeError("accounts endpoint unavailable")
        raise AssertionError(f"unexpected request: {method} {url}")

    kill_switch = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
    )
    adapter = UpbitLiveAdapter(
        PortfolioState(
            as_of=as_of,
            base_currency="KRW",
            cash_balance=Decimal("650000"),
            net_asset_value=Decimal("650000"),
            positions=(),
            market_prices={},
        ),
        client=UpbitExchangeClient(
            access_key="test-access",
            secret_key="test-secret",
            transport=fake_transport,
        ),
        kill_switch=kill_switch,
    )
    intent = OrderIntent(
        intent_id="intent_upbit_live_failclosed",
        strategy_run_id="run_upbit_live_failclosed",
        symbol="KRW-BTC",
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        order_type=OrderType.MARKET,
    )

    result = adapter.submit_intent(intent)

    assert result.accepted is False
    assert result.status is OrderStatus.RECONCILE_PENDING
    assert kill_switch.can_submit_orders() is False
    assert kill_switch.active_events()[0].reason is KillSwitchReason.EVENT_WRITE_FAILURE
