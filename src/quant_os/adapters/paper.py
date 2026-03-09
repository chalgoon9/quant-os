from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterable

from quant_os.db.store import OperationalStore
from quant_os.domain.enums import OrderSide, OrderStatus
from quant_os.domain.ids import new_id
from quant_os.domain.models import FillEvent, OrderEvent, OrderIntent, PortfolioState, SubmitResult
from quant_os.domain.types import ZERO, quantize
from quant_os.execution.state_machine import OrderStateMachine
from quant_os.ledger.projector import LedgerProjector


@dataclass(frozen=True)
class PaperExecutionPolicy:
    fill_ratio: Decimal = Decimal("1")
    uncertain_submit: bool = False

    def __post_init__(self) -> None:
        normalized_ratio = quantize(self.fill_ratio, "0.0000")
        if normalized_ratio <= ZERO or normalized_ratio > Decimal("1"):
            raise ValueError("fill_ratio must be within (0, 1]")
        object.__setattr__(self, "fill_ratio", normalized_ratio)


class PaperAdapter:
    def __init__(
        self,
        initial_portfolio: PortfolioState,
        *,
        commission_bps: Decimal = ZERO,
        slippage_bps: Decimal = ZERO,
        execution_policy: PaperExecutionPolicy | None = None,
        store: OperationalStore | None = None,
        adapter_name: str = "paper",
    ) -> None:
        self._clock = initial_portfolio.as_of
        self._commission_bps = quantize(commission_bps, "0.0000")
        self._slippage_bps = quantize(slippage_bps, "0.0000")
        self._execution_policy = execution_policy or PaperExecutionPolicy()
        self._store = store
        self._adapter_name = adapter_name
        self._market_prices = dict(initial_portfolio.market_prices)
        self._state_machine = OrderStateMachine()
        self._ledger = LedgerProjector(
            base_currency=initial_portfolio.base_currency,
            initial_cash=initial_portfolio.cash_balance,
            initial_positions=initial_portfolio.positions,
        )
        self._event_log: list[OrderEvent | FillEvent] = []
        self._intent_to_order: dict[str, str] = {}

    def submit_intent(self, intent: OrderIntent) -> SubmitResult:
        order_id = self._intent_to_order.get(intent.intent_id)
        if order_id is not None:
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.PRECHECK_REJECTED,
                message="duplicate intent_id rejected",
            )

        order_id = new_id("order")
        self._intent_to_order[intent.intent_id] = order_id

        planned_event = self._state_machine.plan(intent, order_id=order_id, occurred_at=self._tick())
        self._record_order_event(planned_event)

        price = self._market_prices.get(intent.symbol)
        if price is None or price <= ZERO:
            rejected = self._state_machine.transition(
                order_id,
                OrderStatus.PRECHECK_REJECTED,
                occurred_at=self._tick(),
                reason="missing market price",
            )
            self._record_order_event(rejected)
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.PRECHECK_REJECTED,
                message="missing market price",
            )

        fill_price = _apply_slippage(price, intent.side, self._slippage_bps)
        commission = quantize((intent.quantity * fill_price) * self._commission_bps / Decimal("10000"), "0.0000")
        snapshot = self.get_portfolio_state()
        if intent.side is OrderSide.BUY and snapshot.cash_balance < quantize((intent.quantity * fill_price) + commission, "0.0000"):
            rejected = self._state_machine.transition(
                order_id,
                OrderStatus.PRECHECK_REJECTED,
                occurred_at=self._tick(),
                reason="insufficient cash",
            )
            self._record_order_event(rejected)
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.PRECHECK_REJECTED,
                message="insufficient cash",
            )

        for status in (
            OrderStatus.APPROVED,
            OrderStatus.SUBMITTING,
        ):
            event = self._state_machine.transition(
                order_id,
                status,
                occurred_at=self._tick(),
            )
            self._record_order_event(event)

        if self._execution_policy.uncertain_submit:
            pending_event = self._state_machine.transition(
                order_id,
                OrderStatus.RECONCILE_PENDING,
                occurred_at=self._tick(),
                reason="paper adapter submit outcome uncertain",
            )
            self._record_order_event(pending_event)
            return SubmitResult(
                accepted=False,
                order_id=order_id,
                status=OrderStatus.RECONCILE_PENDING,
                message="submit outcome uncertain",
            )

        for status in (
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.WORKING,
        ):
            event = self._state_machine.transition(
                order_id,
                status,
                occurred_at=self._tick(),
                broker_order_id=f"{self._adapter_name}-{order_id}" if status is OrderStatus.ACKNOWLEDGED else None,
            )
            self._record_order_event(event)

        fill_quantity = quantize(intent.quantity * self._execution_policy.fill_ratio, "0.0000")
        fill = FillEvent(
            fill_id=new_id("fill"),
            order_id=order_id,
            intent_id=intent.intent_id,
            strategy_run_id=intent.strategy_run_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=fill_quantity,
            price=fill_price,
            fee=commission,
            tax=ZERO,
            occurred_at=self._tick(),
            broker_fill_id=f"{self._adapter_name}-fill-{order_id}",
            raw_payload={"adapter": self._adapter_name},
        )
        self._record_fill(fill)

        terminal_status = OrderStatus.FILLED if fill_quantity == quantize(intent.quantity, "0.0000") else OrderStatus.PARTIALLY_FILLED
        terminal_event = self._state_machine.transition(order_id, terminal_status, occurred_at=self._tick())
        self._record_order_event(terminal_event)
        return SubmitResult(accepted=True, order_id=order_id, status=OrderStatus.ACKNOWLEDGED, message=None)

    def cancel_order(self, order_id: str) -> None:
        projection = self._state_machine.get_projection(order_id)
        if projection.status in {
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.CANCELLED_PARTIAL,
            OrderStatus.EXPIRED,
            OrderStatus.BROKER_REJECTED,
            OrderStatus.PRECHECK_REJECTED,
            OrderStatus.BUSTED,
        }:
            return
        requested = self._state_machine.transition(order_id, OrderStatus.CANCEL_REQUESTED, occurred_at=self._tick())
        self._record_order_event(requested)
        terminal = OrderStatus.CANCELLED_PARTIAL if projection.filled_quantity > ZERO else OrderStatus.CANCELLED
        cancelled = self._state_machine.transition(order_id, terminal, occurred_at=self._tick())
        self._record_order_event(cancelled)

    def sync_events(self, since: datetime | None) -> Iterable[OrderEvent | FillEvent]:
        if since is None:
            return tuple(self._event_log)
        return tuple(event for event in self._event_log if event.occurred_at > since)

    def get_portfolio_state(self) -> PortfolioState:
        return self._ledger.portfolio_state(self._clock, self._market_prices)

    def _record_order_event(self, event: OrderEvent) -> None:
        self._ledger.apply_order_event(event)
        self._event_log.append(event)
        if self._store is None:
            return
        self._store.append_order_event(event)
        self._store.upsert_order_projection(
            self._state_machine.get_projection(event.order_id),
            projection_source_event_id=event.event_id,
        )

    def _record_fill(self, fill: FillEvent) -> None:
        self._state_machine.record_fill(fill)
        self._ledger.apply_fill_event(fill)
        self._market_prices[fill.symbol] = fill.price
        self._event_log.append(fill)
        if self._store is None:
            return
        self._store.append_fill(fill)
        cash_entries = self._ledger.cash_ledger_entries()
        if cash_entries:
            self._store.append_cash_ledger_entry(cash_entries[-1])
        self._store.append_ledger_snapshot(self._ledger.snapshot(fill.occurred_at, self._market_prices), source="paper")

    def _tick(self) -> datetime:
        self._clock = self._clock + timedelta(milliseconds=1)
        return self._clock


def _apply_slippage(price: Decimal, side: OrderSide, slippage_bps: Decimal) -> Decimal:
    multiplier = Decimal("1") + (slippage_bps / Decimal("10000"))
    if side is OrderSide.SELL:
        multiplier = Decimal("1") - (slippage_bps / Decimal("10000"))
    return quantize(price * multiplier, "0.0000")
