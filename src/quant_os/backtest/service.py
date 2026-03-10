from __future__ import annotations

from pathlib import Path

from quant_os.backtest.orchestrator import BacktestOrchestrator, BacktestRunArtifact
from quant_os.backtest.request import BacktestRequest
from quant_os.config.models import AppSettings


def run_configured_backtest(settings: AppSettings, *, dataset: str | None = None) -> BacktestRunArtifact:
    return BacktestOrchestrator(settings).run_legacy(dataset=dataset)


def run_backtest_request(settings: AppSettings, request: BacktestRequest) -> BacktestRunArtifact:
    return BacktestOrchestrator(settings).run_request(request)
