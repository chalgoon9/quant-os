from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def _write_krx_strategy_bars(research_store, dataset: str) -> None:
    from quant_os.domain.models import MarketBar
    from quant_os.strategy import load_strategy_specs

    spec = load_strategy_specs()["kr_etf_momo_20_60_v1"]
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = []
    for symbol_index, symbol in enumerate(spec.universe, start=1):
        for index in range(140):
            ts = start + timedelta(days=index)
            base = Decimal("100") + (Decimal(symbol_index) * Decimal("5")) + Decimal(index)
            bars.append(
                MarketBar(
                    symbol=symbol,
                    timestamp=ts,
                    open=base,
                    high=base + Decimal("1"),
                    low=base - Decimal("1"),
                    close=base + Decimal("0.5"),
                    volume=Decimal("1000"),
                )
            )
    research_store.write_bars(dataset, bars)


def test_run_backtest_request_persists_catalog_artifacts_and_metadata(tmp_path) -> None:
    from quant_os.backtest.profile import load_backtest_profiles
    from quant_os.backtest.request import BacktestRequest
    from quant_os.backtest.service import run_backtest_request
    from quant_os.config.loader import load_settings
    from quant_os.db.store import OperationalStore
    from quant_os.research_store.store import ResearchStore
    from tests.integration.helpers import write_test_config

    config_path = write_test_config(tmp_path)
    settings = load_settings(config_path)
    research_store = ResearchStore(
        root=tmp_path / "data" / "normalized",
        duckdb_path=tmp_path / "research" / "quant_os.duckdb",
    )
    _write_krx_strategy_bars(research_store, "krx_etf_daily")

    request = BacktestRequest(
        strategy_id="kr_etf_momo_20_60_v1",
        dataset="krx_etf_daily",
        profile_id="baseline",
        notes="catalog run",
        tags=("phase6",),
    )
    artifact = run_backtest_request(settings, request)
    store = OperationalStore(f"sqlite:///{tmp_path / 'var' / 'quant_os.db'}")
    run = store.get_strategy_run(artifact.result.run_id)
    filtered = store.list_strategy_runs(limit=10, strategy_id="kr_etf_momo_20_60_v1", profile_id="baseline")
    profiles = load_backtest_profiles()

    assert profiles["baseline"].profile_id == "baseline"
    assert artifact.path.exists()
    assert "kr_etf_momo_20_60_v1" in str(artifact.path)
    assert run.strategy_id == "kr_etf_momo_20_60_v1"
    assert run.profile_id == "baseline"
    assert run.dataset == "krx_etf_daily"
    assert run.artifact_path == str(artifact.path)
    assert len(filtered) >= 1
