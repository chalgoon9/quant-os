from __future__ import annotations

from fastapi import APIRouter, Depends

from quant_os.api.deps import get_runtime
from quant_os.api.errors import ApiError
from quant_os.api.schemas import DailyReportResponse, daily_report_from_domain
from quant_os.services.wiring import AppRuntime


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily/latest", response_model=DailyReportResponse)
def get_latest_daily_report(runtime: AppRuntime = Depends(get_runtime)) -> DailyReportResponse:
    try:
        snapshot = runtime.operational_store.latest_pnl_snapshot()
        reconciliation = runtime.operational_store.latest_reconciliation_result()
    except KeyError as exc:
        raise ApiError(
            status_code=404,
            code="daily_report_unavailable",
            message="daily report is unavailable until pnl and reconciliation snapshots exist",
        ) from exc
    report = runtime.report_generator.generate(
        as_of=snapshot.as_of,
        snapshot=snapshot,
        reconciliation=reconciliation,
        kill_switch_events=tuple(runtime.operational_store.active_kill_switch_events()),
    )
    return daily_report_from_domain(report)

