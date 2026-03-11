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
class DrawdownPoint:
    timestamp: object
    drawdown: Decimal


@dataclass(frozen=True)
class PositionPoint:
    symbol: str
    quantity: Decimal
    market_price: Decimal
    market_value: Decimal
    weight: Decimal


@dataclass(frozen=True)
class PositionSnapshot:
    timestamp: object
    positions: tuple[PositionPoint, ...]


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: tuple[EquityPoint, ...]
    drawdown_curve: tuple[DrawdownPoint, ...]
    position_path: tuple[PositionSnapshot, ...]
    trades: tuple[SimulatedTrade, ...]
    final_nav: Decimal
    trade_count: int
    max_drawdown: Decimal
    total_turnover: Decimal
    total_commission: Decimal
    total_tax: Decimal
    total_slippage_cost: Decimal
    total_traded_notional: Decimal


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
        drawdown_curve: list[DrawdownPoint] = []
        position_path: list[PositionSnapshot] = []
        peak_nav = self.settings.initial_cash
        max_drawdown = ZERO
        total_turnover = ZERO
        total_commission = ZERO
        total_tax = ZERO
        total_slippage_cost = ZERO
        total_traded_notional = ZERO
        timeline = self._timeline()

        for index, timestamp in enumerate(timeline):
            prices = self._price_map(timestamp)
            portfolio = self._portfolio_state(timestamp, cash, quantities, average_costs, prices)
            nav = quantize(cash + sum(quantity * prices[symbol] for symbol, quantity in quantities.items() if quantity != ZERO), "0.0001")
            peak_nav = max(peak_nav, nav)
            drawdown = ZERO if peak_nav == ZERO else quantize((nav / peak_nav) - Decimal("1"), "0.0001")
            max_drawdown = min(max_drawdown, drawdown)
            equity_curve.append(EquityPoint(timestamp=timestamp, nav=nav, cash=quantize(cash, "0.0001")))
            drawdown_curve.append(DrawdownPoint(timestamp=timestamp, drawdown=drawdown))
            position_path.append(self._position_snapshot(timestamp, quantities, prices, nav))

            if index >= len(timeline) - 1:
                continue

            approved_targets = self.risk_manager.review(self.strategy.generate_targets(timestamp), portfolio)
            intents = self.intent_generator.diff_to_intents(approved_targets, portfolio)
            execution_timestamp = timeline[index + 1]
            execution_bars = self._execution_bar_map(execution_timestamp)
            day_traded_notional = ZERO

            for intent in intents:
                execution_bar = execution_bars.get(intent.symbol)
                if execution_bar is None:
                    continue
                price = execution_bar.open
                fill_price = _apply_slippage(price, intent.side, self.settings.slippage_bps)
                executed_quantity = self._execute_intent(
                    intent.symbol,
                    intent.side,
                    intent.quantity,
                    fill_price,
                    cash,
                    quantities,
                    average_costs,
                    execution_bar.volume,
                )
                if executed_quantity == ZERO:
                    continue
                notional = quantize(executed_quantity * fill_price, "0.0001")
                commission = quantize(notional * self.settings.commission_bps / Decimal("10000"), "0.0001")
                tax = _sell_tax(notional, intent.side, self.settings.sell_tax_bps)
                slippage_cost = _slippage_cost(
                    reference_price=price,
                    fill_price=fill_price,
                    quantity=executed_quantity,
                    side=intent.side,
                )
                if intent.side is OrderSide.BUY:
                    cash -= notional + commission
                else:
                    cash += notional - commission - tax
                day_traded_notional += notional
                total_traded_notional += notional
                total_commission += commission
                total_tax += tax
                total_slippage_cost += slippage_cost
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
            if day_traded_notional > ZERO and portfolio.net_asset_value > ZERO:
                total_turnover += quantize(day_traded_notional / portfolio.net_asset_value, "0.0001")

        final_nav = equity_curve[-1].nav if equity_curve else self.settings.initial_cash
        return BacktestResult(
            equity_curve=tuple(equity_curve),
            drawdown_curve=tuple(drawdown_curve),
            position_path=tuple(position_path),
            trades=tuple(trades),
            final_nav=final_nav,
            trade_count=len(trades),
            max_drawdown=max_drawdown,
            total_turnover=quantize(total_turnover, "0.0001"),
            total_commission=quantize(total_commission, "0.0001"),
            total_tax=quantize(total_tax, "0.0001"),
            total_slippage_cost=quantize(total_slippage_cost, "0.0001"),
            total_traded_notional=quantize(total_traded_notional, "0.0001"),
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

    def _execution_bar_map(self, timestamp) -> dict[str, MarketBar]:
        bars_by_symbol: dict[str, MarketBar] = {}
        for symbol, bars in self.bars_by_symbol.items():
            exact = [bar for bar in bars if bar.timestamp == timestamp]
            if exact:
                bars_by_symbol[symbol] = exact[0]
        return bars_by_symbol

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

    def _position_snapshot(
        self,
        timestamp,
        quantities: dict[str, Decimal],
        prices: dict[str, Decimal],
        nav: Decimal,
    ) -> PositionSnapshot:
        positions: list[PositionPoint] = []
        for symbol, quantity in sorted(quantities.items()):
            if quantity == ZERO or symbol not in prices:
                continue
            market_price = prices[symbol]
            market_value = quantize(quantity * market_price, "0.0001")
            weight = ZERO if nav <= ZERO else quantize(market_value / nav, "0.0001")
            positions.append(
                PositionPoint(
                    symbol=symbol,
                    quantity=quantity,
                    market_price=market_price,
                    market_value=market_value,
                    weight=weight,
                )
            )
        return PositionSnapshot(timestamp=timestamp, positions=tuple(positions))

    def _execute_intent(
        self,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        fill_price: Decimal,
        cash: Decimal,
        quantities: dict[str, Decimal],
        average_costs: dict[str, Decimal],
        bar_volume: Decimal,
    ) -> Decimal:
        volume_limited = _volume_limited_quantity(
            volume=bar_volume,
            max_bar_volume_share=self.settings.max_bar_volume_share,
            lot_size=self.intent_generator.policy.lot_size,
        )
        if side is OrderSide.BUY:
            max_affordable = _affordable_quantity(
                cash=cash,
                price=fill_price,
                commission_bps=self.settings.commission_bps,
                lot_size=self.intent_generator.policy.lot_size,
            )
            executed_quantity = min(quantity, max_affordable, volume_limited)
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
        executed_quantity = min(quantity, available, volume_limited)
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


def _slippage_cost(
    *,
    reference_price: Decimal,
    fill_price: Decimal,
    quantity: Decimal,
    side: OrderSide,
) -> Decimal:
    if side is OrderSide.BUY:
        return quantize((fill_price - reference_price) * quantity, "0.0001")
    return quantize((reference_price - fill_price) * quantity, "0.0001")


def _sell_tax(notional: Decimal, side: OrderSide, sell_tax_bps: Decimal) -> Decimal:
    if side is not OrderSide.SELL or sell_tax_bps <= ZERO:
        return ZERO
    return quantize(notional * sell_tax_bps / Decimal("10000"), "0.0001")


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


def _volume_limited_quantity(
    *,
    volume: Decimal,
    max_bar_volume_share: Decimal,
    lot_size: Decimal,
) -> Decimal:
    if volume <= ZERO:
        return ZERO
    raw = volume * max_bar_volume_share
    steps = (raw / lot_size).to_integral_value(rounding=ROUND_DOWN)
    return steps * lot_size
