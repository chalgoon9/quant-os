from __future__ import annotations

from typing import NewType
from uuid import uuid4


StrategyRunId = NewType("StrategyRunId", str)
IntentId = NewType("IntentId", str)
OrderId = NewType("OrderId", str)
OrderEventId = NewType("OrderEventId", str)
FillId = NewType("FillId", str)
LedgerEntryId = NewType("LedgerEntryId", str)
SnapshotId = NewType("SnapshotId", str)
KillSwitchEventId = NewType("KillSwitchEventId", str)
ReconciliationId = NewType("ReconciliationId", str)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
