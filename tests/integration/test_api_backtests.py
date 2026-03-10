from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.integration.helpers import build_seeded_runtime, seed_backtest_result


def test_backtest_latest_route_returns_saved_result(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, runtime = build_seeded_runtime(tmp_path)
    seed_backtest_result(config_path, runtime)
    client = TestClient(create_app(config=config_path))

    response = client.get("/api/backtests/latest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["strategy_name"] == "daily_momentum"
    assert payload["summary"]["dataset"] == "krx_etf_daily"
    assert payload["summary"]["trade_count"] >= 1
    assert len(payload["equity_curve"]) >= 1


def test_backtest_latest_route_returns_explicit_error_when_missing(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, _runtime = build_seeded_runtime(tmp_path)
    client = TestClient(create_app(config=config_path))

    response = client.get("/api/backtests/latest")

    assert response.status_code == 404
    assert response.json()["code"] == "backtest_not_found"


def test_backtest_run_explorer_routes_list_detail_and_compare(tmp_path) -> None:
    from quant_os.api.main import create_app
    from quant_os.backtest.request import BacktestRequest
    from quant_os.backtest.service import run_backtest_request
    from quant_os.config.loader import load_settings
    from quant_os.domain.models import MarketBar
    from quant_os.strategy import load_strategy_specs

    config_path, runtime = build_seeded_runtime(tmp_path)
    spec = load_strategy_specs()["kr_etf_momo_20_60_v1"]
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    bars = []
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
    runtime.research_store.write_bars("krx_etf_daily", bars)
    settings = load_settings(config_path)
    first = run_backtest_request(
        settings,
        BacktestRequest(strategy_id="kr_etf_momo_20_60_v1", dataset="krx_etf_daily", profile_id="baseline"),
    )
    second = run_backtest_request(
        settings,
        BacktestRequest(strategy_id="kr_etf_momo_30_90_v1", dataset="krx_etf_daily", profile_id="stress_10bps"),
    )
    client = TestClient(create_app(config=config_path))

    list_response = client.get("/api/backtests/runs", params={"limit": 10})
    detail_response = client.get(f"/api/backtests/runs/{first.result.run_id}")
    compare_response = client.post(
        "/api/backtests/compare",
        json={"run_ids": [first.result.run_id, second.result.run_id]},
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert compare_response.status_code == 200
    assert {item["run_id"] for item in list_response.json()["items"]} >= {first.result.run_id, second.result.run_id}
    assert detail_response.json()["summary"]["strategy_id"] == "kr_etf_momo_20_60_v1"
    assert len(compare_response.json()["items"]) == 2
