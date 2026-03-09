from __future__ import annotations

from fastapi import APIRouter, Depends

from quant_os.api.deps import get_runtime, get_system
from quant_os.api.schemas import DoctorResponse, RuntimeResponse
from quant_os.db.schema import REQUIRED_TABLES
from quant_os.domain.models import SystemConfig
from quant_os.services.wiring import AppRuntime


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/runtime", response_model=RuntimeResponse)
def get_runtime_summary(
    system=Depends(get_system),
    runtime=Depends(get_runtime),
) -> RuntimeResponse:
    return RuntimeResponse(
        mode=system.mode.value,
        venue=system.venue,
        strategy=system.strategy.name,
        execution_adapter=type(runtime.execution_adapter).__name__,
        base_currency=system.base_currency,
        research_dataset=system.research.market_data_dataset,
    )


@router.get("/doctor", response_model=DoctorResponse)
def get_doctor_summary(
    system: SystemConfig = Depends(get_system),
    runtime: AppRuntime = Depends(get_runtime),
) -> DoctorResponse:
    return DoctorResponse(
        system_name=system.system_name,
        mode=system.mode.value,
        strategy=system.strategy.name,
        research_dataset=system.research.market_data_dataset,
        intent_lot_size=format(system.intent.lot_size, "f"),
        execution_adapter=type(runtime.execution_adapter).__name__,
        required_tables=sorted(REQUIRED_TABLES),
    )

