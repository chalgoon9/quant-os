from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal


def test_research_store_writes_parquet_and_queries_latest_bar(tmp_path) -> None:
    from quant_os.domain.models import MarketBar
    from quant_os.research_store.store import ResearchStore

    store = ResearchStore(root=tmp_path / "data", duckdb_path=tmp_path / "research.duckdb")
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars = [
        MarketBar(
            symbol="AAA",
            timestamp=start + timedelta(days=index),
            open=Decimal("100") + index,
            high=Decimal("101") + index,
            low=Decimal("99") + index,
            close=Decimal("100") + index,
            volume=Decimal("1000"),
        )
        for index in range(3)
    ]

    dataset_path = store.write_bars("krx_etf_daily", bars)
    latest = store.latest_bar("krx_etf_daily", "AAA")

    assert dataset_path.exists()
    assert latest.close == Decimal("102")
    assert store.count_rows("krx_etf_daily") == 3
