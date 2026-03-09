from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quant_os.domain.models import MarketBar
from quant_os.domain.types import to_decimal
from quant_os.research_store.store import ResearchStore

Transport = Callable[[str, dict[str, str]], list[dict[str, object]]]


class UpbitQuotationClient:
    def __init__(
        self,
        *,
        transport: Transport | None = None,
        base_url: str = "https://api.upbit.com/v1",
        timeout_seconds: float = 10.0,
    ) -> None:
        self._transport = transport or _build_http_transport(base_url=base_url, timeout_seconds=timeout_seconds)

    def list_markets(self, *, fiat: str | None = None) -> list[str]:
        payload = self._transport("/market/all", {"is_details": "false"})
        markets = sorted(str(item["market"]) for item in payload)
        if fiat is None:
            return markets
        prefix = f"{fiat.upper()}-"
        return [market for market in markets if market.startswith(prefix)]

    def fetch_daily_bars(
        self,
        market: str,
        *,
        count: int = 200,
        to: datetime | None = None,
    ) -> list[MarketBar]:
        if count <= 0:
            raise ValueError("count must be positive")
        params = {
            "market": market.strip().upper(),
            "count": str(count),
        }
        if to is not None:
            params["to"] = to.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        payload = self._transport("/candles/days", params)
        bars = [_to_market_bar(item) for item in payload]
        return sorted(bars, key=lambda bar: bar.timestamp)


def ingest_upbit_daily_bars(
    *,
    client: UpbitQuotationClient,
    research_store: ResearchStore,
    market: str,
    count: int,
    dataset: str | None = None,
    to: datetime | None = None,
) -> Path:
    bars = client.fetch_daily_bars(market, count=count, to=to)
    if not bars:
        raise ValueError(f"no bars returned for market={market}")
    resolved_dataset = dataset or default_upbit_dataset_name(market)
    return research_store.write_bars(resolved_dataset, bars)


def default_upbit_dataset_name(market: str) -> str:
    normalized = market.strip().upper().replace("-", "_").lower()
    return f"upbit_{normalized}_daily"


def _to_market_bar(payload: dict[str, object]) -> MarketBar:
    return MarketBar(
        symbol=str(payload["market"]),
        timestamp=_parse_upbit_datetime(str(payload["candle_date_time_utc"])),
        open=to_decimal(payload["opening_price"]),
        high=to_decimal(payload["high_price"]),
        low=to_decimal(payload["low_price"]),
        close=to_decimal(payload["trade_price"]),
        volume=to_decimal(payload["candle_acc_trade_volume"]),
    )


def _parse_upbit_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _build_http_transport(*, base_url: str, timeout_seconds: float) -> Transport:
    def transport(path: str, params: dict[str, str]) -> list[dict[str, object]]:
        query = urlencode(params)
        request = Request(
            f"{base_url}{path}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": "quant-os/0.1.0",
            },
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            payload: Any = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"unexpected Upbit payload type for {path}: {type(payload).__name__}")
        return payload

    return transport
