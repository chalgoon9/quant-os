from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


class _StaticStrategy:
    def __init__(self, targets_by_timestamp):
        self.targets_by_timestamp = targets_by_timestamp

    def generate_targets(self, as_of):
        return self.targets_by_timestamp.get(as_of, [])


class _PassthroughRiskManager:
    def review(self, targets, _portfolio):
        return targets


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
    assert len(result.drawdown_curve) == len(result.equity_curve)
    assert len(result.position_path) == len(result.equity_curve)
    assert result.total_turnover > Decimal("0")
    assert result.total_traded_notional > Decimal("0")
    assert result.trades[0].timestamp == start + timedelta(days=60)


def test_simple_backtester_caps_fill_by_next_bar_volume_share() -> None:
    from quant_os.backtest.simple import SimpleBacktester
    from quant_os.domain.models import BacktestSettings, IntentPolicy, MarketBar, TargetExposure
    from quant_os.intent.generator import TargetExposureIntentGenerator

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    history = {
        "AAA": [
            MarketBar(
                symbol="AAA",
                timestamp=start,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("100"),
            ),
            MarketBar(
                symbol="AAA",
                timestamp=start + timedelta(days=1),
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("20"),
            ),
        ]
    }
    strategy = _StaticStrategy(
        {
            start: [TargetExposure(symbol="AAA", target_weight=Decimal("1.0"))],
        }
    )
    backtester = SimpleBacktester(
        bars_by_symbol=history,
        strategy=strategy,
        risk_manager=_PassthroughRiskManager(),
        intent_generator=TargetExposureIntentGenerator(
            IntentPolicy(
                lot_size=Decimal("1"),
                min_trade_notional=Decimal("0"),
            ),
            strategy_run_id="backtest_run",
        ),
        settings=BacktestSettings(
            initial_cash=Decimal("10000"),
            commission_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
            sell_tax_bps=Decimal("0"),
            max_bar_volume_share=Decimal("0.10"),
        ),
    )

    result = backtester.run()

    assert len(result.trades) == 1
    assert result.trades[0].quantity == Decimal("2")


def test_simple_backtester_applies_sell_tax_to_exit_trade() -> None:
    from quant_os.backtest.simple import SimpleBacktester
    from quant_os.domain.models import BacktestSettings, IntentPolicy, MarketBar, TargetExposure
    from quant_os.intent.generator import TargetExposureIntentGenerator

    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    day_1 = start
    day_2 = start + timedelta(days=1)
    day_3 = start + timedelta(days=2)
    history = {
        "AAA": [
            MarketBar(
                symbol="AAA",
                timestamp=day_1,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
            MarketBar(
                symbol="AAA",
                timestamp=day_2,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
            MarketBar(
                symbol="AAA",
                timestamp=day_3,
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100"),
                volume=Decimal("1000"),
            ),
        ]
    }
    strategy = _StaticStrategy(
        {
            day_1: [TargetExposure(symbol="AAA", target_weight=Decimal("1.0"))],
            day_2: [],
        }
    )
    backtester = SimpleBacktester(
        bars_by_symbol=history,
        strategy=strategy,
        risk_manager=_PassthroughRiskManager(),
        intent_generator=TargetExposureIntentGenerator(
            IntentPolicy(
                lot_size=Decimal("1"),
                min_trade_notional=Decimal("0"),
            ),
            strategy_run_id="backtest_run",
        ),
        settings=BacktestSettings(
            initial_cash=Decimal("1000"),
            commission_bps=Decimal("0"),
            slippage_bps=Decimal("0"),
            sell_tax_bps=Decimal("10"),
            max_bar_volume_share=Decimal("1.00"),
        ),
    )

    result = backtester.run()

    assert len(result.trades) == 2
    assert result.trades[-1].side.value == "sell"
    assert result.total_tax == Decimal("1.0000")
    assert result.final_nav == Decimal("999.0000")
