from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def _build_history() -> dict[str, list]:
    from quant_os.domain.models import MarketBar

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history: dict[str, list[MarketBar]] = {"AAA": [], "BBB": []}

    for index in range(80):
        ts = start + timedelta(days=index)
        history["AAA"].append(
            MarketBar(
                symbol="AAA",
                timestamp=ts,
                open=Decimal("100") + index,
                high=Decimal("101") + index,
                low=Decimal("99") + index,
                close=Decimal("100") + index,
                volume=Decimal("1000"),
            )
        )
        history["BBB"].append(
            MarketBar(
                symbol="BBB",
                timestamp=ts,
                open=Decimal("200") - index,
                high=Decimal("201") - index,
                low=Decimal("199") - index,
                close=Decimal("200") - index,
                volume=Decimal("900"),
            )
        )
    return history


def test_strategy_risk_intent_pipeline_generates_buy_intents() -> None:
    from quant_os.domain.enums import OrderSide
    from quant_os.domain.models import (
        IntentPolicy,
        PortfolioState,
        Position,
        RiskPolicy,
        StrategyDefinition,
    )
    from quant_os.intent.generator import TargetExposureIntentGenerator
    from quant_os.risk.simple import SimpleRiskManager
    from quant_os.strategy.momentum import DailyMomentumStrategy

    history = _build_history()
    as_of = history["AAA"][-1].timestamp
    strategy = DailyMomentumStrategy(
        StrategyDefinition(
            name="daily_momentum",
            universe=("AAA", "BBB"),
            rebalance_calendar="daily",
            max_names=2,
            target_gross_exposure_limit=Decimal("0.95"),
            fast_lookback=20,
            slow_lookback=60,
            trend_lookback=40,
        ),
        history,
    )
    risk_manager = SimpleRiskManager(
        RiskPolicy(
            max_single_name_weight=Decimal("0.40"),
            min_cash_buffer=Decimal("0.10"),
            daily_loss_limit=Decimal("0.03"),
            max_turnover=Decimal("1.00"),
            fail_closed=True,
        )
    )
    portfolio = PortfolioState(
        as_of=as_of,
        base_currency="KRW",
        cash_balance=Decimal("80000"),
        net_asset_value=Decimal("100000"),
        positions=(
            Position(
                symbol="AAA",
                quantity=Decimal("100"),
                average_cost=Decimal("100"),
                market_price=Decimal("179"),
            ),
        ),
        market_prices={"AAA": Decimal("179"), "BBB": Decimal("121")},
    )
    approved = risk_manager.review(strategy.generate_targets(as_of), portfolio)
    generator = TargetExposureIntentGenerator(
        IntentPolicy(
            lot_size=Decimal("1"),
            min_trade_notional=Decimal("1000"),
        ),
        strategy_run_id="run_phase2",
    )
    intents = generator.diff_to_intents(approved, portfolio)

    assert [target.symbol for target in approved] == ["AAA"]
    assert approved[0].target_weight == Decimal("0.40")
    assert len(intents) == 1
    assert intents[0].symbol == "AAA"
    assert intents[0].side is OrderSide.BUY
    assert intents[0].quantity > 0
