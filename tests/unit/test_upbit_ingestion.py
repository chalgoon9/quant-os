from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner


def test_upbit_client_normalizes_markets_and_daily_bars() -> None:
    from quant_os.data_ingestion.upbit import UpbitQuotationClient

    calls: list[tuple[str, dict[str, str]]] = []

    def fake_transport(path: str, params: dict[str, str]) -> list[dict[str, object]]:
        calls.append((path, params))
        if path == "/market/all":
            return [
                {"market": "KRW-BTC"},
                {"market": "BTC-ETH"},
                {"market": "KRW-XRP"},
            ]
        if path == "/candles/days":
            return [
                {
                    "market": "KRW-BTC",
                    "candle_date_time_utc": "2026-03-09T00:00:00",
                    "opening_price": 150000000,
                    "high_price": 151000000,
                    "low_price": 149000000,
                    "trade_price": 150500000,
                    "candle_acc_trade_volume": 123.45,
                },
                {
                    "market": "KRW-BTC",
                    "candle_date_time_utc": "2026-03-08T00:00:00",
                    "opening_price": 148000000,
                    "high_price": 150000000,
                    "low_price": 147500000,
                    "trade_price": 149500000,
                    "candle_acc_trade_volume": 111.11,
                },
            ]
        raise AssertionError(f"unexpected request: {path} {params}")

    client = UpbitQuotationClient(transport=fake_transport)

    assert client.list_markets(fiat="KRW") == ["KRW-BTC", "KRW-XRP"]

    bars = client.fetch_daily_bars("KRW-BTC", count=2)

    assert calls[0] == ("/market/all", {"is_details": "false"})
    assert calls[1] == ("/candles/days", {"market": "KRW-BTC", "count": "2"})
    assert [bar.symbol for bar in bars] == ["KRW-BTC", "KRW-BTC"]
    assert [bar.timestamp for bar in bars] == [
        datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
    ]
    assert str(bars[-1].close) == "150500000"


def test_ingest_upbit_daily_bars_writes_research_store(tmp_path: Path) -> None:
    from quant_os.data_ingestion.upbit import UpbitQuotationClient, ingest_upbit_daily_bars
    from quant_os.research_store.store import ResearchStore

    def fake_transport(path: str, params: dict[str, str]) -> list[dict[str, object]]:
        assert path == "/candles/days"
        return [
            {
                "market": "KRW-BTC",
                "candle_date_time_utc": "2026-03-09T00:00:00",
                "opening_price": 150000000,
                "high_price": 151000000,
                "low_price": 149000000,
                "trade_price": 150500000,
                "candle_acc_trade_volume": 123.45,
            },
            {
                "market": "KRW-BTC",
                "candle_date_time_utc": "2026-03-08T00:00:00",
                "opening_price": 148000000,
                "high_price": 150000000,
                "low_price": 147500000,
                "trade_price": 149500000,
                "candle_acc_trade_volume": 111.11,
            },
        ]

    store = ResearchStore(root=tmp_path / "data", duckdb_path=tmp_path / "research.duckdb")
    client = UpbitQuotationClient(transport=fake_transport)

    path = ingest_upbit_daily_bars(
        client=client,
        research_store=store,
        market="KRW-BTC",
        count=2,
        dataset="upbit_krw_btc_daily",
    )

    loaded = store.load_bars("upbit_krw_btc_daily", symbol="KRW-BTC")

    assert path.exists() is True
    assert len(loaded) == 2
    assert loaded[0].symbol == "KRW-BTC"
    assert loaded[-1].close > loaded[0].close


def test_cli_ingest_upbit_daily_writes_dataset(tmp_path: Path, monkeypatch) -> None:
    import importlib
    import yaml

    from quant_os.cli.main import app

    config_path = tmp_path / "base.yaml"
    config_payload = {
        "app": {"system_name": "quant-os-mvp"},
        "trading": {"mode": "paper", "base_currency": "KRW", "venue": "upbit"},
        "strategy": {
            "name": "daily_momentum",
            "universe": ["KRW-BTC"],
            "rebalance_calendar": "daily",
            "max_names": 1,
            "target_gross_exposure_limit": "0.95",
            "fast_lookback": 20,
            "slow_lookback": 60,
            "trend_lookback": 40,
        },
        "risk": {
            "max_single_name_weight": "0.20",
            "min_cash_buffer": "0.05",
            "daily_loss_limit": "0.03",
            "max_turnover": "0.25",
            "fail_closed": True,
        },
        "research": {
            "duckdb_path": "./research/quant_os.duckdb",
            "market_data_dataset": "krx_etf_daily",
        },
        "intent": {
            "lot_size": "1",
            "min_trade_notional": "1000",
            "default_order_type": "market",
            "time_in_force": "day",
        },
        "backtest": {"initial_cash": "10000000", "commission_bps": "5", "slippage_bps": "5"},
        "controls": {
            "reconciliation_cash_tolerance": "1",
            "reconciliation_position_tolerance": "0.001",
            "stale_market_data_seconds": 86400,
        },
        "storage": {
            "operational_db_url": f"sqlite:///{tmp_path / 'var' / 'quant_os.db'}",
            "data_root": "./data",
            "research_root": "./research",
            "artifacts_root": "./data/artifacts",
        },
    }
    config_path.write_text(yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8")

    class FakeClient:
        def fetch_daily_bars(self, market: str, count: int, to: datetime | None = None):
            from quant_os.domain.models import MarketBar

            assert market == "KRW-BTC"
            assert count == 2
            return [
                MarketBar(
                    symbol="KRW-BTC",
                    timestamp=datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
                    open=148000000,
                    high=150000000,
                    low=147500000,
                    close=149500000,
                    volume=111.11,
                ),
                MarketBar(
                    symbol="KRW-BTC",
                    timestamp=datetime(2026, 3, 9, 0, 0, tzinfo=timezone.utc),
                    open=150000000,
                    high=151000000,
                    low=149000000,
                    close=150500000,
                    volume=123.45,
                ),
            ]

    cli_main = importlib.import_module("quant_os.cli.main")

    monkeypatch.setattr(cli_main, "UpbitQuotationClient", FakeClient)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "ingest-upbit-daily",
            "--config",
            str(config_path),
            "--market",
            "KRW-BTC",
            "--count",
            "2",
        ],
    )

    dataset_path = tmp_path / "data" / "normalized" / "upbit_krw_btc_daily" / "bars.parquet"

    assert result.exit_code == 0
    assert "dataset=upbit_krw_btc_daily" in result.stdout
    assert dataset_path.exists() is True
