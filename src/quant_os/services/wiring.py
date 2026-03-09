from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from quant_os.adapters.live import StubLiveAdapter
from quant_os.adapters.paper import PaperAdapter
from quant_os.adapters.shadow import ShadowAdapter
from quant_os.config.models import AppSettings
from quant_os.db.store import OperationalStore
from quant_os.domain.enums import TradingMode
from quant_os.domain.interfaces import ExecutionAdapter
from quant_os.domain.models import PortfolioState
from quant_os.intent.generator import TargetExposureIntentGenerator
from quant_os.ledger.projector import LedgerProjector
from quant_os.reconciliation.service import PortfolioReconciler
from quant_os.research_store.store import ResearchStore
from quant_os.reporting.daily import DailyReportGenerator
from quant_os.risk.kill_switch import KillSwitch
from quant_os.risk.simple import SimpleRiskManager


@dataclass(frozen=True)
class AppRuntime:
    operational_store: OperationalStore
    research_store: ResearchStore
    risk_manager: SimpleRiskManager
    intent_generator: TargetExposureIntentGenerator
    ledger_projector: LedgerProjector
    execution_adapter: ExecutionAdapter
    reconciler: PortfolioReconciler
    kill_switch: KillSwitch
    report_generator: DailyReportGenerator

    @property
    def paper_adapter(self) -> ExecutionAdapter:
        return self.execution_adapter


def build_app_runtime(settings: AppSettings) -> AppRuntime:
    system = settings.to_domain_model()
    operational_store = OperationalStore(system.storage.operational_db_url)
    initial_portfolio = PortfolioState(
        as_of=datetime.now(tz=timezone.utc),
        base_currency=system.base_currency,
        cash_balance=system.backtest.initial_cash,
        net_asset_value=system.backtest.initial_cash,
        positions=(),
        market_prices={},
    )
    ledger_projector = LedgerProjector(
        base_currency=system.base_currency,
        initial_cash=system.backtest.initial_cash,
    )
    execution_adapter = _build_execution_adapter(
        mode=system.mode,
        venue=system.venue,
        initial_portfolio=initial_portfolio,
        commission_bps=system.backtest.commission_bps,
        slippage_bps=system.backtest.slippage_bps,
        lot_size=system.intent.lot_size,
        min_notional=system.intent.min_trade_notional,
        operational_store=operational_store,
    )
    return AppRuntime(
        operational_store=operational_store,
        research_store=ResearchStore(
            root=system.storage.data_root / "normalized",
            duckdb_path=system.research.duckdb_path,
        ),
        risk_manager=SimpleRiskManager(system.risk),
        intent_generator=TargetExposureIntentGenerator(system.intent, strategy_run_id="doctor_runtime"),
        ledger_projector=ledger_projector,
        execution_adapter=execution_adapter,
        reconciler=PortfolioReconciler(
            cash_tolerance=system.controls.reconciliation_cash_tolerance,
            position_tolerance=system.controls.reconciliation_position_tolerance,
            store=operational_store,
        ),
        kill_switch=KillSwitch(
            daily_loss_limit=system.risk.daily_loss_limit,
            stale_market_data_seconds=system.controls.stale_market_data_seconds,
            store=operational_store,
        ),
        report_generator=DailyReportGenerator(),
    )


def build_phase2_runtime(settings: AppSettings) -> AppRuntime:
    return build_app_runtime(settings)


def _build_execution_adapter(
    *,
    mode: TradingMode,
    venue: str,
    initial_portfolio: PortfolioState,
    commission_bps,
    slippage_bps,
    lot_size,
    min_notional,
    operational_store: OperationalStore,
) -> ExecutionAdapter:
    if mode is TradingMode.PAPER:
        return PaperAdapter(
            initial_portfolio,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            store=operational_store,
        )
    if mode is TradingMode.SHADOW:
        return ShadowAdapter(
            initial_portfolio,
            venue=venue,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            lot_size=lot_size,
            min_notional=min_notional,
            store=operational_store,
        )
    return StubLiveAdapter(initial_portfolio, store=operational_store)
