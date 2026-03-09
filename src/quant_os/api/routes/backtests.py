from __future__ import annotations

from fastapi import APIRouter, Depends

from quant_os.api.deps import get_system
from quant_os.api.errors import ApiError
from quant_os.api.schemas import BacktestDetailResponse, backtest_detail_from_domain
from quant_os.backtest.results import BacktestArtifactStore
from quant_os.domain.models import SystemConfig


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
