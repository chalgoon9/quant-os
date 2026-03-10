from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from quant_os.api.deps import get_system
from quant_os.api.errors import ApiError
from quant_os.api.schemas import (
    BacktestCompareRequest,
    BacktestCompareResponse,
    BacktestDetailResponse,
    BacktestRunListItemResponse,
    BacktestRunListResponse,
    backtest_detail_from_domain,
    backtest_summary_from_domain,
)
from quant_os.backtest.results import BacktestArtifactStore
from quant_os.domain.models import SystemConfig
from quant_os.db.store import OperationalStore


router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("/latest", response_model=BacktestDetailResponse)
def get_latest_backtest(system: SystemConfig = Depends(get_system)) -> BacktestDetailResponse:
    store = BacktestArtifactStore(system.storage.artifacts_root)
    try:
        result = store.latest()
    except FileNotFoundError as exc:
        raise ApiError(
            status_code=404,
            code="backtest_not_found",
            message="backtest result is unavailable until run-backtest has been executed",
        ) from exc
    return backtest_detail_from_domain(result)


@router.get("/runs", response_model=BacktestRunListResponse)
def list_backtest_runs(
    limit: int = Query(default=20, ge=1, le=200),
    strategy_id: str | None = Query(default=None),
    dataset: str | None = Query(default=None),
    profile_id: str | None = Query(default=None),
    system: SystemConfig = Depends(get_system),
) -> BacktestRunListResponse:
    store = OperationalStore(system.storage.operational_db_url)
    runs = store.list_strategy_runs(
        limit=limit,
        strategy_id=strategy_id,
        dataset=dataset,
        profile_id=profile_id,
        mode="backtest",
    )
    items = []
    for run in runs:
        payload = run.config_payload or {}
        items.append(
            BacktestRunListItemResponse(
                run_id=run.strategy_run_id,
                strategy_id=run.strategy_id,
                strategy_name=run.strategy_name,
                strategy_kind=run.strategy_kind,
                strategy_version=run.strategy_version,
                dataset=run.dataset,
                profile_id=run.profile_id,
                status=run.status.value,
                started_at=run.started_at.isoformat(),
                finished_at=run.finished_at.isoformat() if run.finished_at is not None else None,
                final_nav=str(payload["final_nav"]) if payload.get("final_nav") is not None else None,
                total_return=str(payload["total_return"]) if payload.get("total_return") is not None else None,
                max_drawdown=str(payload["max_drawdown"]) if payload.get("max_drawdown") is not None else None,
                trade_count=int(payload["trade_count"]) if payload.get("trade_count") is not None else None,
            )
        )
    return BacktestRunListResponse(items=items)


@router.get("/runs/{run_id}", response_model=BacktestDetailResponse)
def get_backtest_run_detail(run_id: str, system: SystemConfig = Depends(get_system)) -> BacktestDetailResponse:
    metadata_store = OperationalStore(system.storage.operational_db_url)
    artifact_store = BacktestArtifactStore(system.storage.artifacts_root)
    try:
        run = metadata_store.get_strategy_run(run_id)
    except KeyError as exc:
        raise ApiError(status_code=404, code="backtest_run_not_found", message=f"backtest run not found: {run_id}") from exc
    try:
        result = artifact_store.load_path(run.artifact_path) if run.artifact_path else artifact_store.load(run_id)
    except FileNotFoundError as exc:
        raise ApiError(
            status_code=404,
            code="backtest_artifact_not_found",
            message=f"backtest artifact not found for run: {run_id}",
        ) from exc
    return backtest_detail_from_domain(result)


@router.post("/compare", response_model=BacktestCompareResponse)
def compare_backtest_runs(
    payload: BacktestCompareRequest,
    system: SystemConfig = Depends(get_system),
) -> BacktestCompareResponse:
    artifact_store = BacktestArtifactStore(system.storage.artifacts_root)
    items = []
    for run_id in payload.run_ids:
        try:
            result = artifact_store.load(run_id)
        except FileNotFoundError as exc:
            raise ApiError(
                status_code=404,
                code="backtest_run_not_found",
                message=f"backtest run not found: {run_id}",
            ) from exc
        items.append(backtest_summary_from_domain(result))
    return BacktestCompareResponse(items=items)
