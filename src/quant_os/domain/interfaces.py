from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol

from quant_os.domain.models import (
    FillEvent,
    OrderEvent,
    OrderIntent,
    PortfolioState,
    SubmitResult,
    TargetExposure,
)


class Strategy(Protocol):
    def generate_targets(self, as_of: datetime) -> list[TargetExposure]:
        """Return target exposures only, never order intents."""


class RiskManager(Protocol):
    def review(self, targets: list[TargetExposure], portfolio: PortfolioState) -> list[TargetExposure]:
        """Fail closed and return only approved targets."""


class IntentGenerator(Protocol):
    def diff_to_intents(
        self,
        approved_targets: list[TargetExposure],
        portfolio: PortfolioState,
    ) -> list[OrderIntent]:
        """Convert approved targets into order intents."""


class ExecutionAdapter(Protocol):
    def submit_intent(self, intent: OrderIntent) -> SubmitResult:
        ...

    def cancel_order(self, order_id: str) -> None:
        ...

    def sync_events(self, since: datetime | None) -> Iterable[OrderEvent | FillEvent]:
        ...

    def get_portfolio_state(self) -> PortfolioState:
        ...


class LedgerProjector(Protocol):
    def apply_order_event(self, event: OrderEvent) -> None:
        ...

    def apply_fill_event(self, event: FillEvent) -> None:
        ...
