# Quant OS Phase 6c Backtest Request / Catalog

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the single hardcoded backtest path with a request-driven orchestrator that can resolve a strategy spec, dataset, and backtest profile into a reproducible run, while preserving legacy CLI compatibility.

**Architecture:** Keep the current `run_configured_backtest()` path as a legacy wrapper. Introduce `BacktestRequest`, `BacktestProfile`, and an orchestrator that resolves strategy specs via the registry, loads datasets from the research store, executes the backtest, and persists both artifacts and strategy-run metadata.

**Tech Stack:** Pydantic v2, Typer, DuckDB, pytest

---

## Task 1: Write failing backtest request/catalog tests

**Files:**
- Create: `tests/unit/test_backtest_request.py`
- Modify: `tests/unit/test_backtest_artifacts.py`
- Modify: `tests/unit/test_backtest_cli.py`
- Modify if needed: `tests/unit/test_backtest.py`

**Step 1: Write the failing test**

Require:
- a typed `BacktestRequest`
- a typed `BacktestProfile`
- running a backtest by `strategy_id + dataset + profile_id`
- storing artifacts in a catalog, not just as `latest.json`
- listing runs and loading run details by `run_id`
- preserving `latest.json` for compatibility
- preserving legacy CLI invocation through a wrapper path

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --extra dev pytest tests/unit/test_backtest.py tests/unit/test_backtest_artifacts.py tests/unit/test_backtest_cli.py tests/unit/test_backtest_request.py -q
```

Expected:
- FAIL because request/profile/orchestrator/catalog do not exist yet.

**Step 3: Write minimal implementation**

Implement the smallest orchestrator and artifact catalog needed to satisfy the tests.

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --extra dev pytest tests/unit/test_backtest.py tests/unit/test_backtest_artifacts.py tests/unit/test_backtest_cli.py tests/unit/test_backtest_request.py -q
```

Expected:
- PASS

---

## Task 2: Introduce request/profile/orchestrator modules

**Files:**
- Create: `src/quant_os/backtest/request.py`
- Create: `src/quant_os/backtest/profile.py`
- Create: `src/quant_os/backtest/orchestrator.py`
- Modify: `src/quant_os/backtest/service.py`
- Modify: `src/quant_os/backtest/results.py`
- Modify: `src/quant_os/cli/main.py`
- Create: `conf/backtests/baseline.yaml`
- Create: `conf/backtests/stress_10bps.yaml`

**Step 1: Add request and profile types**

Minimum request fields:
- `strategy_id`
- `dataset`
- `profile_id`
- optional `date_from`
- optional `date_to`
- optional `notes`
- optional `tags`

Minimum profile fields:
- `profile_id`
- cost assumptions (commission/slippage)
- optional overrides for initial cash or trade assumptions

**Step 2: Refactor the service into an orchestrator**

The orchestrator should:
- resolve the strategy spec via registry
- resolve the profile
- load bars for the strategy universe from the research store
- run the backtest
- persist artifact file and strategy run metadata

**Step 3: Keep legacy CLI compatibility**

These should both keep working:

```bash
uv run quant-os run-backtest --config conf/base.yaml --dataset krx_etf_daily
uv run quant-os run-backtest --strategy-id kr_etf_momo_20_60_v1 --dataset krx_etf_daily --profile-id baseline
```

The old path may internally synthesize a `BacktestRequest`.

---

## Task 3: Turn artifact storage into a catalog

**Files:**
- Modify: `src/quant_os/backtest/results.py`

**Step 1: Keep latest, add catalog**

Required capabilities:
- save run artifact under a stable path such as `backtests/<strategy_id>/<timestamp>_<run_id>.json`
- list runs
- load by `run_id`
- keep writing `latest.json` for compatibility

**Step 2: Do not overbuild compare here**

Store enough metadata for later API compare, but keep compare computation simple in this phase.

---

## Acceptance criteria

- same strategy can be run under multiple profiles
- multiple strategy ids can coexist in artifacts without overwriting one another
- legacy CLI still works
- `latest.json` still works
- run metadata answers strategy / dataset / profile / artifact path / fingerprint
