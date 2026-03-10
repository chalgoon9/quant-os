from __future__ import annotations

from fastapi import APIRouter

from quant_os.api.schemas import StrategyCatalogItemResponse, StrategyCatalogResponse
from quant_os.strategy import load_strategy_specs


router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.get("", response_model=StrategyCatalogResponse)
def list_strategies() -> StrategyCatalogResponse:
    specs = load_strategy_specs()
    return StrategyCatalogResponse(
        items=[
            StrategyCatalogItemResponse(
                strategy_id=spec.strategy_id,
                kind=spec.kind,
                version=spec.version,
                description=spec.description,
                dataset_default=spec.dataset_default,
                tags=list(spec.tags),
            )
            for spec in specs.values()
        ]
    )
