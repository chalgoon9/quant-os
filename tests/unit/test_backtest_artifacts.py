from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal


def test_backtest_artifact_store_round_trips_latest_result(tmp_path) -> None:
    from quant_os.backtest.results import BacktestArtifactStore, StoredBacktestResult
    from quant_os.backtest.simple import EquityPoint, SimulatedTrade
    from quant_os.domain.enums import OrderSide

    store = BacktestArtifactStore(tmp_path / "artifacts")
    result = StoredBacktestResult(
        run_id="backtest_1",
        strategy_name="daily_momentum",
        dataset="krx_etf_daily",
        generated_at=datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc),
        as_of=datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
        initial_cash=Decimal("100000"),
        final_nav=Decimal("105000"),
        total_return=Decimal("0.0500"),
        max_drawdown=Decimal("-0.0200"),
        trade_count=2,
        loaded_symbols=("AAA",),
        missing_symbols=("BBB",),
        equity_curve=(
            EquityPoint(
                timestamp=datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
                nav=Decimal("100000"),
                cash=Decimal("100000"),
            ),
            EquityPoint(
                timestamp=datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
                nav=Decimal("105000"),
                cash=Decimal("20000"),
            ),
        ),
        trades=(
            SimulatedTrade(
                timestamp=datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
                symbol="AAA",
                side=OrderSide.BUY,
                quantity=Decimal("1"),
                price=Decimal("100"),
                notional=Decimal("100"),
            ),
        ),
    )

    path = store.save(result)
    loaded = store.latest()

    assert path.exists()
    assert loaded.run_id == result.run_id
    assert loaded.final_nav == result.final_nav
    assert loaded.loaded_symbols == ("AAA",)
    assert loaded.trades[0].symbol == "AAA"
