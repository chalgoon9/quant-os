from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from quant_os.db.store import OperationalStore
from quant_os.domain.enums import KillSwitchReason, ReconciliationStatus
from quant_os.domain.ids import new_id
from quant_os.domain.models import KillSwitchEvent, LedgerSnapshot, ReconciliationResult
from quant_os.domain.types import ZERO, quantize


class KillSwitch:
    def __init__(
        self,
        *,
        daily_loss_limit: Decimal,
        stale_market_data_seconds: int,
        store: OperationalStore | None = None,
    ) -> None:
        self.daily_loss_limit = quantize(daily_loss_limit, "0.0000")
        self.stale_market_data_seconds = stale_market_data_seconds
        self._store = store
        self._active_by_reason: dict[KillSwitchReason, KillSwitchEvent] = {}
        self._history: list[KillSwitchEvent] = []

    def evaluate_daily_loss(self, *, snapshot: LedgerSnapshot, start_of_day_nav: Decimal) -> KillSwitchEvent | None:
        if start_of_day_nav <= ZERO:
            raise ValueError("start_of_day_nav must be positive")
        loss_ratio = quantize((start_of_day_nav - snapshot.nav) / start_of_day_nav, "0.0001")
        if loss_ratio < self.daily_loss_limit:
            return None
        return self.trigger(
            reason=KillSwitchReason.DAILY_LOSS_LIMIT,
            triggered_at=snapshot.as_of,
            trigger_value=loss_ratio,
            threshold_value=self.daily_loss_limit,
            details={"nav": str(quantize(snapshot.nav, "0.0000"))},
        )

    def evaluate_reconciliation(self, reconciliation: ReconciliationResult) -> KillSwitchEvent | None:
        if reconciliation.status is ReconciliationStatus.MATCHED:
            return None
        return self.trigger(
            reason=KillSwitchReason.RECONCILIATION_FAILURE,
            triggered_at=reconciliation.occurred_at,
            trigger_value=Decimal(reconciliation.mismatch_count),
            threshold_value=ZERO,
            details={"summary": reconciliation.summary},
        )

    def evaluate_market_data_freshness(
        self,
        *,
        as_of: datetime,
        latest_market_data_at: datetime,
    ) -> KillSwitchEvent | None:
        age_seconds = max(0, int((as_of - latest_market_data_at).total_seconds()))
        if age_seconds <= self.stale_market_data_seconds:
            return None
        return self.trigger(
            reason=KillSwitchReason.STALE_MARKET_DATA,
            triggered_at=as_of,
            trigger_value=Decimal(age_seconds),
            threshold_value=Decimal(self.stale_market_data_seconds),
            details={"latest_market_data_at": latest_market_data_at.isoformat()},
        )

    def evaluate_event_write_failure(
        self,
        *,
        triggered_at: datetime,
        component: str,
        error_message: str,
    ) -> KillSwitchEvent:
        return self.trigger(
            reason=KillSwitchReason.EVENT_WRITE_FAILURE,
            triggered_at=triggered_at,
            details={
                "component": component,
                "error_message": error_message,
            },
        )

    def evaluate_duplicate_intent(
        self,
        *,
        intent_id: str,
        triggered_at: datetime,
    ) -> KillSwitchEvent:
        return self.trigger(
            reason=KillSwitchReason.DUPLICATE_INTENT,
            triggered_at=triggered_at,
            trigger_value=Decimal("1"),
            threshold_value=ZERO,
            details={"intent_id": intent_id},
        )

    def evaluate_unknown_open_orders(
        self,
        *,
        triggered_at: datetime,
        order_ids: tuple[str, ...],
    ) -> KillSwitchEvent | None:
        if not order_ids:
            return None
        return self.trigger(
            reason=KillSwitchReason.UNKNOWN_OPEN_ORDER,
            triggered_at=triggered_at,
            trigger_value=Decimal(len(order_ids)),
            threshold_value=ZERO,
            details={"order_ids": list(order_ids)},
        )

    def trigger(
        self,
        *,
        reason: KillSwitchReason,
        triggered_at: datetime,
        trigger_value: Decimal | None = None,
        threshold_value: Decimal | None = None,
        details: dict[str, object] | None = None,
    ) -> KillSwitchEvent:
        existing = self._active_by_reason.get(reason)
        if existing is not None:
            return existing
        event = KillSwitchEvent(
            event_id=new_id("killsw"),
            reason=reason,
            triggered_at=triggered_at,
            trigger_value=trigger_value,
            threshold_value=threshold_value,
            details=details,
            is_active=True,
        )
        self._active_by_reason[reason] = event
        self._history.append(event)
        if self._store is not None:
            self._store.save_kill_switch_event(event)
        return event

    def reset(self, cleared_at: datetime) -> None:
        if not self._active_by_reason:
            return
        updated_history: list[KillSwitchEvent] = []
        for event in self._history:
            if event.reason in self._active_by_reason and event.is_active:
                cleared_event = event.model_copy(update={"is_active": False, "cleared_at": cleared_at})
                updated_history.append(cleared_event)
                if self._store is not None:
                    self._store.save_kill_switch_event(cleared_event)
            else:
                updated_history.append(event)
        self._history = updated_history
        self._active_by_reason.clear()

    def can_submit_orders(self) -> bool:
        return not self._active_by_reason

    def active_events(self) -> tuple[KillSwitchEvent, ...]:
        return tuple(self._active_by_reason.values())

    def event_history(self) -> tuple[KillSwitchEvent, ...]:
        return tuple(self._history)
