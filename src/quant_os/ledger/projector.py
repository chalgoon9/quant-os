from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from quant_os.domain.enums import OrderSide
from quant_os.domain.ids import new_id
from quant_os.domain.models import (
    CashLedgerEntry,
    FillEvent,
    LedgerSnapshot,
    OrderEvent,
    PortfolioState,
    Position,
    PositionLot,
)
from quant_os.domain.types import ZERO, quantize


class LedgerProjector:
    def __init__(
        self,
        *,
        base_currency: str,
        initial_cash: Decimal,
        initial_positions: tuple[Position, ...] = (),
    ) -> None:
        self.base_currency = base_currency
        self._cash_balance = quantize(initial_cash, "0.0000")
        self._initial_cash = quantize(initial_cash, "0.0000")
        self._realized_pnl = ZERO
        self._order_events: list[OrderEvent] = []
        self._cash_entries: list[CashLedgerEntry] = []
        self._lots_by_symbol: dict[str, list[PositionLot]] = defaultdict(list)

        for position in initial_positions:
            if position.quantity <= ZERO:
                continue
            opened_at = datetime.now(tz=timezone.utc)
            self._lots_by_symbol[position.symbol].append(
                PositionLot(
                    lot_id=new_id("lot"),
                    symbol=position.symbol,
                    opened_at=opened_at,
                    quantity=quantize(position.quantity, "0.0000"),
                    unit_cost=quantize(position.average_cost, "0.0000"),
                )
            )

    def apply_order_event(self, event: OrderEvent) -> None:
        self._order_events.append(event)

    def apply_fill_event(self, fill: FillEvent) -> None:
        quantity = quantize(fill.quantity, "0.0000")
        gross_amount = quantize(quantity * fill.price, "0.0000")
        fee = quantize(fill.fee, "0.0000")
        tax = quantize(fill.tax, "0.0000")

        if fill.side is OrderSide.BUY:
            total_cost = quantize(gross_amount + fee + tax, "0.0000")
            unit_cost = quantize(total_cost / quantity, "0.0000")
            self._lots_by_symbol[fill.symbol].append(
                PositionLot(
                    lot_id=new_id("lot"),
                    symbol=fill.symbol,
                    opened_at=fill.occurred_at,
                    quantity=quantity,
                    unit_cost=unit_cost,
                )
            )
            self._cash_balance = quantize(self._cash_balance - total_cost, "0.0000")
            self._append_cash_entry(
                occurred_at=fill.occurred_at,
                amount=-total_cost,
                reference_id=fill.fill_id,
                notes=f"buy {fill.symbol}",
            )
            return

        net_proceeds = quantize(gross_amount - fee - tax, "0.0000")
        cost_basis = self._consume_lots(fill.symbol, quantity)
        self._realized_pnl = quantize(self._realized_pnl + (net_proceeds - cost_basis), "0.0000")
        self._cash_balance = quantize(self._cash_balance + net_proceeds, "0.0000")
        self._append_cash_entry(
            occurred_at=fill.occurred_at,
            amount=net_proceeds,
            reference_id=fill.fill_id,
            notes=f"sell {fill.symbol}",
        )

    def snapshot(self, as_of: datetime, market_prices: dict[str, Decimal]) -> LedgerSnapshot:
        positions: dict[str, Position] = {}
        unrealized_pnl = ZERO
        market_value_total = ZERO

        for symbol, lots in sorted(self._lots_by_symbol.items()):
            live_lots = [lot for lot in lots if lot.quantity > ZERO]
            if not live_lots:
                continue
            quantity = quantize(sum(lot.quantity for lot in live_lots), "0.0000")
            total_cost = quantize(sum(lot.quantity * lot.unit_cost for lot in live_lots), "0.0000")
            average_cost = ZERO if quantity == ZERO else quantize(total_cost / quantity, "0.0000")
            market_price = quantize(market_prices.get(symbol, average_cost), "0.0000")
            market_value = quantize(quantity * market_price, "0.0000")
            market_value_total = quantize(market_value_total + market_value, "0.0000")
            unrealized_pnl = quantize(unrealized_pnl + (market_value - total_cost), "0.0000")
            positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                average_cost=average_cost,
                market_price=market_price,
            )

        nav = quantize(self._cash_balance + market_value_total, "0.0000")
        total_pnl = quantize(self._realized_pnl + unrealized_pnl, "0.0000")
        return LedgerSnapshot(
            as_of=as_of,
            base_currency=self.base_currency,
            cash_balance=self._cash_balance,
            positions=positions,
            realized_pnl=self._realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,
            nav=nav,
        )

    def portfolio_state(self, as_of: datetime, market_prices: dict[str, Decimal]) -> PortfolioState:
        snapshot = self.snapshot(as_of, market_prices)
        return PortfolioState(
            as_of=as_of,
            base_currency=self.base_currency,
            cash_balance=snapshot.cash_balance,
            net_asset_value=max(snapshot.nav, Decimal("0.0001")),
            positions=tuple(snapshot.positions.values()),
            market_prices=market_prices,
        )

    def cash_ledger_entries(self) -> tuple[CashLedgerEntry, ...]:
        return tuple(self._cash_entries)

    def _append_cash_entry(
        self,
        *,
        occurred_at: datetime,
        amount: Decimal,
        reference_id: str,
        notes: str,
    ) -> None:
        self._cash_entries.append(
            CashLedgerEntry(
                entry_id=new_id("cash"),
                occurred_at=occurred_at,
                currency=self.base_currency,
                amount=quantize(amount, "0.0000"),
                balance_after=self._cash_balance,
                reference_type="fill",
                reference_id=reference_id,
                notes=notes,
            )
        )

    def _consume_lots(self, symbol: str, quantity: Decimal) -> Decimal:
        remaining = quantize(quantity, "0.0000")
        lots = self._lots_by_symbol.get(symbol, [])
        total_cost = ZERO

        for index, lot in enumerate(list(lots)):
            if remaining == ZERO:
                break
            lot_quantity = quantize(lot.quantity, "0.0000")
            if lot_quantity == ZERO:
                continue
            consumed = min(lot_quantity, remaining)
            total_cost = quantize(total_cost + (consumed * lot.unit_cost), "0.0000")
            remaining = quantize(remaining - consumed, "0.0000")
            new_quantity = quantize(lot_quantity - consumed, "0.0000")
            lots[index] = lot.model_copy(update={"quantity": new_quantity}) if new_quantity > ZERO else lot.model_copy(update={"quantity": ZERO})

        if remaining > ZERO:
            raise ValueError(f"sell quantity exceeds available position for {symbol}")

        self._lots_by_symbol[symbol] = [lot for lot in lots if lot.quantity > ZERO]
        return quantize(total_cost, "0.0000")
