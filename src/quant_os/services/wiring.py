from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os

from quant_os.adapters.live import StubLiveAdapter
from quant_os.adapters.paper import PaperAdapter
from quant_os.adapters.shadow import ShadowAdapter
from quant_os.adapters.upbit_live import UpbitExchangeClient, UpbitLiveAdapter
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
    kill_switch = KillSwitch(
        daily_loss_limit=system.risk.daily_loss_limit,
        stale_market_data_seconds=system.controls.stale_market_data_seconds,
        allowed_symbols=system.strategy.universe,
        max_gross_exposure=system.controls.max_gross_exposure,
        reject_rate_window=system.controls.reject_rate_window,
        reject_rate_threshold=system.controls.reject_rate_threshold,
        store=operational_store,
    )
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
        live_settings=system.live,
        kill_switch=kill_switch,
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
        kill_switch=kill_switch,
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
    live_settings=None,
    kill_switch: KillSwitch | None = None,
) -> ExecutionAdapter:
    if mode is TradingMode.PAPER:
        return PaperAdapter(
            initial_portfolio,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            store=operational_store,
            kill_switch=kill_switch,
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
            kill_switch=kill_switch,
        )
    if venue.lower() == "upbit":
        access_key = os.environ.get(live_settings.upbit_access_key_env) if live_settings is not None else None
        secret_key = os.environ.get(live_settings.upbit_secret_key_env) if live_settings is not None else None
        if access_key and secret_key and live_settings is not None:
            return UpbitLiveAdapter(
                initial_portfolio,
                client=UpbitExchangeClient(
                    access_key=access_key,
                    secret_key=secret_key,
                    api_base_url=live_settings.upbit_api_base_url,
                ),
                store=operational_store,
                kill_switch=kill_switch,
            )
    return StubLiveAdapter(initial_portfolio, store=operational_store, kill_switch=kill_switch)
