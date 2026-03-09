from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from quant_os.domain.enums import OrderEventType, OrderStatus
from quant_os.domain.ids import new_id
from quant_os.domain.models import FillEvent, OrderEvent, OrderIntent, OrderProjection
from quant_os.domain.types import ZERO, quantize


ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLANNED: {OrderStatus.PRECHECK_REJECTED, OrderStatus.APPROVED},
    OrderStatus.PRECHECK_REJECTED: set(),
    OrderStatus.APPROVED: {OrderStatus.SUBMITTING},
    OrderStatus.SUBMITTING: {
        OrderStatus.ACKNOWLEDGED,
        OrderStatus.BROKER_REJECTED,
        OrderStatus.RECONCILE_PENDING,
    },
    OrderStatus.ACKNOWLEDGED: {
        OrderStatus.WORKING,
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_REQUESTED,
        OrderStatus.RECONCILE_PENDING,
    },
    OrderStatus.WORKING: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCEL_REQUESTED,
        OrderStatus.EXPIRED,
        OrderStatus.BROKER_REJECTED,
        OrderStatus.RECONCILE_PENDING,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.FILLED,
        OrderStatus.CANCEL_REQUESTED,
        OrderStatus.CANCELLED_PARTIAL,
        OrderStatus.EXPIRED,
        OrderStatus.RECONCILE_PENDING,
    },
    OrderStatus.FILLED: set(),
    OrderStatus.CANCEL_REQUESTED: {
        OrderStatus.CANCELLED,
        OrderStatus.CANCELLED_PARTIAL,
        OrderStatus.RECONCILE_PENDING,
    },
    OrderStatus.CANCELLED: set(),
    OrderStatus.CANCELLED_PARTIAL: set(),
    OrderStatus.EXPIRED: set(),
    OrderStatus.BROKER_REJECTED: set(),
    OrderStatus.RECONCILE_PENDING: {OrderStatus.MANUAL_INTERVENTION, OrderStatus.BUSTED},
    OrderStatus.MANUAL_INTERVENTION: {OrderStatus.BUSTED},
    OrderStatus.BUSTED: set(),
}


class OrderStateMachine:
    def __init__(self) -> None:
        self._projections: dict[str, OrderProjection] = {}
        self._events: dict[str, list[OrderEvent]] = defaultdict(list)
        self._fills: dict[str, list[FillEvent]] = defaultdict(list)

    def plan(self, intent: OrderIntent, order_id: str, occurred_at: datetime) -> OrderEvent:
        if order_id in self._projections:
            raise ValueError(f"order already exists: {order_id}")
        event = OrderEvent(
            event_id=new_id("ordevt"),
            order_id=order_id,
            intent_id=intent.intent_id,
            strategy_run_id=intent.strategy_run_id,
            symbol=intent.symbol,
            status=OrderStatus.PLANNED,
            event_type=OrderEventType.STATE_TRANSITION,
            occurred_at=occurred_at,
            reason=intent.rationale,
        )
        self._projections[order_id] = OrderProjection(
            order_id=order_id,
            intent_id=intent.intent_id,
            strategy_run_id=intent.strategy_run_id,
            symbol=intent.symbol,
            side=intent.side,
            order_type=intent.order_type,
            time_in_force=intent.time_in_force,
            quantity=quantize(intent.quantity, "0.0000"),
            status=OrderStatus.PLANNED,
            created_at=occurred_at,
            updated_at=occurred_at,
            filled_quantity=ZERO,
            last_event_at=occurred_at,
        )
        self._events[order_id].append(event)
        return event

    def transition(
        self,
        order_id: str,
        new_status: OrderStatus,
        occurred_at: datetime,
        *,
        event_type: OrderEventType = OrderEventType.STATE_TRANSITION,
        broker_order_id: str | None = None,
        reason: str | None = None,
        raw_payload: dict[str, object] | None = None,
    ) -> OrderEvent:
        projection = self.get_projection(order_id)
        allowed = ALLOWED_TRANSITIONS.get(projection.status, set())
        if new_status not in allowed:
            raise ValueError(f"invalid transition: {projection.status.value} -> {new_status.value}")
        if projection.last_event_at is not None and occurred_at < projection.last_event_at:
            raise ValueError("out-of-order order event")

        event = OrderEvent(
            event_id=new_id("ordevt"),
            order_id=projection.order_id,
            intent_id=projection.intent_id,
            strategy_run_id=projection.strategy_run_id,
            symbol=projection.symbol,
            status=new_status,
            event_type=event_type,
            occurred_at=occurred_at,
            broker_order_id=broker_order_id or projection.broker_order_id,
            reason=reason,
            raw_payload=raw_payload,
        )
        self._projections[order_id] = projection.model_copy(
            update={
                "status": new_status,
                "updated_at": occurred_at,
                "last_event_at": occurred_at,
                "broker_order_id": broker_order_id or projection.broker_order_id,
            }
        )
        self._events[order_id].append(event)
        return event

    def record_fill(self, fill: FillEvent) -> OrderProjection:
        projection = self.get_projection(fill.order_id)
        if fill.quantity <= ZERO:
            raise ValueError("fill quantity must be positive")
        if fill.symbol != projection.symbol:
            raise ValueError("fill symbol must match order symbol")
        if fill.intent_id != projection.intent_id:
            raise ValueError("fill intent_id must match order projection")
        if projection.status not in {
            OrderStatus.ACKNOWLEDGED,
            OrderStatus.WORKING,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.FILLED,
        }:
            raise ValueError(f"cannot apply fill while order is {projection.status.value}")
        if any(existing.fill_id == fill.fill_id for existing in self._fills[fill.order_id]):
            raise ValueError("duplicate fill id")
        if projection.last_event_at is not None and fill.occurred_at < projection.last_event_at:
            raise ValueError("out-of-order fill event")

        new_filled_quantity = quantize(projection.filled_quantity + fill.quantity, "0.0000")
        if new_filled_quantity > projection.quantity:
            raise ValueError("fill quantity exceeds order quantity")
        self._fills[fill.order_id].append(fill)
        updated = projection.model_copy(
            update={
                "filled_quantity": new_filled_quantity,
                "updated_at": fill.occurred_at,
                "last_event_at": fill.occurred_at,
            }
        )
        self._projections[fill.order_id] = updated
        return updated

    def get_projection(self, order_id: str) -> OrderProjection:
        if order_id not in self._projections:
            raise KeyError(f"unknown order: {order_id}")
        return self._projections[order_id]

    def order_events(self, order_id: str) -> tuple[OrderEvent, ...]:
        return tuple(self._events.get(order_id, ()))

    def fills(self, order_id: str) -> tuple[FillEvent, ...]:
        return tuple(self._fills.get(order_id, ()))
