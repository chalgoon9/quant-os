from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from typer.testing import CliRunner


def test_run_backtest_command_writes_latest_artifact(tmp_path) -> None:
    from quant_os.cli.main import app
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import StrategyRunStatus
    from quant_os.domain.models import MarketBar
    from quant_os.research_store.store import ResearchStore
    from tests.integration.helpers import write_test_config

    config_path = write_test_config(tmp_path)
    research_store = ResearchStore(
        root=tmp_path / "data" / "normalized",
        duckdb_path=tmp_path / "research" / "quant_os.duckdb",
    )
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    research_store.write_bars(
        "krx_etf_daily",
        [
            MarketBar(
                symbol="KRW-BTC",
                timestamp=start + timedelta(days=index),
                open=Decimal("100000000") + index * Decimal("100000"),
                high=Decimal("100500000") + index * Decimal("100000"),
                low=Decimal("99500000") + index * Decimal("100000"),
                close=Decimal("100000000") + index * Decimal("120000"),
                volume=Decimal("10"),
            )
            for index in range(90)
        ],
    )

    runner = CliRunner()
    result = runner.invoke(app, ["run-backtest", "--config", str(config_path)])

    latest_path = tmp_path / "data" / "artifacts" / "backtests" / "latest.json"
    run_id = next(line.split("=", 1)[1] for line in result.stdout.splitlines() if line.startswith("run_id="))
    store = OperationalStore(f"sqlite:///{tmp_path / 'var' / 'quant_os.db'}")
    strategy_run = store.get_strategy_run(run_id)

    assert result.exit_code == 0
    assert "strategy_id=daily_momentum" in result.stdout
    assert "strategy=daily_momentum" in result.stdout
    assert "profile_id=runtime-config" in result.stdout
    assert "trade_count=" in result.stdout
    assert "total_turnover=" in result.stdout
    assert "total_commission=" in result.stdout
    assert "total_tax=" in result.stdout
    assert latest_path.exists()
    assert strategy_run.status is StrategyRunStatus.SUCCEEDED
    assert strategy_run.config_payload is not None
    assert strategy_run.config_payload["dataset"] == "krx_etf_daily"
    assert strategy_run.config_payload["config_fingerprint"]


def test_run_backtest_command_records_failed_strategy_run(tmp_path) -> None:
    from quant_os.cli.main import app
    from quant_os.db.store import OperationalStore
    from quant_os.domain.enums import StrategyRunStatus
    from tests.integration.helpers import write_test_config

    config_path = write_test_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["run-backtest", "--config", str(config_path)])

    store = OperationalStore(f"sqlite:///{tmp_path / 'var' / 'quant_os.db'}")
    latest_run = store.list_strategy_runs(limit=1)[0]

    assert result.exit_code == 1
    assert "error=" in result.stdout
    assert latest_run.status is StrategyRunStatus.FAILED
    assert latest_run.config_payload is not None
    assert "error" in latest_run.config_payload


def test_run_backtest_command_supports_strategy_request_mode(tmp_path) -> None:
    from quant_os.cli.main import app
    from quant_os.domain.models import MarketBar
    from quant_os.research_store.store import ResearchStore
    from quant_os.strategy import load_strategy_specs
    from tests.integration.helpers import write_test_config

    config_path = write_test_config(tmp_path)
    research_store = ResearchStore(
        root=tmp_path / "data" / "normalized",
        duckdb_path=tmp_path / "research" / "quant_os.duckdb",
    )
    spec = load_strategy_specs()["kr_etf_momo_20_60_v1"]
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars: list[MarketBar] = []
    for symbol_index, symbol in enumerate(spec.universe, start=1):
        for index in range(140):
            ts = start + timedelta(days=index)
            base = Decimal("100") + Decimal(symbol_index * 5) + Decimal(index)
            bars.append(
                MarketBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=base,
                    high=base + Decimal("1"),
                    low=base - Decimal("1"),
                    close=base + Decimal("0.5"),
                    volume=Decimal("10"),
                )
            )
    research_store.write_bars("krx_etf_daily", bars)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run-backtest",
            "--config",
            str(config_path),
            "--strategy-id",
            "kr_etf_momo_20_60_v1",
            "--dataset",
            "krx_etf_daily",
            "--profile-id",
            "baseline",
        ],
    )

    assert result.exit_code == 0
    assert "strategy_id=kr_etf_momo_20_60_v1" in result.stdout
    assert "profile_id=baseline" in result.stdout
