from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from quant_os.backtest.results import BacktestArtifactStore, StoredBacktestResult
from quant_os.backtest.simple import SimpleBacktester
from quant_os.config.models import AppSettings
from quant_os.domain.types import quantize
from quant_os.intent.generator import TargetExposureIntentGenerator
from quant_os.research_store.store import ResearchStore
from quant_os.risk.simple import SimpleRiskManager
from quant_os.strategy.momentum import DailyMomentumStrategy


@dataclass(frozen=True)
class BacktestRunArtifact:
    result: StoredBacktestResult
    path: Path


def run_configured_backtest(settings: AppSettings, *, dataset: str | None = None) -> BacktestRunArtifact:
    system = settings.to_domain_model()
    dataset_name = dataset or system.research.market_data_dataset
    research_store = ResearchStore(
        root=system.storage.data_root / "normalized",
        duckdb_path=system.research.duckdb_path,
    )
    bars_by_symbol = _load_bars_for_universe(research_store, dataset_name, system.strategy.universe)
    loaded_symbols = tuple(sorted(symbol for symbol, bars in bars_by_symbol.items() if bars))
    missing_symbols = tuple(symbol for symbol in system.strategy.universe if symbol not in loaded_symbols)
    if not loaded_symbols:
        raise ValueError(f"dataset '{dataset_name}' does not contain bars for the configured strategy universe")

    run_id = f"backtest_{uuid4().hex[:12]}"
    backtester = SimpleBacktester(
        bars_by_symbol=bars_by_symbol,
        strategy=DailyMomentumStrategy(system.strategy, bars_by_symbol),
        risk_manager=SimpleRiskManager(system.risk),
        intent_generator=TargetExposureIntentGenerator(system.intent, strategy_run_id=run_id),
        settings=system.backtest,
    )
    raw_result = backtester.run()
    generated_at = datetime.now(tz=timezone.utc)
    as_of = raw_result.equity_curve[-1].timestamp if raw_result.equity_curve else generated_at
    total_return = quantize((raw_result.final_nav / system.backtest.initial_cash) - Decimal("1"), "0.0001")
    stored_result = StoredBacktestResult(
        run_id=run_id,
        strategy_name=system.strategy.name,
        dataset=dataset_name,
        generated_at=generated_at,
        as_of=as_of,
        initial_cash=system.backtest.initial_cash,
        final_nav=raw_result.final_nav,
        total_return=total_return,
        max_drawdown=raw_result.max_drawdown,
        trade_count=raw_result.trade_count,
        loaded_symbols=loaded_symbols,
        missing_symbols=missing_symbols,
        equity_curve=raw_result.equity_curve,
        trades=raw_result.trades,
    )
    artifact_store = BacktestArtifactStore(system.storage.artifacts_root)
    path = artifact_store.save(stored_result)
    return BacktestRunArtifact(result=stored_result, path=path)


def _load_bars_for_universe(
    research_store: ResearchStore,
    dataset: str,
    universe: tuple[str, ...],
) -> dict[str, list]:
    bars_by_symbol: dict[str, list] = {}
    dataset_error: FileNotFoundError | None = None
    for symbol in universe:
        try:
            bars = research_store.load_bars(dataset, symbol=symbol)
        except FileNotFoundError as exc:
            dataset_error = exc
            break
        if bars:
            bars_by_symbol[symbol] = bars
    if dataset_error is not None:
        raise FileNotFoundError(f"research dataset not found: {dataset}") from dataset_error
    return bars_by_symbol
