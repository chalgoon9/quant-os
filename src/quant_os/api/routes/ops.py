from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from quant_os.api.deps import get_runtime
from quant_os.api.errors import ApiError
from quant_os.api.schemas import (
    KillSwitchEventsResponse,
    OpsSummaryResponse,
    OrderDetailResponse,
    OrdersResponse,
    ReconciliationResponse,
    fill_event_from_domain,
    kill_switch_event_from_domain,
    order_event_from_domain,
    order_list_item_from_domain,
    order_projection_from_domain,
    reconciliation_from_domain,
)
from quant_os.services.wiring import AppRuntime
from quant_os.domain.types import quantize


router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/summary", response_model=OpsSummaryResponse)
def get_ops_summary(runtime: AppRuntime = Depends(get_runtime)) -> OpsSummaryResponse:
    try:
        snapshot = runtime.operational_store.latest_pnl_snapshot()
        reconciliation = runtime.operational_store.latest_reconciliation_result()
    except KeyError as exc:
        raise ApiError(
            status_code=404,
            code="ops_summary_unavailable",
            message="ops summary is unavailable until pnl and reconciliation snapshots exist",
        ) from exc
    active_events = runtime.operational_store.active_kill_switch_events()
    return OpsSummaryResponse(
        nav=format(quantize(snapshot.nav, "0.0000"), "f"),
        cash_balance=format(quantize(snapshot.cash_balance, "0.0000"), "f"),
        realized_pnl=format(quantize(snapshot.realized_pnl, "0.0000"), "f"),
        unrealized_pnl=format(quantize(snapshot.unrealized_pnl, "0.0000"), "f"),
        total_pnl=format(quantize(snapshot.total_pnl, "0.0000"), "f"),
        reconciliation_status=reconciliation.status.value,
        reconciliation_summary=reconciliation.summary,
        active_kill_switch_reasons=[event.reason.value for event in active_events],
    )


@router.get("/orders", response_model=OrdersResponse)
def list_orders(
    limit: int = Query(default=100, ge=1, le=500),
    runtime: AppRuntime = Depends(get_runtime),
) -> OrdersResponse:
    items = [order_list_item_from_domain(projection) for projection in runtime.operational_store.list_recent_orders(limit)]
    return OrdersResponse(items=items)


@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
def get_order_detail(order_id: str, runtime: AppRuntime = Depends(get_runtime)) -> OrderDetailResponse:
    try:
        projection = runtime.operational_store.get_order_projection(order_id)
    except KeyError as exc:
        raise ApiError(status_code=404, code="order_not_found", message=f"order not found: {order_id}") from exc
    return OrderDetailResponse(
        projection=order_projection_from_domain(projection),
        events=[order_event_from_domain(item) for item in runtime.operational_store.list_order_events(order_id)],
        fills=[fill_event_from_domain(item) for item in runtime.operational_store.list_fills(order_id)],
    )


@router.get("/reconciliation/latest", response_model=ReconciliationResponse)
def get_latest_reconciliation(runtime: AppRuntime = Depends(get_runtime)) -> ReconciliationResponse:
    try:
        result = runtime.operational_store.latest_reconciliation_result()
    except KeyError as exc:
        raise ApiError(
            status_code=404,
            code="reconciliation_not_found",
            message="reconciliation result not found",
        ) from exc
    return reconciliation_from_domain(result)


@router.get("/kill-switch/active", response_model=KillSwitchEventsResponse)
def get_active_kill_switch_events(runtime: AppRuntime = Depends(get_runtime)) -> KillSwitchEventsResponse:
    return KillSwitchEventsResponse(
        items=[kill_switch_event_from_domain(event) for event in runtime.operational_store.active_kill_switch_events()]
    )
