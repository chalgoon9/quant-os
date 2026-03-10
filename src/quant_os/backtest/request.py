from __future__ import annotations

from datetime import date

from pydantic import Field

from quant_os.domain.models import ImmutableModel


class BacktestRequest(ImmutableModel):
    strategy_id: str
    dataset: str
    profile_id: str
    date_from: date | None = None
    date_to: date | None = None
    notes: str | None = None
    tags: tuple[str, ...] = ()
