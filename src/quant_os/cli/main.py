from __future__ import annotations

from pathlib import Path
import uvicorn

import typer

from quant_os.backtest.service import run_configured_backtest
from quant_os.api.main import create_app
from quant_os.config.loader import load_settings
from quant_os.data_ingestion.upbit import (
    UpbitQuotationClient,
    default_upbit_dataset_name,
    ingest_upbit_daily_bars,
)
from quant_os.db.schema import REQUIRED_TABLES
from quant_os.services.wiring import build_app_runtime


app = typer.Typer(
    add_completion=False,
    help="Quant OS operational CLI skeleton.",
    name="quant-os",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


@app.callback()
def callback() -> None:
    """Quant OS operational commands."""


@app.command("doctor")
def doctor(config: Path = Path("conf/base.yaml")) -> None:
    """Validate the base config and show the current runtime surface."""
    settings = load_settings(config)
    system = settings.to_domain_model()
    runtime = build_app_runtime(settings)
    typer.echo(f"system={system.system_name}")
    typer.echo(f"mode={system.mode.value}")
    typer.echo(f"strategy={system.strategy.name}")
    typer.echo(f"research_dataset={system.research.market_data_dataset}")
    typer.echo(f"intent_lot_size={system.intent.lot_size}")
    typer.echo(
        "runtime="
        f"research:{runtime.research_store.duckdb_path.name},"
        f"risk:intent,ledger:{type(runtime.ledger_projector).__name__},"
        f"execution:{type(runtime.execution_adapter).__name__},"
        f"recon:{type(runtime.reconciler).__name__},"
        f"kill:{type(runtime.kill_switch).__name__},"
        f"report:{type(runtime.report_generator).__name__}"
    )
    typer.echo(f"tables={','.join(sorted(REQUIRED_TABLES))}")


@app.command("ingest-upbit-daily")
def ingest_upbit_daily(
    market: str = typer.Option(..., "--market", help="Upbit market code such as KRW-BTC."),
    count: int = typer.Option(200, "--count", min=1, help="Number of daily candles to fetch."),
    dataset: str | None = typer.Option(None, "--dataset", help="Override the dataset name."),
    config: Path = Path("conf/base.yaml"),
) -> None:
    """Fetch read-only Upbit daily candles and store them in the research store."""
    settings = load_settings(config)
    runtime = build_app_runtime(settings)
    client = UpbitQuotationClient()
    resolved_dataset = dataset or default_upbit_dataset_name(market)
    path = ingest_upbit_daily_bars(
        client=client,
        research_store=runtime.research_store,
        market=market,
        count=count,
        dataset=resolved_dataset,
    )
    typer.echo(f"source=upbit_quotation")
    typer.echo(f"market={market.upper()}")
    typer.echo(f"dataset={resolved_dataset}")
    typer.echo(f"path={path}")


@app.command("run-backtest")
def run_backtest(
    config: Path = Path("conf/base.yaml"),
    dataset: str | None = typer.Option(None, "--dataset", help="Override the research dataset name."),
) -> None:
    """Run the configured strategy through the simple backtest engine and save the latest result artifact."""
    settings = load_settings(config)
    try:
        artifact = run_configured_backtest(settings, dataset=dataset)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error={exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(f"run_id={artifact.result.run_id}")
    typer.echo(f"strategy={artifact.result.strategy_name}")
    typer.echo(f"dataset={artifact.result.dataset}")
    typer.echo(f"path={artifact.path}")
    typer.echo(f"loaded_symbols={','.join(artifact.result.loaded_symbols)}")
    typer.echo(f"missing_symbols={','.join(artifact.result.missing_symbols)}")
    typer.echo(f"final_nav={artifact.result.final_nav}")
    typer.echo(f"total_return={artifact.result.total_return}")
    typer.echo(f"max_drawdown={artifact.result.max_drawdown}")
    typer.echo(f"trade_count={artifact.result.trade_count}")


@app.command("serve-api")
def serve_api(
    config: Path = Path("conf/base.yaml"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host for the FastAPI server."),
    port: int = typer.Option(8000, "--port", min=1, max=65535, help="Bind port for the FastAPI server."),
) -> None:
    """Serve the FastAPI dashboard backend against the selected config."""
    uvicorn.run(create_app(config=config), host=host, port=port)


def main() -> None:
    app()
