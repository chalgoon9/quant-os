from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from quant_os.domain.enums import OrderSide
from quant_os.domain.ids import new_id
from quant_os.domain.models import IntentPolicy, OrderIntent, PortfolioState, TargetExposure
from quant_os.domain.types import ZERO, quantize
from quant_os.portfolio.analytics import current_weights, position_map, resolve_price_map, target_weight_map


class TargetExposureIntentGenerator:
    def __init__(self, policy: IntentPolicy, strategy_run_id: str) -> None:
        self.policy = policy
        self.strategy_run_id = strategy_run_id

    def diff_to_intents(
        self,
        approved_targets: list[TargetExposure],
        portfolio: PortfolioState,
    ) -> list[OrderIntent]:
        current = current_weights(portfolio)
        current_positions = position_map(portfolio)
        target_map = target_weight_map(approved_targets)
        prices = resolve_price_map(portfolio)
        intents: list[OrderIntent] = []

        for symbol in sorted(set(current) | set(target_map)):
            delta_weight = target_map.get(symbol, ZERO) - current.get(symbol, ZERO)
            if delta_weight == ZERO:
                continue
            price = prices.get(symbol)
            if price is None or price <= ZERO:
                continue

            trade_notional = abs(delta_weight) * portfolio.net_asset_value
            if trade_notional < self.policy.min_trade_notional:
                continue

            raw_quantity = trade_notional / price
            quantity = _round_down_to_lot(raw_quantity, self.policy.lot_size)
            if quantity == ZERO:
                continue

            side = OrderSide.BUY if delta_weight > ZERO else OrderSide.SELL
            if side is OrderSide.SELL:
                current_quantity = current_positions.get(symbol).quantity if symbol in current_positions else ZERO
                quantity = min(quantity, _round_down_to_lot(current_quantity, self.policy.lot_size))
                if quantity == ZERO:
                    continue

            intents.append(
                OrderIntent(
                    intent_id=new_id("intent"),
                    strategy_run_id=self.strategy_run_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantize(quantity, "0.0001"),
                    order_type=self.policy.default_order_type,
                    time_in_force=self.policy.time_in_force,
                    rationale=f"target-diff:{quantize(delta_weight, '0.0001')}",
                )
            )

        return intents


def _round_down_to_lot(quantity: Decimal, lot_size: Decimal) -> Decimal:
    steps = (quantity / lot_size).to_integral_value(rounding=ROUND_DOWN)
    return steps * lot_size
