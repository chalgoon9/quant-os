from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


def test_reconciler_reports_position_and_cash_mismatches() -> None:
    from quant_os.domain.enums import ReconciliationStatus
    from quant_os.domain.models import ExternalStateSnapshot, FillEvent, PortfolioState, Position
    from quant_os.reconciliation.service import PortfolioReconciler

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    local = PortfolioState(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000"),
        net_asset_value=Decimal("101200"),
        positions=(
            Position(symbol="AAA", quantity=Decimal("10"), average_cost=Decimal("100"), market_price=Decimal("120")),
        ),
        market_prices={"AAA": Decimal("120")},
    )
    external = ExternalStateSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("99950"),
        positions=(
            Position(symbol="AAA", quantity=Decimal("9"), average_cost=Decimal("100"), market_price=Decimal("120")),
        ),
        fills=(
            FillEvent(
                fill_id="ext_fill_1",
                order_id="order_1",
                intent_id="intent_1",
                strategy_run_id="run_1",
                symbol="AAA",
                side="buy",
                quantity=Decimal("1"),
                price=Decimal("120"),
                fee=Decimal("0"),
                tax=Decimal("0"),
                occurred_at=as_of,
                broker_fill_id="broker-fill-1",
            ),
        ),
    )
    reconciler = PortfolioReconciler(
        cash_tolerance=Decimal("1"),
        position_tolerance=Decimal("0.0001"),
    )

    result = reconciler.reconcile(local_portfolio=local, external_state=external, local_fills=())

    assert result.status is ReconciliationStatus.MISMATCH
    assert result.mismatch_count == 3
    assert result.requires_manual_intervention is True
    assert {issue.code for issue in result.issues} == {
        "cash_balance_mismatch",
        "position_quantity_mismatch",
        "unknown_external_fill",
    }
    assert {issue.severity for issue in result.issues} >= {"error", "critical"}


def test_reconciler_reports_match_within_tolerance() -> None:
    from quant_os.domain.enums import ReconciliationStatus
    from quant_os.domain.models import ExternalStateSnapshot, PortfolioState, Position
    from quant_os.reconciliation.service import PortfolioReconciler

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    local = PortfolioState(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000"),
        net_asset_value=Decimal("101200"),
        positions=(
            Position(symbol="AAA", quantity=Decimal("10"), average_cost=Decimal("100"), market_price=Decimal("120")),
        ),
        market_prices={"AAA": Decimal("120")},
    )
    external = ExternalStateSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000.5"),
        positions=(
            Position(symbol="AAA", quantity=Decimal("10.0000"), average_cost=Decimal("100"), market_price=Decimal("120")),
        ),
    )
    reconciler = PortfolioReconciler(
        cash_tolerance=Decimal("1"),
        position_tolerance=Decimal("0.001"),
    )

    result = reconciler.reconcile(local_portfolio=local, external_state=external)

    assert result.status is ReconciliationStatus.MATCHED
    assert result.mismatch_count == 0
    assert result.requires_manual_intervention is False


def test_reconciler_reports_missing_external_fill() -> None:
    from quant_os.domain.enums import OrderSide, ReconciliationStatus
    from quant_os.domain.models import ExternalStateSnapshot, FillEvent, PortfolioState
    from quant_os.reconciliation.service import PortfolioReconciler

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    local = PortfolioState(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000"),
        net_asset_value=Decimal("100000"),
        positions=(),
        market_prices={},
    )
    external = ExternalStateSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000"),
        positions=(),
        fills=(),
    )
    local_fill = FillEvent(
        fill_id="fill_local_1",
        order_id="order_1",
        intent_id="intent_1",
        strategy_run_id="run_1",
        symbol="AAA",
        side=OrderSide.BUY,
        quantity=Decimal("1"),
        price=Decimal("120"),
        fee=Decimal("0"),
        tax=Decimal("0"),
        occurred_at=as_of,
        broker_fill_id="broker-fill-1",
    )
    reconciler = PortfolioReconciler(
        cash_tolerance=Decimal("1"),
        position_tolerance=Decimal("0.001"),
    )

    result = reconciler.reconcile(local_portfolio=local, external_state=external, local_fills=(local_fill,))

    assert result.status is ReconciliationStatus.MISMATCH
    assert {issue.code for issue in result.issues} == {"missing_external_fill"}


def test_reconciler_and_kill_switch_can_persist_operational_logs(tmp_path) -> None:
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import KillSwitchReason, ReconciliationStatus
    from quant_os.domain.models import ExternalStateSnapshot, PortfolioState
    from quant_os.reconciliation.service import PortfolioReconciler
    from quant_os.risk.kill_switch import KillSwitch

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    store = OperationalStore(f"sqlite:///{tmp_path / 'recon_store.db'}")
    store.create_schema()
    local = PortfolioState(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000"),
        net_asset_value=Decimal("100000"),
        positions=(),
        market_prices={},
    )
    external = ExternalStateSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("99900"),
        positions=(),
    )
    reconciler = PortfolioReconciler(
        cash_tolerance=Decimal("1"),
        position_tolerance=Decimal("0.001"),
        store=store,
    )
    kill_switch = KillSwitch(
        daily_loss_limit=Decimal("0.03"),
        stale_market_data_seconds=3600,
        store=store,
    )

    result = reconciler.reconcile(local_portfolio=local, external_state=external)
    event = kill_switch.evaluate_reconciliation(result)

    assert result.status is ReconciliationStatus.MISMATCH
    assert store.latest_reconciliation_result().summary == result.summary
    assert event is not None
    assert store.active_kill_switch_events()[0].reason is KillSwitchReason.RECONCILIATION_FAILURE


def test_reconciler_uses_broker_order_identity_for_open_orders() -> None:
    from quant_os.domain.enums import OrderSide, OrderType, ReconciliationStatus, TimeInForce, OrderStatus
    from quant_os.domain.models import ExternalStateSnapshot, OrderProjection, PortfolioState
    from quant_os.reconciliation.service import PortfolioReconciler

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    local = PortfolioState(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000"),
        net_asset_value=Decimal("100000"),
        positions=(),
        market_prices={},
    )
    local_order = OrderProjection(
        order_id="order_local_1",
        intent_id="intent_local_1",
        strategy_run_id="run_1",
        symbol="AAA",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        quantity=Decimal("1"),
        status=OrderStatus.WORKING,
        created_at=as_of,
        updated_at=as_of,
        filled_quantity=Decimal("0"),
        broker_order_id="broker-local-1",
    )
    external = ExternalStateSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("100000"),
        positions=(),
        open_orders=(
            local_order.model_copy(update={"broker_order_id": "broker-external-1"}),
        ),
    )
    reconciler = PortfolioReconciler(
        cash_tolerance=Decimal("1"),
        position_tolerance=Decimal("0.001"),
    )

    result = reconciler.reconcile(
        local_portfolio=local,
        external_state=external,
        local_open_orders=(local_order,),
    )

    assert result.status is ReconciliationStatus.MISMATCH
    assert {issue.code for issue in result.issues} == {"open_order_mismatch"}
