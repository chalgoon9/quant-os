from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quant_os.domain.models import MarketBar
from quant_os.normalization import normalize_upbit_daily_payload
from quant_os.research_store.store import ResearchStore
from quant_os.data_ingestion.archive import IngestionArtifactStore

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

    def fetch_daily_candle_payload(
        self,
        market: str,
        *,
        count: int = 200,
        to: datetime | None = None,
    ) -> list[dict[str, object]]:
        if count <= 0:
            raise ValueError("count must be positive")
        params = {
            "market": market.strip().upper(),
            "count": str(count),
        }
        if to is not None:
            params["to"] = to.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        return self._transport("/candles/days", params)

    def fetch_daily_bars(
        self,
        market: str,
        *,
        count: int = 200,
        to: datetime | None = None,
    ) -> list[MarketBar]:
        fetched_at = datetime.now(tz=timezone.utc)
        request_params = {
            "market": market.strip().upper(),
            "count": str(count),
        }
        if to is not None:
            request_params["to"] = to.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        payload = self.fetch_daily_candle_payload(market, count=count, to=to)
        normalized = normalize_upbit_daily_payload(
            payload,
            expected_symbol=market.strip().upper(),
            fetched_at=fetched_at,
            request_params=request_params,
        )
        if normalized.quarantine_records:
            raise ValueError(
                f"invalid Upbit payload for {market.strip().upper()}: "
                f"{normalized.report.invalid_records} record(s) quarantined"
            )
        return list(normalized.bars)


def ingest_upbit_daily_bars(
    *,
    client: UpbitQuotationClient,
    research_store: ResearchStore,
    market: str,
    count: int,
    dataset: str | None = None,
    to: datetime | None = None,
    data_root: Path | None = None,
    artifacts_root: Path | None = None,
) -> Path:
    resolved_dataset = dataset or default_upbit_dataset_name(market)
    normalized_data_root = research_store.root.parent if research_store.root.name == "normalized" else research_store.root
    artifact_store = IngestionArtifactStore(
        data_root=data_root or normalized_data_root,
        artifacts_root=artifacts_root or (normalized_data_root / "artifacts"),
    )
    fetched_at = datetime.now(tz=timezone.utc)
    request_params = {
        "market": market.strip().upper(),
        "count": str(count),
    }
    if to is not None:
        request_params["to"] = to.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    payload, bars = _fetch_payload_or_bars(client, market=market, count=count, to=to)
    raw_archive_path = artifact_store.save_raw_payload(
        source="upbit_quotation",
        dataset=resolved_dataset,
        fetched_at=fetched_at,
        request_params=request_params,
        payload=payload,
    )
    normalized = normalize_upbit_daily_payload(
        payload,
        expected_symbol=market.strip().upper(),
        fetched_at=fetched_at,
        request_params=request_params,
    ) if payload else None

    if normalized is not None:
        validation_report_path = artifact_store.save_validation_report(
            source="upbit_quotation",
            dataset=resolved_dataset,
            fetched_at=fetched_at,
            raw_archive_path=raw_archive_path,
            report=normalized.report,
        )
        quarantine_path = artifact_store.save_quarantine_records(
            source="upbit_quotation",
            dataset=resolved_dataset,
            fetched_at=fetched_at,
            issues=normalized.quarantine_records,
        )
        if normalized.quarantine_records:
            raise ValueError(
                "ingestion aborted because payload validation failed; "
                f"raw={raw_archive_path} report={validation_report_path} quarantine={quarantine_path}"
            )
        bars = list(normalized.bars)

    if not bars:
        raise ValueError(f"no bars returned for market={market}")
    return research_store.write_bars(resolved_dataset, bars)


def default_upbit_dataset_name(market: str) -> str:
    normalized = market.strip().upper().replace("-", "_").lower()
    return f"upbit_{normalized}_daily"

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


def _fetch_payload_or_bars(
    client: UpbitQuotationClient,
    *,
    market: str,
    count: int,
    to: datetime | None,
) -> tuple[list[dict[str, object]], list[MarketBar]]:
    if hasattr(client, "fetch_daily_candle_payload"):
        payload = client.fetch_daily_candle_payload(market, count=count, to=to)
        return payload, []
    bars = client.fetch_daily_bars(market, count=count, to=to)
    payload = [
        {
            "market": bar.symbol,
            "candle_date_time_utc": bar.timestamp.astimezone(timezone.utc).replace(tzinfo=None).isoformat(),
            "opening_price": str(bar.open),
            "high_price": str(bar.high),
            "low_price": str(bar.low),
            "trade_price": str(bar.close),
            "candle_acc_trade_volume": str(bar.volume),
            "raw_payload_unavailable": True,
        }
        for bar in bars
    ]
    return payload, bars
