from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from quant_os.api.deps import get_runtime
from quant_os.api.errors import ApiError
from quant_os.api.schemas import (
    DatasetBarsResponse,
    DatasetListResponse,
    DatasetSummaryResponse,
    UpbitDailyIngestionRequest,
    UpbitDailyIngestionResponse,
    market_bar_from_domain,
)
from quant_os.data_ingestion.upbit import UpbitQuotationClient, default_upbit_dataset_name, ingest_upbit_daily_bars
from quant_os.services.wiring import AppRuntime


router = APIRouter(prefix="/research", tags=["research"])


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(runtime: AppRuntime = Depends(get_runtime)) -> DatasetListResponse:
    items: list[DatasetSummaryResponse] = []
    for dataset in runtime.research_store.list_datasets():
        latest_timestamp = runtime.research_store.latest_timestamp(dataset)
        items.append(
            DatasetSummaryResponse(
                dataset=dataset,
                row_count=runtime.research_store.count_rows(dataset),
                latest_timestamp=latest_timestamp.isoformat() if latest_timestamp is not None else None,
            )
        )
    return DatasetListResponse(items=items)


@router.get("/datasets/{dataset}/bars", response_model=DatasetBarsResponse)
def get_dataset_bars(
    dataset: str,
    symbol: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=500),
    runtime: AppRuntime = Depends(get_runtime),
) -> DatasetBarsResponse:
    try:
        bars = runtime.research_store.sample_bars(dataset, symbol=symbol, limit=limit)
    except FileNotFoundError as exc:
        raise ApiError(status_code=404, code="dataset_not_found", message=f"dataset not found: {dataset}") from exc
    return DatasetBarsResponse(
        dataset=dataset,
        symbol=symbol,
        items=[market_bar_from_domain(bar) for bar in bars],
    )


@router.post("/ingestion/upbit/daily", response_model=UpbitDailyIngestionResponse)
def ingest_upbit_daily(
    payload: UpbitDailyIngestionRequest,
    runtime: AppRuntime = Depends(get_runtime),
) -> UpbitDailyIngestionResponse:
    market = payload.market.strip().upper()
    dataset = payload.dataset or default_upbit_dataset_name(market)
    path = ingest_upbit_daily_bars(
        client=UpbitQuotationClient(),
        research_store=runtime.research_store,
        market=market,
        count=payload.count,
        dataset=dataset,
    )
    return UpbitDailyIngestionResponse(
        source="upbit_quotation",
        market=market,
        dataset=dataset,
        path=str(path),
    )
