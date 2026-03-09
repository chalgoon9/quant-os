from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from quant_os.db.store import OperationalStore
from quant_os.domain.enums import OrderStatus
from quant_os.domain.ids import new_id
from quant_os.domain.models import FillEvent, OrderEvent, OrderIntent, PortfolioState, SubmitResult
from quant_os.execution.state_machine import OrderStateMachine


class LiveAdapterBase:
    def __init__(
        self,
        initial_portfolio: PortfolioState,
        *,
        store: OperationalStore | None = None,
    ) -> None:
        self._clock = initial_portfolio.as_of
        self._portfolio = initial_portfolio
        self._store = store
        self._state_machine = OrderStateMachine()
        self._event_log: list[OrderEvent | FillEvent] = []
        self._intent_to_order: dict[str, str] = {}

    def cancel_order(self, order_id: str) -> None:
        if order_id not in {event.order_id for event in self._event_log if isinstance(event, OrderEvent)}:
            return

    def sync_events(self, since: datetime | None) -> Iterable[OrderEvent | FillEvent]:
        if since is None:
            return tuple(self._event_log)
        return tuple(event for event in self._event_log if event.occurred_at > since)

    def get_portfolio_state(self) -> PortfolioState:
        return self._portfolio

    def _record_order_event(self, event: OrderEvent) -> None:
        self._event_log.append(event)
        if self._store is None:
            return
        self._store.append_order_event(event)
        self._store.upsert_order_projection(
            self._state_machine.get_projection(event.order_id),
            projection_source_event_id=event.event_id,
        )

    def _tick(self) -> datetime:
        self._clock = self._clock + timedelta(milliseconds=1)
        return self._clock


class StubLiveAdapter(LiveAdapterBase):
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
        rejected_event = self._state_machine.transition(
            order_id,
            OrderStatus.PRECHECK_REJECTED,
            occurred_at=self._tick(),
            reason="live adapter not configured",
        )
        self._record_order_event(rejected_event)
        return SubmitResult(
            accepted=False,
            order_id=order_id,
            status=OrderStatus.PRECHECK_REJECTED,
            message="live adapter not configured",
        )
