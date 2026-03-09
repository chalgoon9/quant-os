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
