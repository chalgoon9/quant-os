from __future__ import annotations

from decimal import Decimal

from quant_os.domain.models import PortfolioState, RiskPolicy, TargetExposure
from quant_os.domain.types import ZERO, quantize
from quant_os.portfolio.analytics import current_weights, target_weight_map


class SimpleRiskManager:
    def __init__(self, policy: RiskPolicy) -> None:
        self.policy = policy

    def review(self, targets: list[TargetExposure], portfolio: PortfolioState) -> list[TargetExposure]:
        if not targets:
            return []

        current: dict[str, Decimal] = {}
        try:
            current = current_weights(portfolio)
            reviewed = _clip_single_name_limits(targets, self.policy.max_single_name_weight)
            reviewed = _clip_cash_buffer(reviewed, Decimal("1") - self.policy.min_cash_buffer)
            reviewed = _clip_turnover(reviewed, current, self.policy.max_turnover)
            return reviewed
        except ValueError:
            if not self.policy.fail_closed:
                return targets
            return [
                TargetExposure(symbol=symbol, target_weight=weight, rationale="risk-fail-closed-hold")
                for symbol, weight in current.items()
                if weight != ZERO
            ]


def _clip_single_name_limits(targets: list[TargetExposure], max_weight: Decimal) -> list[TargetExposure]:
    reviewed: list[TargetExposure] = []
    for target in targets:
        bounded = max(-max_weight, min(max_weight, target.target_weight))
        if bounded == ZERO:
            continue
        reviewed.append(
            TargetExposure(
                symbol=target.symbol,
                target_weight=quantize(bounded, "0.0001"),
                rationale=target.rationale or "risk-single-name",
            )
        )
    return reviewed


def _clip_cash_buffer(targets: list[TargetExposure], gross_cap: Decimal) -> list[TargetExposure]:
    gross = sum(abs(target.target_weight) for target in targets)
    if gross == ZERO or gross <= gross_cap:
        return targets
    scale = gross_cap / gross
    return [
        TargetExposure(
            symbol=target.symbol,
            target_weight=quantize(target.target_weight * scale, "0.0001"),
            rationale=target.rationale or "risk-cash-buffer",
        )
        for target in targets
        if quantize(target.target_weight * scale, "0.0001") != ZERO
    ]


def _clip_turnover(
    targets: list[TargetExposure],
    current: dict[str, Decimal],
    max_turnover: Decimal,
) -> list[TargetExposure]:
    requested = target_weight_map(targets)
    symbols = set(current) | set(requested)
    turnover = sum(abs(requested.get(symbol, ZERO) - current.get(symbol, ZERO)) for symbol in symbols)
    if turnover == ZERO or turnover <= max_turnover:
        return targets

    scale = max_turnover / turnover
    reviewed: list[TargetExposure] = []
    for symbol in symbols:
        weight = current.get(symbol, ZERO) + ((requested.get(symbol, ZERO) - current.get(symbol, ZERO)) * scale)
        normalized = quantize(weight, "0.0001")
        if normalized == ZERO:
            continue
        reviewed.append(TargetExposure(symbol=symbol, target_weight=normalized, rationale="risk-turnover"))
    return reviewed
