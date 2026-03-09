# Quant OS

Phase 1 through Phase 5 skeleton for a personal quant operating system MVP. This repository is intentionally biased toward:

- modular monolith over microservices
- batch-first workflows over unnecessary async
- fail-closed controls over fail-open convenience
- append-only order and fill events, with `orders` treated as a projection
- a common execution contract across `paper`, `shadow`, and `live`

## Current Scope

Implemented so far:

- project skeleton and importable Python package
- core domain enums, IDs, types, and models
- operational DB schema with SQLAlchemy and Alembic
- explicit YAML config with fail-closed loading into typed domain models
- Typer-based CLI skeleton
- Parquet-backed research storage indexed through DuckDB
- simple daily momentum strategy producing `TargetExposure`
- fail-closed risk review with single-name, cash-buffer, and turnover clipping
- target-to-intent diff generation
- simple batch backtest that reuses strategy, risk, and intent logic
- paper adapter with append-only order/fill event emission
- order state machine with projection derived from order events plus fills
- ledger projector with cash ledger, inventory lots, and PnL snapshot support
- reconciliation service for local vs external state comparison
- fail-closed kill switch for daily loss, stale market data, and reconciliation failures
- daily report generator summarizing NAV, cash, PnL, reconciliation, and kill-switch state
- shadow adapter skeleton that reuses the paper execution path for dry-run execution, venue-rule prechecks, and shadow reporting
- live adapter base plus fail-closed stub that preserves the common execution contract
- Upbit Quotation API read-only ingestion for no-signup daily market data collection
- pytest coverage for import, config, migration, research store, strategy pipeline, backtest, execution, reconciliation, kill switch, reporting, shadow, and simulation

The key boundary remains enforced: strategies produce `TargetExposure`, not `OrderIntent`.

## Proposed File Layout

```text
quant/
├─ alembic/
├─ conf/
│  └─ base.yaml
├─ data/
├─ docs/
│  └─ plans/
├─ research/
├─ src/quant_os/
│  ├─ adapters/
│  ├─ backtest/
│  ├─ cli/
│  ├─ config/
│  ├─ dashboard/
│  ├─ data_ingestion/
│  ├─ db/
│  ├─ domain/
│  ├─ execution/
│  ├─ intent/
│  ├─ ledger/
│  ├─ normalization/
│  ├─ portfolio/
│  ├─ reconciliation/
│  ├─ reporting/
│  ├─ research_store/
│  ├─ risk/
│  ├─ scheduler/
│  ├─ services/
│  └─ strategy/
├─ tests/
│  ├─ integration/
│  ├─ replay/
│  ├─ shadow/
│  ├─ simulation/
│  └─ unit/
├─ AGENTS.md
├─ pyproject.toml
└─ quant-os-mvp-design-spec.md
```

## Config Model

`conf/base.yaml` maps to `quant_os.config.models.AppSettings`, then converts into `quant_os.domain.models.SystemConfig`.

Current defaults assume:

- market: KRX ETF
- mode: `paper`
- strategy: daily momentum with configurable lookbacks
- risk: fail-closed limits with explicit cash buffer and turnover caps
- intent generation: market order defaults with minimum notional and lot size
- backtest: explicit initial cash and bps cost model
- controls: reconciliation tolerances and stale market data threshold
- storage: operational DB plus local research/data paths

## DB Model

The operational schema includes:

- `strategy_runs`
- `orders`
- `order_events`
- `fills`
- `positions_snapshot`
- `cash_ledger`
- `pnl_snapshot`
- `reconciliation_log`
- `kill_switch_events`

Rules enforced by the schema design:

- `order_events` and `fills` are append-only source-of-truth tables
- `orders` is a projection table
- broker identifiers are dedupe-aware
- numeric columns use explicit precision

## CLI

The initial CLI exposes:

```bash
quant-os doctor --config conf/base.yaml
quant-os ingest-upbit-daily --config conf/base.yaml --market KRW-BTC --count 30
quant-os serve-api --config conf/base.yaml --host 127.0.0.1 --port 8000
```

That command validates the base config, converts it into the domain config, and prints the current research/risk/intent/ledger/execution/reconciliation/kill-switch/reporting runtime surface plus required operational tables.

Runtime adapter selection is now mode-aware:

- `paper` -> `PaperAdapter`
- `shadow` -> `ShadowAdapter`
- `live` -> `StubLiveAdapter`

`StubLiveAdapter` is intentionally fail-closed. Until a real broker adapter is added, live submissions are rejected with append-only order events rather than silently proceeding.

Current simulation coverage now includes:

- partial-fill and timeout-to-`RECONCILE_PENDING`
- duplicate-fill and out-of-order event rejection
- store-backed restart/recovery readback
- operational kill-switch trigger paths

## API Reference

The evaluated API options and the currently attached no-signup API are documented in [api_reference.md](/home/lia/repos/my-projects/quant/docs/api_reference.md).

## Usage Guide

Step-by-step execution and usage instructions are documented in [usage_guide.md](/home/lia/repos/my-projects/quant/docs/usage_guide.md).

## End-to-End Workflow

The full system workflow is documented in [end_to_end_workflow.md](/home/lia/repos/my-projects/quant/docs/end_to_end_workflow.md).

## Frontend Design

The current frontend-first architecture and dashboard scope are documented in [frontend_ops_dashboard_design.md](/home/lia/repos/my-projects/quant/docs/frontend_ops_dashboard_design.md).

The screen-by-screen specification is documented in [frontend_screen_spec.md](/home/lia/repos/my-projects/quant/docs/frontend_screen_spec.md).

The frontend/backend data contract is documented in [frontend_data_contract.md](/home/lia/repos/my-projects/quant/docs/frontend_data_contract.md).

The proposed FastAPI surface for that dashboard is documented in [frontend_fastapi_api_design.md](/home/lia/repos/my-projects/quant/docs/frontend_fastapi_api_design.md).

The implementation plan is documented in [2026-03-10-frontend-ops-dashboard-implementation.md](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-frontend-ops-dashboard-implementation.md).

## Quick Start

1. Create the project environment:

```bash
uv sync --extra dev
```

2. Run the unit skeleton:

```bash
uv run --extra dev pytest -q
```

3. Validate the migration:

```bash
uv run python -m alembic upgrade head
```

4. Validate config and package wiring:

```bash
uv run quant-os doctor --config conf/base.yaml
```

5. Start the dashboard backend:

```bash
uv run quant-os serve-api --config conf/base.yaml --host 0.0.0.0 --port 8000
```

6. Open the dashboard:

```bash
http://127.0.0.1:8000
```

The same process now serves:

- frontend SPA at `/`
- API at `/api`

## Next Phase Targets

Immediate follow-up work should focus on:

- venue-specific live adapter implementation
- broader simulation coverage for timeout, duplicate, and out-of-order event paths
- richer shadow/live comparison reporting
- restart/replay hardening around execution recovery
