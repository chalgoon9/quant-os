from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from tests.integration.helpers import build_seeded_runtime


def test_research_routes_list_bars_and_run_upbit_ingestion(tmp_path, monkeypatch) -> None:
    from quant_os.api.main import create_app
    from quant_os.domain.models import MarketBar

    config_path, runtime = build_seeded_runtime(tmp_path)
    runtime.research_store.write_bars(
        "upbit_krw_eth_daily",
        [
            MarketBar(
                symbol="KRW-ETH",
                timestamp=datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
                open=3000000,
                high=3050000,
                low=2950000,
                close=3020000,
                volume=100,
            ),
            MarketBar(
                symbol="KRW-ETH",
                timestamp=datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
                open=3020000,
                high=3060000,
                low=3010000,
                close=3040000,
                volume=120,
            ),
        ],
    )

    class FakeUpbitClient:
        def fetch_daily_bars(self, market: str, *, count: int = 200, to=None):
            assert market == "KRW-BTC"
            assert count == 2
            return [
                MarketBar(
                    symbol="KRW-BTC",
                    timestamp=datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
                    open=150000000,
                    high=151000000,
                    low=149000000,
                    close=150500000,
                    volume=123.45,
                ),
                MarketBar(
                    symbol="KRW-BTC",
                    timestamp=datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
                    open=150500000,
                    high=152000000,
                    low=150000000,
                    close=151000000,
                    volume=111.11,
                ),
            ]

    import quant_os.api.routes.research as research_routes

    monkeypatch.setattr(research_routes, "UpbitQuotationClient", FakeUpbitClient)
    client = TestClient(create_app(config=config_path))

    datasets_response = client.get("/api/research/datasets")
    bars_response = client.get("/api/research/datasets/upbit_krw_eth_daily/bars", params={"symbol": "KRW-ETH", "limit": 1})
    ingestion_response = client.post(
        "/api/research/ingestion/upbit/daily",
        json={"market": "KRW-BTC", "count": 2},
    )

    assert datasets_response.status_code == 200
    assert datasets_response.json()["items"][0]["dataset"] == "upbit_krw_eth_daily"

    assert bars_response.status_code == 200
    assert bars_response.json()["items"][0]["symbol"] == "KRW-ETH"
    assert len(bars_response.json()["items"]) == 1

    assert ingestion_response.status_code == 200
    assert ingestion_response.json()["dataset"] == "upbit_krw_btc_daily"


def test_research_bars_route_returns_explicit_error_for_missing_dataset(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, _runtime = build_seeded_runtime(tmp_path)
    client = TestClient(create_app(config=config_path))

    response = client.get("/api/research/datasets/unknown_dataset/bars")

    assert response.status_code == 404
    assert response.json()["code"] == "dataset_not_found"
