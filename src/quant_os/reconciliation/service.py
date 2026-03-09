from __future__ import annotations

from decimal import Decimal

from quant_os.db.store import OperationalStore
from quant_os.domain.enums import ReconciliationStatus
from quant_os.domain.ids import new_id
from quant_os.domain.models import (
    ExternalStateSnapshot,
    OrderProjection,
    PortfolioState,
    ReconciliationIssue,
    ReconciliationResult,
)
from quant_os.domain.types import ZERO, quantize
from quant_os.portfolio.analytics import position_map


class PortfolioReconciler:
    def __init__(
        self,
        *,
        cash_tolerance: Decimal,
        position_tolerance: Decimal,
        store: OperationalStore | None = None,
    ) -> None:
        self.cash_tolerance = quantize(cash_tolerance, "0.0000")
        self.position_tolerance = quantize(position_tolerance, "0.0000")
        self._store = store

    def reconcile(
        self,
        *,
        local_portfolio: PortfolioState,
        external_state: ExternalStateSnapshot,
        local_open_orders: tuple[OrderProjection, ...] = (),
    ) -> ReconciliationResult:
        issues: list[ReconciliationIssue] = []
        occurred_at = max(local_portfolio.as_of, external_state.as_of)

        if local_portfolio.base_currency != external_state.base_currency:
            issues.append(
                ReconciliationIssue(
                    code="base_currency_mismatch",
                    message="base currency mismatch",
                    details={
                        "local": local_portfolio.base_currency,
                        "external": external_state.base_currency,
                    },
                )
            )

        cash_delta = abs(local_portfolio.cash_balance - external_state.cash_balance)
        if cash_delta > self.cash_tolerance:
            issues.append(
                ReconciliationIssue(
                    code="cash_balance_mismatch",
                    message="cash balance mismatch",
                    details={
                        "local": str(quantize(local_portfolio.cash_balance, "0.0000")),
                        "external": str(quantize(external_state.cash_balance, "0.0000")),
                        "delta": str(quantize(cash_delta, "0.0000")),
                    },
                )
            )

        local_positions = position_map(local_portfolio)
        external_positions = {position.symbol: position for position in external_state.positions}
        for symbol in sorted(set(local_positions) | set(external_positions)):
            local_qty = quantize(local_positions.get(symbol).quantity, "0.0000") if symbol in local_positions else ZERO
            external_qty = quantize(external_positions.get(symbol).quantity, "0.0000") if symbol in external_positions else ZERO
            if abs(local_qty - external_qty) > self.position_tolerance:
                issues.append(
                    ReconciliationIssue(
                        code="position_quantity_mismatch",
                        message=f"position quantity mismatch for {symbol}",
                        details={
                            "symbol": symbol,
                            "local": str(local_qty),
                            "external": str(external_qty),
                        },
                    )
                )

        if _normalize_orders(local_open_orders) != _normalize_orders(external_state.open_orders):
            issues.append(
                ReconciliationIssue(
                    code="open_order_mismatch",
                    message="open order projection mismatch",
                    details={
                        "local_count": len(local_open_orders),
                        "external_count": len(external_state.open_orders),
                    },
                )
            )

        status = ReconciliationStatus.MATCHED if not issues else ReconciliationStatus.MISMATCH
        summary = "reconciliation matched" if not issues else f"{len(issues)} mismatch(es): " + ", ".join(issue.code for issue in issues)
        result = ReconciliationResult(
            reconciliation_id=new_id("recon"),
            occurred_at=occurred_at,
            status=status,
            mismatch_count=len(issues),
            requires_manual_intervention=bool(issues),
            summary=summary,
            issues=tuple(issues),
        )
        if self._store is not None:
            self._store.append_reconciliation_result(result)
        return result


def _normalize_orders(orders: tuple[OrderProjection, ...]) -> tuple[tuple[str, ...], ...]:
    return tuple(
        sorted(
            (
                order.symbol,
                order.side.value,
                order.status.value,
                str(quantize(order.quantity, "0.0000")),
                str(quantize(order.filled_quantity, "0.0000")),
            )
            for order in orders
        )
    )
