# Quant OS Phase 2 Decision Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Phase 2 research and decision pipeline so normalized market data can be stored in the research layer, replayed through a simple backtest, converted into `TargetExposure`, reviewed by risk, and transformed into `OrderIntent`.

**Architecture:** Keep the research layer separate from operational persistence by using Parquet/DuckDB-backed artifacts under the local research/data roots. Implement a simple daily momentum strategy that returns `TargetExposure` only, then pass it through a fail-closed risk manager and a deterministic target-to-intent diff engine. Use the same strategy/risk/intent logic in a minimal batch backtest so the paper path in Phase 3 can reuse it.

**Tech Stack:** Python 3.12+, Pydantic v2, DuckDB, PyArrow, SQLAlchemy 2.x, Typer, pytest

---

### Task 1: Write failing tests for the Phase 2 pipeline

**Files:**
- Create: `tests/unit/test_research_store.py`
- Create: `tests/unit/test_strategy_pipeline.py`
- Create: `tests/unit/test_backtest.py`

**Step 1: Write the failing test**

Add tests that require:
- writing normalized bars to Parquet and querying them through DuckDB
- generating `TargetExposure` from a momentum strategy
- clipping targets through a fail-closed risk manager
- creating `OrderIntent` from approved targets and current portfolio state
- replaying the strategy/risk pipeline through a simple backtest

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/unit/test_research_store.py tests/unit/test_strategy_pipeline.py tests/unit/test_backtest.py -q`
Expected: FAIL because Phase 2 modules do not exist yet.

**Step 3: Write minimal implementation**

Implement research store, strategy, risk, intent, and backtest modules with only the behavior required by the tests.

**Step 4: Run test to verify it passes**

Run: `uv run --extra dev pytest tests/unit/test_research_store.py tests/unit/test_strategy_pipeline.py tests/unit/test_backtest.py -q`
Expected: PASS.

### Task 2: Update config and domain support

**Files:**
- Modify: `conf/base.yaml`
- Modify: `src/quant_os/config/models.py`
- Modify: `src/quant_os/domain/models.py`

**Step 1: Extend the config surface**

Add the smallest set of fields needed to configure:
- research DuckDB path
- momentum strategy lookbacks
- sizing/min-lot assumptions for intent generation
- backtest cost assumptions

**Step 2: Keep boundaries explicit**

Ensure the strategy config still seeds or generates `TargetExposure` only and does not leak order logic into the strategy layer.

### Task 3: Add verification hooks

**Files:**
- Modify: `src/quant_os/cli/main.py`

**Step 1: Add a Phase 2 doctor path**

Expose a CLI command that proves the config can instantiate the strategy/risk/intent pipeline.

**Step 2: Verify**

Run:
- `uv run --extra dev pytest -q`
- `uv run quant-os doctor --config conf/base.yaml`

Expected:
- all tests green
- CLI still prints valid config/runtime information
