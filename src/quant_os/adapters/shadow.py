from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from quant_os.adapters.paper import PaperAdapter, PaperExecutionPolicy
from quant_os.db.store import OperationalStore
from quant_os.domain.enums import OrderStatus, TradingMode
from quant_os.domain.ids import new_id
from quant_os.domain.models import ExternalStateSnapshot, FillEvent, OrderEvent, OrderIntent, PortfolioState, ReconciliationResult, SubmitResult
from quant_os.domain.types import ZERO, quantize
from quant_os.execution.state_machine import OrderStateMachine
from quant_os.reconciliation.service import PortfolioReconciler
from quant_os.risk.kill_switch import KillSwitch


@dataclass(frozen=True)
class ShadowReportLine:
    intent_id: str
    order_id: str
    symbol: str
    venue_check_passed: bool
    venue_check_reason: str | None
    final_status: OrderStatus
    filled_quantity: Decimal


@dataclass(frozen=True)
class ShadowRunReport:
    mode: TradingMode
    venue: str
    simulated_order_count: int
    simulated_fill_count: int
    venue_rejection_count: int
    lines: tuple[ShadowReportLine, ...]


@dataclass(frozen=True)
class ShadowComparisonReport:
    mode: TradingMode
    venue: str
    simulated_order_count: int
    simulated_fill_count: int
    venue_rejection_count: int
    lines: tuple[ShadowReportLine, ...]
    reconciliation: ReconciliationResult
    local_fill_count: int
    external_fill_count: int


class ShadowAdapter:
    def __init__(
        self,
        initial_portfolio: PortfolioState,
        *,
        venue: str,
        commission_bps: Decimal = ZERO,
        slippage_bps: Decimal = ZERO,
        execution_policy: PaperExecutionPolicy | None = None,
        lot_size: Decimal = Decimal("1"),
        min_notional: Decimal = ZERO,
        store: OperationalStore | None = None,
        kill_switch: KillSwitch | None = None,
    ) -> None:
        self._venue = venue
        self._store = store
        self._lot_size = quantize(lot_size, "0.0000")
        self._min_notional = quantize(min_notional, "0.0000")
        self._paper = PaperAdapter(
            initial_portfolio,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            execution_policy=execution_policy,
            store=store,
            adapter_name="shadow",
            kill_switch=kill_switch,
        )
        self._rejections = OrderStateMachine()
        self._rejection_events: list[OrderEvent] = []
        self._report_lines: list[ShadowReportLine] = []

    def submit_intent(self, intent: OrderIntent) -> SubmitResult:
        rejection_reason = self._validate_venue_rules(intent)
        if rejection_reason is not None:
            order_id = new_id("order")
            planned_event = self._rejections.plan(intent, order_id=order_id, occurred_at=self._paper._tick())
            self._record_rejection_event(planned_event)
            rejected_event = self._rejections.transition(
                order_id,
                OrderStatus.PRECHECK_REJECTED,
                occurred_at=self._paper._tick(),
                reason=rejection_reason,
            )
            self._record_rejection_event(rejected_event)
            self._report_lines.append(
                self._build_line(
                    intent.intent_id,
                    order_id,
                    venue_check_passed=False,
                    venue_check_reason=rejection_reason,
                )
            )
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.PRECHECK_REJECTED,
                message=rejection_reason,
            )
        result = self._paper.submit_intent(intent)
        if result.order_id is not None:
            self._report_lines.append(
                self._build_line(
                    intent.intent_id,
                    result.order_id,
                    venue_check_passed=True,
                    venue_check_reason=None,
                )
            )
        return result

    def cancel_order(self, order_id: str) -> None:
        self._paper.cancel_order(order_id)

    def sync_events(self, since: datetime | None) -> Iterable[OrderEvent | FillEvent]:
        events = tuple(self._rejection_events) + tuple(self._paper.sync_events(None))
        ordered = tuple(sorted(events, key=lambda event: event.occurred_at))
        if since is None:
            return ordered
        return tuple(event for event in ordered if event.occurred_at > since)

    def get_portfolio_state(self) -> PortfolioState:
        return self._paper.get_portfolio_state()

    def build_shadow_report(self) -> ShadowRunReport:
        simulated_fill_count = sum(1 for event in self.sync_events(None) if isinstance(event, FillEvent))
        return ShadowRunReport(
            mode=TradingMode.SHADOW,
            venue=self._venue,
            simulated_order_count=len(self._report_lines),
            simulated_fill_count=simulated_fill_count,
            venue_rejection_count=sum(1 for line in self._report_lines if not line.venue_check_passed),
            lines=tuple(self._report_lines),
        )

    def compare_with_external_state(
        self,
        *,
        external_state: ExternalStateSnapshot,
        cash_tolerance: Decimal,
        position_tolerance: Decimal,
    ) -> ShadowComparisonReport:
        reconciler = PortfolioReconciler(
            cash_tolerance=cash_tolerance,
            position_tolerance=position_tolerance,
        )
        local_fills = tuple(event for event in self.sync_events(None) if isinstance(event, FillEvent))
        local_open_orders = tuple(
            projection
            for projection in self._paper.list_order_projections()
            if projection.status
            not in {
                OrderStatus.FILLED,
                OrderStatus.CANCELLED,
                OrderStatus.CANCELLED_PARTIAL,
                OrderStatus.EXPIRED,
                OrderStatus.BROKER_REJECTED,
                OrderStatus.PRECHECK_REJECTED,
                OrderStatus.BUSTED,
            }
        )
        reconciliation = reconciler.reconcile(
            local_portfolio=self.get_portfolio_state(),
            external_state=external_state,
            local_open_orders=local_open_orders,
            local_fills=local_fills,
        )
        return ShadowComparisonReport(
            mode=TradingMode.SHADOW,
            venue=self._venue,
            simulated_order_count=len(self._report_lines),
            simulated_fill_count=len(local_fills),
            venue_rejection_count=sum(1 for line in self._report_lines if not line.venue_check_passed),
            lines=tuple(self._report_lines),
            reconciliation=reconciliation,
            local_fill_count=len(local_fills),
            external_fill_count=len(external_state.fills),
        )

    def _build_line(
        self,
        intent_id: str,
        order_id: str,
        *,
        venue_check_passed: bool,
        venue_check_reason: str | None,
    ) -> ShadowReportLine:
        final_status = OrderStatus.PLANNED
        filled_quantity = ZERO
        symbol = ""
        for event in self.sync_events(None):
            if isinstance(event, OrderEvent) and event.order_id == order_id:
                symbol = event.symbol
                final_status = event.status
            elif isinstance(event, FillEvent) and event.order_id == order_id:
                filled_quantity = quantize(filled_quantity + event.quantity, "0.0000")
        return ShadowReportLine(
            intent_id=intent_id,
            order_id=order_id,
            symbol=symbol,
            venue_check_passed=venue_check_passed,
            venue_check_reason=venue_check_reason,
            final_status=final_status,
            filled_quantity=filled_quantity,
        )

    def _record_rejection_event(self, event: OrderEvent) -> None:
        self._rejection_events.append(event)
        if self._store is None:
            return
        self._store.append_order_event(event)
        self._store.upsert_order_projection(
            self._rejections.get_projection(event.order_id),
            projection_source_event_id=event.event_id,
        )

    def _validate_venue_rules(self, intent: OrderIntent) -> str | None:
        if self._lot_size > ZERO and quantize(intent.quantity % self._lot_size, "0.0000") != ZERO:
            return f"quantity must align with lot size {self._lot_size}"

        price = self.get_portfolio_state().market_prices.get(intent.symbol)
        if price is None:
            if self._min_notional > ZERO:
                return "missing market price for venue notional validation"
            return None
        notional = quantize(intent.quantity * price, "0.0000")
        if self._min_notional > ZERO and notional < self._min_notional:
            return f"order notional must be at least {self._min_notional}"
        return None
