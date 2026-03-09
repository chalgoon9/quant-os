from __future__ import annotations

from datetime import datetime

from quant_os.domain.models import DailyReport, KillSwitchEvent, LedgerSnapshot, ReconciliationResult
from quant_os.domain.types import quantize


class DailyReportGenerator:
    def generate(
        self,
        *,
        as_of: datetime,
        snapshot: LedgerSnapshot,
        reconciliation: ReconciliationResult,
        kill_switch_events: tuple[KillSwitchEvent, ...] = (),
    ) -> DailyReport:
        active_events = tuple(event.reason for event in kill_switch_events if event.is_active)
        return DailyReport(
            as_of=as_of,
            base_currency=snapshot.base_currency,
            nav=quantize(snapshot.nav, "0.0000"),
            cash_balance=quantize(snapshot.cash_balance, "0.0000"),
            realized_pnl=quantize(snapshot.realized_pnl, "0.0000"),
            unrealized_pnl=quantize(snapshot.unrealized_pnl, "0.0000"),
            total_pnl=quantize(snapshot.total_pnl, "0.0000"),
            reconciliation_status=reconciliation.status,
            active_kill_switch_reasons=active_events,
            body_markdown=self._render_markdown(
                as_of=as_of,
                snapshot=snapshot,
                reconciliation=reconciliation,
                active_events=active_events,
            ),
        )

    def _render_markdown(
        self,
        *,
        as_of: datetime,
        snapshot: LedgerSnapshot,
        reconciliation: ReconciliationResult,
        active_events: tuple,
    ) -> str:
        positions = ", ".join(
            f"{position.symbol}:{quantize(position.quantity, '0.0000')}@{quantize(position.market_price or position.average_cost, '0.0000')}"
            for position in snapshot.positions.values()
        ) or "none"
        kill_switch_state = "active" if active_events else "clear"
        active_list = ", ".join(reason.value for reason in active_events) or "none"
        return "\n".join(
            [
                f"# Daily Report {as_of.date().isoformat()}",
                "",
                f"- NAV: {quantize(snapshot.nav, '0.0000')} {snapshot.base_currency}",
                f"- Cash: {quantize(snapshot.cash_balance, '0.0000')} {snapshot.base_currency}",
                f"- Realized PnL: {quantize(snapshot.realized_pnl, '0.0000')}",
                f"- Unrealized PnL: {quantize(snapshot.unrealized_pnl, '0.0000')}",
                f"- Total PnL: {quantize(snapshot.total_pnl, '0.0000')}",
                f"- Positions: {positions}",
                f"- Reconciliation: {reconciliation.status.value}",
                f"- Reconciliation Summary: {reconciliation.summary}",
                f"- Kill Switch: {kill_switch_state}",
                f"- Active Kill Switch Reasons: {active_list}",
            ]
        )
