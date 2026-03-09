from __future__ import annotations

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
