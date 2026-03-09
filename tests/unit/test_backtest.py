from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def test_simple_backtester_replays_momentum_strategy() -> None:
    from quant_os.backtest.simple import SimpleBacktester
    from quant_os.domain.models import BacktestSettings, IntentPolicy, MarketBar, RiskPolicy, StrategyDefinition
    from quant_os.intent.generator import TargetExposureIntentGenerator
    from quant_os.risk.simple import SimpleRiskManager
    from quant_os.strategy.momentum import DailyMomentumStrategy

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history: dict[str, list[MarketBar]] = {"AAA": [], "BBB": []}

    for index in range(90):
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
                volume=Decimal("1000"),
            )
        )

    strategy = DailyMomentumStrategy(
        StrategyDefinition(
            name="daily_momentum",
            universe=("AAA", "BBB"),
            rebalance_calendar="daily",
            max_names=1,
            target_gross_exposure_limit=Decimal("0.95"),
            fast_lookback=20,
            slow_lookback=60,
            trend_lookback=40,
        ),
        history,
    )
    risk_manager = SimpleRiskManager(
        RiskPolicy(
            max_single_name_weight=Decimal("0.95"),
            min_cash_buffer=Decimal("0.05"),
            daily_loss_limit=Decimal("0.03"),
            max_turnover=Decimal("1.00"),
            fail_closed=True,
        )
    )
    generator = TargetExposureIntentGenerator(
        IntentPolicy(
            lot_size=Decimal("1"),
            min_trade_notional=Decimal("1000"),
        ),
        strategy_run_id="backtest_run",
    )
    backtester = SimpleBacktester(
        bars_by_symbol=history,
        strategy=strategy,
        risk_manager=risk_manager,
        intent_generator=generator,
        settings=BacktestSettings(
            initial_cash=Decimal("100000"),
            commission_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
        ),
    )

    result = backtester.run()

    assert result.final_nav > Decimal("100000")
    assert result.trade_count >= 1
    assert result.equity_curve[-1].nav == result.final_nav
    assert result.trades[0].timestamp == start + timedelta(days=60)
