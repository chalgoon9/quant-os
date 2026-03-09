from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


def test_daily_report_summarizes_pnl_reconciliation_and_kill_switch() -> None:
    from quant_os.domain.enums import KillSwitchReason, ReconciliationStatus
    from quant_os.domain.models import DailyReport, KillSwitchEvent, LedgerSnapshot, Position, ReconciliationResult
    from quant_os.reporting.daily import DailyReportGenerator

    as_of = datetime(2026, 3, 9, 15, 30, tzinfo=timezone.utc)
    snapshot = LedgerSnapshot(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("99425"),
        positions={
            "AAA": Position(
                symbol="AAA",
                quantity=Decimal("6"),
                average_cost=Decimal("101"),
                market_price=Decimal("120"),
            )
        },
        realized_pnl=Decimal("31"),
        unrealized_pnl=Decimal("114"),
        total_pnl=Decimal("145"),
        nav=Decimal("100145"),
    )
    reconciliation = ReconciliationResult(
        reconciliation_id="recon_2",
        occurred_at=as_of,
        status=ReconciliationStatus.MISMATCH,
        mismatch_count=1,
        requires_manual_intervention=True,
        summary="position mismatch",
        issues=(),
    )
    active_event = KillSwitchEvent(
        event_id="ks_1",
        reason=KillSwitchReason.RECONCILIATION_FAILURE,
        triggered_at=as_of,
        trigger_value=Decimal("1"),
        threshold_value=Decimal("0"),
        details={"summary": "position mismatch"},
        is_active=True,
    )
    generator = DailyReportGenerator()

    report = generator.generate(
        as_of=as_of,
        snapshot=snapshot,
        reconciliation=reconciliation,
        kill_switch_events=(active_event,),
    )

    assert isinstance(report, DailyReport)
    assert report.nav == Decimal("100145.0000")
    assert report.reconciliation_status is ReconciliationStatus.MISMATCH
    assert report.active_kill_switch_reasons == (KillSwitchReason.RECONCILIATION_FAILURE,)
    assert "NAV: 100145.0000 KRW" in report.body_markdown
    assert "Reconciliation: mismatch" in report.body_markdown
    assert "Kill Switch: active" in report.body_markdown
