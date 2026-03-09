from __future__ import annotations

from decimal import Decimal

from quant_os.domain.models import PortfolioState, Position, TargetExposure
from quant_os.domain.types import ZERO, quantize


def resolve_price_map(portfolio: PortfolioState) -> dict[str, Decimal]:
    prices = dict(portfolio.market_prices)
    for position in portfolio.positions:
        if position.market_price is not None:
            prices[position.symbol] = position.market_price
        elif position.average_cost > ZERO and position.symbol not in prices:
            prices[position.symbol] = position.average_cost
    return prices


def position_map(portfolio: PortfolioState) -> dict[str, Position]:
    return {position.symbol: position for position in portfolio.positions}


def current_weights(portfolio: PortfolioState) -> dict[str, Decimal]:
    if portfolio.net_asset_value <= ZERO:
        raise ValueError("portfolio.net_asset_value must be positive")

    prices = resolve_price_map(portfolio)
    weights: dict[str, Decimal] = {}
    for position in portfolio.positions:
        if position.quantity == ZERO:
            continue
        price = prices.get(position.symbol)
        if price is None:
            raise ValueError(f"missing market price for {position.symbol}")
        weights[position.symbol] = quantize(
            (position.quantity * price) / portfolio.net_asset_value,
            "0.0001",
        )
    return weights


def target_weight_map(targets: list[TargetExposure]) -> dict[str, Decimal]:
    return {target.symbol: target.target_weight for target in targets if target.target_weight != ZERO}
