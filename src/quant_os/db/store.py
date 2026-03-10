from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from quant_os.db.base import Base
from quant_os.db.schema import (
    CashLedgerRecord,
    FillRecord,
    KillSwitchEventRecord,
    OrderEventRecord,
    OrderRecord,
    PnlSnapshotRecord,
    PositionSnapshotRecord,
    ReconciliationLogRecord,
    StrategyRunRecord,
)
from quant_os.domain.enums import StrategyRunStatus, TradingMode
from quant_os.domain.models import (
    CashLedgerEntry,
    FillEvent,
    KillSwitchEvent,
    LedgerSnapshot,
    OrderEvent,
    OrderProjection,
    ReconciliationIssue,
    ReconciliationResult,
    StrategyRun,
)
from quant_os.domain.types import ZERO, quantize


class OperationalStore:
    def __init__(self, url: str) -> None:
        self.url = url
        _ensure_sqlite_parent(url)
        self.engine = create_engine(url, future=True)
        self._session_factory = sessionmaker(bind=self.engine, future=True, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def start_strategy_run(self, run: StrategyRun) -> None:
        with self._session() as session:
            record = session.get(StrategyRunRecord, run.strategy_run_id)
            if record is None:
                record = StrategyRunRecord(id=run.strategy_run_id)
                session.add(record)
            record.strategy_name = run.strategy_name
            record.mode = run.mode
            record.status = run.status.value
            record.strategy_id = run.strategy_id
            record.strategy_kind = run.strategy_kind
            record.strategy_version = run.strategy_version
            record.dataset = run.dataset
            record.profile_id = run.profile_id
            record.artifact_path = run.artifact_path
            record.config_fingerprint = run.config_fingerprint
            record.tags_json = list(run.tags_json) if run.tags_json else None
            record.notes = run.notes
            record.started_at = run.started_at
            record.finished_at = run.finished_at
            record.config_payload = run.config_payload

    def finish_strategy_run(
        self,
        strategy_run_id: str,
        *,
        status: StrategyRunStatus,
        finished_at,
        config_payload: dict[str, object] | None = None,
        artifact_path: str | None = None,
    ) -> None:
        with self._session() as session:
            record = session.get(StrategyRunRecord, strategy_run_id)
            if record is None:
                raise KeyError(f"unknown strategy run: {strategy_run_id}")
            record.status = status.value
            record.finished_at = finished_at
            if artifact_path is not None:
                record.artifact_path = artifact_path
            if config_payload is not None:
                record.config_payload = config_payload

    def get_strategy_run(self, strategy_run_id: str) -> StrategyRun:
        with self._session() as session:
            record = session.get(StrategyRunRecord, strategy_run_id)
            if record is None:
                raise KeyError(f"unknown strategy run: {strategy_run_id}")
        return _strategy_run_from_record(record)

    def list_strategy_runs(
        self,
        limit: int = 50,
        *,
        strategy_id: str | None = None,
        dataset: str | None = None,
        profile_id: str | None = None,
        mode: str | None = None,
    ) -> list[StrategyRun]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._session() as session:
            statement = select(StrategyRunRecord)
            if strategy_id is not None:
                statement = statement.where(StrategyRunRecord.strategy_id == strategy_id)
            if dataset is not None:
                statement = statement.where(StrategyRunRecord.dataset == dataset)
            if profile_id is not None:
                statement = statement.where(StrategyRunRecord.profile_id == profile_id)
            if mode is not None:
                statement = statement.where(StrategyRunRecord.mode == mode)
            records = session.scalars(
                statement.order_by(StrategyRunRecord.started_at.desc()).limit(limit)
            ).all()
        return [_strategy_run_from_record(record) for record in records]

    def append_order_event(self, event: OrderEvent) -> None:
        with self._session() as session:
            self._ensure_strategy_run(session, event.strategy_run_id)
            session.add(
                OrderEventRecord(
                    id=event.event_id,
                    order_id=event.order_id,
                    intent_id=event.intent_id,
                    strategy_run_id=event.strategy_run_id,
                    symbol=event.symbol,
                    status=event.status.value,
                    event_type=event.event_type.value,
                    occurred_at=event.occurred_at,
                    broker_order_id=event.broker_order_id,
                    reason=event.reason,
                    raw_payload=event.raw_payload,
                    metadata_json=None,
                )
            )

    def upsert_order_projection(self, projection: OrderProjection, *, projection_source_event_id: str | None = None) -> None:
        with self._session() as session:
            self._ensure_strategy_run(session, projection.strategy_run_id)
            record = session.get(OrderRecord, projection.order_id)
            if record is None:
                record = OrderRecord(id=projection.order_id)
                session.add(record)
            record.intent_id = projection.intent_id
            record.strategy_run_id = projection.strategy_run_id
            record.symbol = projection.symbol
            record.side = projection.side.value
            record.order_type = projection.order_type.value
            record.time_in_force = projection.time_in_force.value
            record.status = projection.status.value
            record.quantity = quantize(projection.quantity, "0.0000")
            record.filled_quantity = quantize(projection.filled_quantity, "0.0000")
            record.limit_price = None
            record.broker_order_id = projection.broker_order_id
            record.created_at = projection.created_at
            record.updated_at = projection.updated_at
            record.last_event_at = projection.last_event_at
            record.projection_source_event_id = projection_source_event_id

    def append_fill(self, fill: FillEvent) -> None:
        with self._session() as session:
            self._ensure_strategy_run(session, fill.strategy_run_id)
            session.add(
                FillRecord(
                    id=fill.fill_id,
                    order_id=fill.order_id,
                    intent_id=fill.intent_id,
                    strategy_run_id=fill.strategy_run_id,
                    symbol=fill.symbol,
                    side=fill.side.value,
                    quantity=quantize(fill.quantity, "0.0000"),
                    price=quantize(fill.price, "0.0000"),
                    gross_amount=quantize(fill.quantity * fill.price, "0.0000"),
                    fee=quantize(fill.fee, "0.0000"),
                    tax=quantize(fill.tax, "0.0000"),
                    occurred_at=fill.occurred_at,
                    broker_fill_id=fill.broker_fill_id,
                    raw_payload=fill.raw_payload,
                )
            )

    def append_cash_ledger_entry(self, entry: CashLedgerEntry) -> None:
        with self._session() as session:
            session.add(
                CashLedgerRecord(
                    id=entry.entry_id,
                    occurred_at=entry.occurred_at,
                    currency=entry.currency,
                    entry_type=entry.reference_type,
                    amount=quantize(entry.amount, "0.0000"),
                    balance_after=quantize(entry.balance_after, "0.0000"),
                    reference_type=entry.reference_type,
                    reference_id=entry.reference_id,
                    notes=entry.notes,
                )
            )

    def append_ledger_snapshot(self, snapshot: LedgerSnapshot, *, source: str) -> None:
        gross_exposure = ZERO
        net_exposure = ZERO
        for position in snapshot.positions.values():
            if position.market_price is None or snapshot.nav == ZERO:
                continue
            market_value = quantize(position.quantity * position.market_price, "0.0000")
            weight = quantize(market_value / snapshot.nav, "0.000000")
            gross_exposure += abs(weight)
            net_exposure += weight

        with self._session() as session:
            session.add(
                PnlSnapshotRecord(
                    id=f"pnl_{snapshot.as_of.isoformat()}",
                    snapshot_at=snapshot.as_of,
                    realized_pnl=quantize(snapshot.realized_pnl, "0.0000"),
                    unrealized_pnl=quantize(snapshot.unrealized_pnl, "0.0000"),
                    total_pnl=quantize(snapshot.total_pnl, "0.0000"),
                    nav=quantize(snapshot.nav, "0.0000"),
                    gross_exposure=quantize(gross_exposure, "0.000000"),
                    net_exposure=quantize(net_exposure, "0.000000"),
                )
            )
            for index, position in enumerate(snapshot.positions.values(), start=1):
                market_value = None
                unrealized_pnl = None
                if position.market_price is not None:
                    market_value = quantize(position.quantity * position.market_price, "0.0000")
                    unrealized_pnl = quantize(market_value - (position.quantity * position.average_cost), "0.0000")
                session.add(
                    PositionSnapshotRecord(
                        id=f"pos_{snapshot.as_of.isoformat()}_{index}_{position.symbol}",
                        snapshot_at=snapshot.as_of,
                        symbol=position.symbol,
                        quantity=quantize(position.quantity, "0.0000"),
                        average_cost=quantize(position.average_cost, "0.0000"),
                        market_price=quantize(position.market_price, "0.0000") if position.market_price is not None else None,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl,
                        source=source,
                    )
                )

    def append_reconciliation_result(self, result: ReconciliationResult) -> None:
        with self._session() as session:
            session.add(
                ReconciliationLogRecord(
                    id=result.reconciliation_id,
                    occurred_at=result.occurred_at,
                    status=result.status.value,
                    mismatch_count=result.mismatch_count,
                    requires_manual_intervention=result.requires_manual_intervention,
                    summary=result.summary,
                    details={
                        "issues": [
                            {
                                "code": issue.code,
                                "message": issue.message,
                                "severity": issue.severity,
                                "recommended_action": issue.recommended_action,
                                "details": issue.details,
                            }
                            for issue in result.issues
                        ]
                    },
                )
            )

    def save_kill_switch_event(self, event: KillSwitchEvent) -> None:
        with self._session() as session:
            record = session.get(KillSwitchEventRecord, event.event_id)
            if record is None:
                record = KillSwitchEventRecord(id=event.event_id)
                session.add(record)
            record.triggered_at = event.triggered_at
            record.reason = event.reason.value
            record.is_active = event.is_active
            record.trigger_value = quantize(event.trigger_value, "0.000000") if event.trigger_value is not None else None
            record.threshold_value = quantize(event.threshold_value, "0.000000") if event.threshold_value is not None else None
            record.details = event.details
            record.cleared_at = event.cleared_at

    def get_order_projection(self, order_id: str) -> OrderProjection:
        with self._session() as session:
            record = session.get(OrderRecord, order_id)
            if record is None:
                raise KeyError(f"unknown order: {order_id}")
            return OrderProjection(
                order_id=record.id,
                intent_id=record.intent_id,
                strategy_run_id=record.strategy_run_id,
                symbol=record.symbol,
                side=record.side,
                order_type=record.order_type,
                time_in_force=record.time_in_force,
                quantity=record.quantity,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                filled_quantity=record.filled_quantity,
                broker_order_id=record.broker_order_id,
                last_event_at=record.last_event_at,
            )

    def list_recent_orders(self, limit: int = 100) -> list[OrderProjection]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._session() as session:
            records = session.scalars(
                select(OrderRecord).order_by(OrderRecord.updated_at.desc(), OrderRecord.created_at.desc()).limit(limit)
            ).all()
        return [
            OrderProjection(
                order_id=record.id,
                intent_id=record.intent_id,
                strategy_run_id=record.strategy_run_id,
                symbol=record.symbol,
                side=record.side,
                order_type=record.order_type,
                time_in_force=record.time_in_force,
                quantity=record.quantity,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                filled_quantity=record.filled_quantity,
                broker_order_id=record.broker_order_id,
                last_event_at=record.last_event_at,
            )
            for record in records
        ]

    def list_open_orders(self, limit: int = 100) -> list[OrderProjection]:
        open_statuses = {
            "planned",
            "approved",
            "submitting",
            "acknowledged",
            "working",
            "partially_filled",
            "cancel_requested",
            "reconcile_pending",
            "manual_intervention",
        }
        with self._session() as session:
            records = session.scalars(
                select(OrderRecord)
                .where(OrderRecord.status.in_(open_statuses))
                .order_by(OrderRecord.updated_at.desc(), OrderRecord.created_at.desc())
                .limit(limit)
            ).all()
        return [
            OrderProjection(
                order_id=record.id,
                intent_id=record.intent_id,
                strategy_run_id=record.strategy_run_id,
                symbol=record.symbol,
                side=record.side,
                order_type=record.order_type,
                time_in_force=record.time_in_force,
                quantity=record.quantity,
                status=record.status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                filled_quantity=record.filled_quantity,
                broker_order_id=record.broker_order_id,
                last_event_at=record.last_event_at,
            )
            for record in records
        ]

    def list_order_events(self, order_id: str) -> list[OrderEvent]:
        with self._session() as session:
            records = session.scalars(
                select(OrderEventRecord).where(OrderEventRecord.order_id == order_id).order_by(OrderEventRecord.occurred_at)
            ).all()
        return [
            OrderEvent(
                event_id=record.id,
                order_id=record.order_id,
                intent_id=record.intent_id,
                strategy_run_id=record.strategy_run_id,
                symbol=record.symbol,
                status=record.status,
                event_type=record.event_type,
                occurred_at=record.occurred_at,
                broker_order_id=record.broker_order_id,
                reason=record.reason,
                raw_payload=record.raw_payload,
            )
            for record in records
        ]

    def list_fills(self, order_id: str) -> list[FillEvent]:
        with self._session() as session:
            records = session.scalars(
                select(FillRecord).where(FillRecord.order_id == order_id).order_by(FillRecord.occurred_at)
            ).all()
        return [
            FillEvent(
                fill_id=record.id,
                order_id=record.order_id,
                intent_id=record.intent_id,
                strategy_run_id=record.strategy_run_id,
                symbol=record.symbol,
                side=record.side,
                quantity=record.quantity,
                price=record.price,
                fee=record.fee,
                tax=record.tax,
                occurred_at=record.occurred_at,
                broker_fill_id=record.broker_fill_id,
                raw_payload=record.raw_payload,
            )
            for record in records
        ]

    def list_recent_fills(self, limit: int = 500) -> list[FillEvent]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._session() as session:
            records = session.scalars(
                select(FillRecord).order_by(FillRecord.occurred_at.desc()).limit(limit)
            ).all()
        return [
            FillEvent(
                fill_id=record.id,
                order_id=record.order_id,
                intent_id=record.intent_id,
                strategy_run_id=record.strategy_run_id,
                symbol=record.symbol,
                side=record.side,
                quantity=record.quantity,
                price=record.price,
                fee=record.fee,
                tax=record.tax,
                occurred_at=record.occurred_at,
                broker_fill_id=record.broker_fill_id,
                raw_payload=record.raw_payload,
            )
            for record in reversed(records)
        ]

    def latest_pnl_snapshot(self) -> LedgerSnapshot:
        with self._session() as session:
            pnl = session.scalars(select(PnlSnapshotRecord).order_by(PnlSnapshotRecord.snapshot_at.desc())).first()
            if pnl is None:
                raise KeyError("no pnl snapshot stored")
            position_records = session.scalars(
                select(PositionSnapshotRecord).where(PositionSnapshotRecord.snapshot_at == pnl.snapshot_at)
            ).all()
            latest_cash_entry = session.scalars(
                select(CashLedgerRecord).order_by(CashLedgerRecord.occurred_at.desc())
            ).first()
        return LedgerSnapshot(
            as_of=pnl.snapshot_at,
            base_currency=latest_cash_entry.currency if latest_cash_entry is not None else "KRW",
            cash_balance=latest_cash_entry.balance_after if latest_cash_entry and latest_cash_entry.balance_after is not None else ZERO,
            positions={record.symbol: _position_from_snapshot(record) for record in position_records},
            realized_pnl=pnl.realized_pnl,
            unrealized_pnl=pnl.unrealized_pnl,
            total_pnl=pnl.total_pnl,
            nav=pnl.nav,
        )

    def latest_reconciliation_result(self) -> ReconciliationResult:
        with self._session() as session:
            record = session.scalars(
                select(ReconciliationLogRecord).order_by(ReconciliationLogRecord.occurred_at.desc())
            ).first()
            if record is None:
                raise KeyError("no reconciliation result stored")
        issues = tuple(
            ReconciliationIssue(
                code=item["code"],
                message=item["message"],
                severity=item.get("severity", "error"),
                recommended_action=item.get("recommended_action"),
                details=item.get("details"),
            )
            for item in (record.details or {}).get("issues", [])
        )
        return ReconciliationResult(
            reconciliation_id=record.id,
            occurred_at=record.occurred_at,
            status=record.status,
            mismatch_count=record.mismatch_count,
            requires_manual_intervention=record.requires_manual_intervention,
            summary=record.summary,
            issues=issues,
        )

    def active_kill_switch_events(self) -> list[KillSwitchEvent]:
        try:
            with self._session() as session:
                records = session.scalars(
                    select(KillSwitchEventRecord)
                    .where(KillSwitchEventRecord.is_active.is_(True))
                    .order_by(KillSwitchEventRecord.triggered_at)
                ).all()
        except OperationalError:
            return []
        return [
            KillSwitchEvent(
                event_id=record.id,
                reason=record.reason,
                triggered_at=record.triggered_at,
                trigger_value=record.trigger_value,
                threshold_value=record.threshold_value,
                details=record.details,
                is_active=record.is_active,
                cleared_at=record.cleared_at,
            )
            for record in records
        ]

    @contextmanager
    def _session(self):
        with self._session_factory.begin() as session:
            yield session

    def _ensure_strategy_run(self, session: Session, strategy_run_id: str) -> None:
        if session.get(StrategyRunRecord, strategy_run_id) is not None:
            return
        session.add(
            StrategyRunRecord(
                id=strategy_run_id,
                strategy_name="unspecified",
                mode=TradingMode.PAPER.value,
                status=StrategyRunStatus.RUNNING.value,
            )
        )


def _position_from_snapshot(record: PositionSnapshotRecord):
    from quant_os.domain.models import Position

    return Position(
        symbol=record.symbol,
        quantity=record.quantity,
        average_cost=record.average_cost,
        market_price=record.market_price,
    )


def _strategy_run_from_record(record: StrategyRunRecord) -> StrategyRun:
    return StrategyRun(
        strategy_run_id=record.id,
        strategy_name=record.strategy_name,
        mode=record.mode,
        status=record.status,
        strategy_id=record.strategy_id,
        strategy_kind=record.strategy_kind,
        strategy_version=record.strategy_version,
        dataset=record.dataset,
        profile_id=record.profile_id,
        artifact_path=record.artifact_path,
        config_fingerprint=record.config_fingerprint,
        tags_json=tuple(record.tags_json or ()),
        notes=record.notes,
        started_at=record.started_at,
        finished_at=record.finished_at,
        config_payload=record.config_payload,
    )


def _ensure_sqlite_parent(url: str) -> None:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return
    db_path = Path(url.removeprefix(prefix))
    db_path.parent.mkdir(parents=True, exist_ok=True)
