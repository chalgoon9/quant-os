from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN

from quant_os.domain.enums import OrderSide
from quant_os.domain.models import BacktestSettings, MarketBar, PortfolioState, Position
from quant_os.domain.types import ZERO, quantize


@dataclass(frozen=True)
class EquityPoint:
    timestamp: object
    nav: Decimal
    cash: Decimal


@dataclass(frozen=True)
class SimulatedTrade:
    timestamp: object
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    notional: Decimal


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: tuple[EquityPoint, ...]
    trades: tuple[SimulatedTrade, ...]
    final_nav: Decimal
    trade_count: int
    max_drawdown: Decimal


class SimpleBacktester:
    def __init__(
        self,
        bars_by_symbol: Mapping[str, Sequence[MarketBar]],
        strategy,
        risk_manager,
        intent_generator,
        settings: BacktestSettings,
    ) -> None:
        self.bars_by_symbol = {symbol: sorted(list(bars), key=lambda bar: bar.timestamp) for symbol, bars in bars_by_symbol.items()}
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.intent_generator = intent_generator
        self.settings = settings

    def run(self) -> BacktestResult:
        cash = self.settings.initial_cash
        quantities: dict[str, Decimal] = {}
        average_costs: dict[str, Decimal] = {}
        trades: list[SimulatedTrade] = []
        equity_curve: list[EquityPoint] = []
        peak_nav = self.settings.initial_cash
        max_drawdown = ZERO
        timeline = self._timeline()

        for index, timestamp in enumerate(timeline):
            prices = self._price_map(timestamp)
            portfolio = self._portfolio_state(timestamp, cash, quantities, average_costs, prices)
            nav = quantize(cash + sum(quantity * prices[symbol] for symbol, quantity in quantities.items() if quantity != ZERO), "0.0001")
            peak_nav = max(peak_nav, nav)
            drawdown = ZERO if peak_nav == ZERO else quantize((nav / peak_nav) - Decimal("1"), "0.0001")
            max_drawdown = min(max_drawdown, drawdown)
            equity_curve.append(EquityPoint(timestamp=timestamp, nav=nav, cash=quantize(cash, "0.0001")))

            if index >= len(timeline) - 1:
                continue

            approved_targets = self.risk_manager.review(self.strategy.generate_targets(timestamp), portfolio)
            intents = self.intent_generator.diff_to_intents(approved_targets, portfolio)
            execution_timestamp = timeline[index + 1]
            execution_prices = self._execution_price_map(execution_timestamp)

            for intent in intents:
                price = execution_prices.get(intent.symbol)
                if price is None:
                    continue
                fill_price = _apply_slippage(price, intent.side, self.settings.slippage_bps)
                executed_quantity = self._execute_intent(
                    intent.symbol,
                    intent.side,
                    intent.quantity,
                    fill_price,
                    cash,
                    quantities,
                    average_costs,
                )
                if executed_quantity == ZERO:
                    continue
                notional = quantize(executed_quantity * fill_price, "0.0001")
                commission = quantize(notional * self.settings.commission_bps / Decimal("10000"), "0.0001")
                if intent.side is OrderSide.BUY:
                    cash -= notional + commission
                else:
                    cash += notional - commission
                trades.append(
                    SimulatedTrade(
                        timestamp=execution_timestamp,
                        symbol=intent.symbol,
                        side=intent.side,
                        quantity=executed_quantity,
                        price=fill_price,
                        notional=notional,
                    )
                )

        final_nav = equity_curve[-1].nav if equity_curve else self.settings.initial_cash
        return BacktestResult(
            equity_curve=tuple(equity_curve),
            trades=tuple(trades),
            final_nav=final_nav,
            trade_count=len(trades),
            max_drawdown=max_drawdown,
        )

    def _timeline(self) -> list[object]:
        timestamps = {bar.timestamp for bars in self.bars_by_symbol.values() for bar in bars}
        return sorted(timestamps)

    def _price_map(self, timestamp) -> dict[str, Decimal]:
        prices: dict[str, Decimal] = {}
        for symbol, bars in self.bars_by_symbol.items():
            prior = [bar for bar in bars if bar.timestamp <= timestamp]
            if prior:
                prices[symbol] = prior[-1].close
        return prices

    def _execution_price_map(self, timestamp) -> dict[str, Decimal]:
        prices: dict[str, Decimal] = {}
        for symbol, bars in self.bars_by_symbol.items():
            exact = [bar for bar in bars if bar.timestamp == timestamp]
            if exact:
                prices[symbol] = exact[0].open
        return prices

    def _portfolio_state(
        self,
        timestamp,
        cash: Decimal,
        quantities: dict[str, Decimal],
        average_costs: dict[str, Decimal],
        prices: dict[str, Decimal],
    ) -> PortfolioState:
        positions = tuple(
            Position(
                symbol=symbol,
                quantity=quantity,
                average_cost=average_costs.get(symbol, ZERO),
                market_price=prices[symbol],
            )
            for symbol, quantity in sorted(quantities.items())
            if quantity != ZERO and symbol in prices
        )
        nav = quantize(cash + sum(position.quantity * position.market_price for position in positions if position.market_price), "0.0001")
        return PortfolioState(
            as_of=timestamp,
            base_currency="KRW",
            cash_balance=quantize(cash, "0.0001"),
            net_asset_value=max(nav, Decimal("0.0001")),
            positions=positions,
            market_prices=prices,
        )

    def _execute_intent(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        fill_price: Decimal,
        cash: Decimal,
        quantities: dict[str, Decimal],
        average_costs: dict[str, Decimal],
    ) -> Decimal:
        if side is OrderSide.BUY:
            max_affordable = _affordable_quantity(
                cash=cash,
                price=fill_price,
                commission_bps=self.settings.commission_bps,
                lot_size=self.intent_generator.policy.lot_size,
            )
            executed_quantity = min(quantity, max_affordable)
            if executed_quantity == ZERO:
                return ZERO
            previous_quantity = quantities.get(symbol, ZERO)
            previous_cost = average_costs.get(symbol, ZERO)
            new_total_quantity = previous_quantity + executed_quantity
            average_costs[symbol] = (
                ZERO
                if new_total_quantity == ZERO
                else quantize(
                    ((previous_quantity * previous_cost) + (executed_quantity * fill_price)) / new_total_quantity,
                    "0.0001",
                )
            )
            quantities[symbol] = new_total_quantity
            return executed_quantity

        available = quantities.get(symbol, ZERO)
        executed_quantity = min(quantity, available)
        if executed_quantity == ZERO:
            return ZERO
        remaining = available - executed_quantity
        quantities[symbol] = remaining
        if remaining == ZERO:
            average_costs.pop(symbol, None)
        return executed_quantity


def _apply_slippage(price: Decimal, side: OrderSide, slippage_bps: Decimal) -> Decimal:
    multiplier = Decimal("1") + (slippage_bps / Decimal("10000"))
    if side is OrderSide.SELL:
        multiplier = Decimal("1") - (slippage_bps / Decimal("10000"))
    return quantize(price * multiplier, "0.0001")


def _affordable_quantity(
    cash: Decimal,
    price: Decimal,
    commission_bps: Decimal,
    lot_size: Decimal,
) -> Decimal:
    if price <= ZERO:
        return ZERO
    per_unit_cost = price * (Decimal("1") + (commission_bps / Decimal("10000")))
    if per_unit_cost <= ZERO:
        return ZERO
    raw = cash / per_unit_cost
    steps = (raw / lot_size).to_integral_value(rounding=ROUND_DOWN)
    return steps * lot_size
