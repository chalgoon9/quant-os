from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from quant_os.backtest.results import BacktestArtifactStore, StoredBacktestResult
from quant_os.backtest.simple import SimpleBacktester
from quant_os.config.models import AppSettings
from quant_os.db.store import OperationalStore
from quant_os.domain.enums import StrategyRunStatus
from quant_os.domain.models import StrategyRun
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
    run_id = f"backtest_{uuid4().hex[:12]}"
    strategy_run_payload = _build_strategy_run_payload(settings, dataset_name)
    operational_store = OperationalStore(system.storage.operational_db_url)
    operational_store.create_schema()
    operational_store.start_strategy_run(
        StrategyRun(
            strategy_run_id=run_id,
            strategy_name=system.strategy.name,
            mode="backtest",
            status=StrategyRunStatus.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
            config_payload=strategy_run_payload,
        )
    )

    research_store = ResearchStore(
        root=system.storage.data_root / "normalized",
        duckdb_path=system.research.duckdb_path,
    )
    try:
        bars_by_symbol = _load_bars_for_universe(research_store, dataset_name, system.strategy.universe)
        loaded_symbols = tuple(sorted(symbol for symbol, bars in bars_by_symbol.items() if bars))
        missing_symbols = tuple(symbol for symbol in system.strategy.universe if symbol not in loaded_symbols)
        if not loaded_symbols:
            raise ValueError(f"dataset '{dataset_name}' does not contain bars for the configured strategy universe")

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
        operational_store.finish_strategy_run(
            run_id,
            status=StrategyRunStatus.SUCCEEDED,
            finished_at=generated_at,
            config_payload={
                **strategy_run_payload,
                "artifact_path": str(path),
                "loaded_symbols": list(loaded_symbols),
                "missing_symbols": list(missing_symbols),
                "as_of": _jsonify(as_of),
                "final_nav": str(stored_result.final_nav),
                "total_return": str(stored_result.total_return),
                "max_drawdown": str(stored_result.max_drawdown),
                "trade_count": stored_result.trade_count,
            },
        )
        return BacktestRunArtifact(result=stored_result, path=path)
    except Exception as exc:
        operational_store.finish_strategy_run(
            run_id,
            status=StrategyRunStatus.FAILED,
            finished_at=datetime.now(tz=timezone.utc),
            config_payload={
                **strategy_run_payload,
                "error": str(exc),
            },
        )
        raise


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


def _build_strategy_run_payload(settings: AppSettings, dataset_name: str) -> dict[str, object]:
    settings_payload = settings.model_dump(mode="json")
    fingerprint = hashlib.sha256(json.dumps(settings_payload, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "trigger": "run-backtest",
        "dataset": dataset_name,
        "config_fingerprint": fingerprint,
        "settings": settings_payload,
    }


def _jsonify(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
