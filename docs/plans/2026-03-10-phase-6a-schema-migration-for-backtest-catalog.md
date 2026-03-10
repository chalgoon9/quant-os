# Quant OS Phase 6a Schema Migration For Backtest Catalog

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Widen the operational metadata model just enough to support a multi-strategy research/backtest catalog, without disturbing the current execution tables or live runtime behavior.

**Architecture:** Keep the existing operational schema intact and apply an additive migration centered on `strategy_runs`. Do not redesign orders/fills/ledger now. Add catalog metadata columns so a run can be identified by strategy id, strategy kind, dataset, profile, config fingerprint, and artifact path.

**Tech Stack:** Alembic, SQLAlchemy 2.x, pytest

---

## Task 1: Write failing schema/store tests

**Files:**
- Modify: `tests/unit/test_db_schema.py`
- Modify: `tests/unit/test_operational_store.py`
- Create if needed: `tests/unit/test_strategy_run_catalog_schema.py`

**Step 1: Write the failing test**

Require:
- migrated `strategy_runs` table exposes the new catalog columns
- `OperationalStore.start_strategy_run()` persists those fields
- `OperationalStore.list_strategy_runs()` can return them
- legacy run creation without explicit new fields still works

New fields to require at minimum:
- `strategy_id`
- `strategy_kind`
- `strategy_version`
- `dataset`
- `profile_id`
- `artifact_path`
- `config_fingerprint`
- `tags_json`
- `notes`

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --extra dev pytest tests/unit/test_db_schema.py tests/unit/test_operational_store.py -q
```

Expected:
- FAIL because the schema and domain/store models do not expose the new fields yet.

**Step 3: Write minimal implementation**

Implement the smallest migration and model widening necessary to satisfy the tests.

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --extra dev pytest tests/unit/test_db_schema.py tests/unit/test_operational_store.py -q
```

Expected:
- PASS

---

## Task 2: Apply additive schema widening only

**Files:**
- Modify: `src/quant_os/db/schema.py`
- Modify: `src/quant_os/db/store.py`
- Modify: `src/quant_os/domain/models.py`
- Create: `alembic/versions/20260310_000X_phase6a_backtest_catalog.py`

**Step 1: Additive migration only**

Do:
- add nullable or compatibility-friendly columns to `strategy_runs`
- backfill or derive legacy values where reasonable
- keep existing primary keys and current order/fill foreign keys unchanged

Do not:
- rename core tables
- redesign order/fill schema
- change execution paths in this phase

**Step 2: Keep compatibility with current run callers**

Existing code paths such as:
- `run_configured_backtest()`
- doctor runtime setup
- paper/shadow/live run bookkeeping

must still be able to create `StrategyRun` rows without immediately requiring the full new catalog payload.

---

## Task 3: Expose useful query helpers for later phases

**Files:**
- Modify: `src/quant_os/db/store.py`

**Step 1: Add narrow helper methods**

Add only the minimum helpers needed for later phases, such as:
- `list_strategy_runs(limit, strategy_id=None, dataset=None, profile_id=None)`
- `get_strategy_run(run_id)` returning widened metadata

Avoid adding a generic query builder abstraction.

---

## Acceptance criteria

- migration applies cleanly to SQLite test DB and PostgreSQL-compatible schema shape
- old code paths can still create strategy runs
- new columns can distinguish two runs of the same strategy under different datasets/profiles
- no live runtime code is forced to understand multiple active strategies yet
