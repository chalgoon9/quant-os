from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from quant_os.backtest.profile import BacktestProfile, load_backtest_profiles
from quant_os.backtest.request import BacktestRequest
from quant_os.backtest.results import BacktestArtifactStore, StoredBacktestResult
from quant_os.backtest.simple import SimpleBacktester
from quant_os.config.models import AppSettings
from quant_os.db.store import OperationalStore
from quant_os.domain.enums import StrategyRunStatus
from quant_os.domain.models import MarketBar, StrategyRun
from quant_os.domain.types import quantize
from quant_os.intent.generator import TargetExposureIntentGenerator
from quant_os.research_store.store import ResearchStore
from quant_os.risk.simple import SimpleRiskManager
from quant_os.strategy import StrategySpec, load_strategy_specs, strategy_registry


@dataclass(frozen=True)
class BacktestRunArtifact:
    result: StoredBacktestResult
    path: Path


class BacktestOrchestrator:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.system = settings.to_domain_model()
        self.operational_store = OperationalStore(self.system.storage.operational_db_url)
        self.operational_store.create_schema()
        self.research_store = ResearchStore(
            root=self.system.storage.data_root / "normalized",
            duckdb_path=self.system.research.duckdb_path,
        )
        self.artifact_store = BacktestArtifactStore(self.system.storage.artifacts_root)
        self.strategy_specs = load_strategy_specs()
        self.profiles = load_backtest_profiles()

    def run_request(self, request: BacktestRequest) -> BacktestRunArtifact:
        spec = self._resolve_strategy_spec(request.strategy_id)
        profile = self._resolve_profile(request.profile_id)
        return self._run_resolved(
            request=request,
            spec=spec,
            profile=profile,
        )

    def run_legacy(self, *, dataset: str | None = None) -> BacktestRunArtifact:
        strategy = self.system.strategy
        spec = StrategySpec(
            strategy_id=strategy.name,
            kind="daily_momentum",
            version="runtime",
            description=strategy.name,
            dataset_default=dataset or self.system.research.market_data_dataset,
            universe=strategy.universe,
            rebalance_calendar=strategy.rebalance_calendar,
            params={
                "max_names": strategy.max_names,
                "target_gross_exposure_limit": str(strategy.target_gross_exposure_limit),
                "fast_lookback": strategy.fast_lookback,
                "slow_lookback": strategy.slow_lookback,
                "trend_lookback": strategy.trend_lookback,
                "seed_weights": {key: str(value) for key, value in (strategy.seed_weights or {}).items()},
            },
            tags=("legacy-runtime",),
        )
        request = BacktestRequest(
            strategy_id=spec.strategy_id,
            dataset=dataset or self.system.research.market_data_dataset,
            profile_id="runtime-config",
            notes="legacy config-driven backtest",
            tags=("legacy",),
        )
        profile = BacktestProfile(
            profile_id="runtime-config",
            description="legacy profile synthesized from conf/base.yaml",
            commission_bps=self.system.backtest.commission_bps,
            slippage_bps=self.system.backtest.slippage_bps,
            initial_cash=self.system.backtest.initial_cash,
        )
        return self._run_resolved(request=request, spec=spec, profile=profile)

    def _run_resolved(
        self,
        *,
        request: BacktestRequest,
        spec: StrategySpec,
        profile: BacktestProfile,
    ) -> BacktestRunArtifact:
        run_id = f"backtest_{uuid4().hex[:12]}"
        request_payload = request.model_dump(mode="json")
        spec_payload = spec.model_dump(mode="json")
        profile_payload = profile.model_dump(mode="json")
        settings_payload = {
            "trigger": "run-backtest",
            "strategy_id": spec.strategy_id,
            "strategy_kind": spec.kind,
            "strategy_version": spec.version,
            "dataset": request.dataset,
            "profile_id": request.profile_id,
            "config_fingerprint": None,
            "request": request_payload,
            "strategy_spec": spec_payload,
            "profile": profile_payload,
        }
        config_fingerprint = hashlib.sha256(
            json.dumps(settings_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        settings_payload["config_fingerprint"] = config_fingerprint
        self.operational_store.start_strategy_run(
            StrategyRun(
                strategy_run_id=run_id,
                strategy_name=spec.description,
                mode="backtest",
                status=StrategyRunStatus.RUNNING,
                strategy_id=spec.strategy_id,
                strategy_kind=spec.kind,
                strategy_version=spec.version,
                dataset=request.dataset,
                profile_id=request.profile_id,
                config_fingerprint=config_fingerprint,
                tags_json=request.tags or spec.tags,
                notes=request.notes,
                started_at=datetime.now(tz=timezone.utc),
                config_payload=settings_payload,
            )
        )

        try:
            bars_by_symbol = self._load_bars_for_universe(request.dataset, spec.universe, request.date_from, request.date_to)
            loaded_symbols = tuple(sorted(symbol for symbol, bars in bars_by_symbol.items() if bars))
            missing_symbols = tuple(symbol for symbol in spec.universe if symbol not in loaded_symbols)
            if not loaded_symbols:
                raise ValueError(f"dataset '{request.dataset}' does not contain bars for the requested strategy universe")
            raw_result = SimpleBacktester(
                bars_by_symbol=bars_by_symbol,
                strategy=strategy_registry.build(spec, bars_by_symbol),
                risk_manager=SimpleRiskManager(self.system.risk),
                intent_generator=TargetExposureIntentGenerator(self.system.intent, strategy_run_id=run_id),
                settings=profile.to_backtest_settings(self.system.backtest),
            ).run()
            generated_at = datetime.now(tz=timezone.utc)
            as_of = raw_result.equity_curve[-1].timestamp if raw_result.equity_curve else generated_at
            initial_cash = profile.initial_cash or self.system.backtest.initial_cash
            total_return = quantize((raw_result.final_nav / initial_cash) - Decimal("1"), "0.0001")
            stored_result = StoredBacktestResult(
                run_id=run_id,
                strategy_id=spec.strategy_id,
                strategy_name=spec.description,
                strategy_kind=spec.kind,
                strategy_version=spec.version,
                dataset=request.dataset,
                profile_id=request.profile_id,
                generated_at=generated_at,
                as_of=as_of,
                initial_cash=initial_cash,
                final_nav=raw_result.final_nav,
                total_return=total_return,
                max_drawdown=raw_result.max_drawdown,
                trade_count=raw_result.trade_count,
                loaded_symbols=loaded_symbols,
                missing_symbols=missing_symbols,
                equity_curve=raw_result.equity_curve,
                trades=raw_result.trades,
                tags=request.tags or spec.tags,
                notes=request.notes,
            )
            path = self.artifact_store.save(stored_result)
            self.operational_store.finish_strategy_run(
                run_id,
                status=StrategyRunStatus.SUCCEEDED,
                finished_at=generated_at,
                artifact_path=str(path),
                config_payload={
                    **settings_payload,
                    "artifact_path": str(path),
                    "loaded_symbols": list(loaded_symbols),
                    "missing_symbols": list(missing_symbols),
                    "as_of": as_of.isoformat(),
                    "final_nav": str(stored_result.final_nav),
                    "total_return": str(stored_result.total_return),
                    "max_drawdown": str(stored_result.max_drawdown),
                    "trade_count": stored_result.trade_count,
                },
            )
            return BacktestRunArtifact(result=stored_result, path=path)
        except Exception as exc:
            self.operational_store.finish_strategy_run(
                run_id,
                status=StrategyRunStatus.FAILED,
                finished_at=datetime.now(tz=timezone.utc),
                config_payload={
                    **settings_payload,
                    "error": str(exc),
                },
            )
            raise

    def _resolve_strategy_spec(self, strategy_id: str) -> StrategySpec:
        try:
            return self.strategy_specs[strategy_id]
        except KeyError as exc:
            raise KeyError(f"unknown strategy id: {strategy_id}") from exc

    def _resolve_profile(self, profile_id: str) -> BacktestProfile:
        try:
            return self.profiles[profile_id]
        except KeyError as exc:
            raise KeyError(f"unknown backtest profile: {profile_id}") from exc

    def _load_bars_for_universe(
        self,
        dataset: str,
        universe: tuple[str, ...],
        date_from,
        date_to,
    ) -> dict[str, list[MarketBar]]:
        bars_by_symbol: dict[str, list[MarketBar]] = {}
        dataset_error: FileNotFoundError | None = None
        for symbol in universe:
            try:
                bars = self.research_store.load_bars(dataset, symbol=symbol)
            except FileNotFoundError as exc:
                dataset_error = exc
                break
            filtered = []
            for bar in bars:
                bar_date = getattr(bar.timestamp, "date", lambda: bar.timestamp)()
                if date_from is not None and bar_date < date_from:
                    continue
                if date_to is not None and bar_date > date_to:
                    continue
                filtered.append(bar)
            if filtered:
                bars_by_symbol[symbol] = filtered
        if dataset_error is not None:
            raise FileNotFoundError(f"research dataset not found: {dataset}") from dataset_error
        return bars_by_symbol
