# Quant OS Phase 6d Backtest API List / Detail / Compare

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand the backtest read API from a single `latest` view into a minimal run explorer surface that supports strategy enumeration, backtest run listing, run detail, and compare.

**Architecture:** Keep the API thin and read-mostly. Reuse the new strategy catalog, operational run metadata, and artifact catalog. Preserve `GET /api/backtests/latest` as a compatibility route. Do not add job queues or long-running background execution in this phase.

**Tech Stack:** FastAPI, Pydantic v2, pytest

---

## Task 1: Write failing API tests

**Files:**
- Modify: `tests/integration/test_api_backtests.py`
- Create if needed: `tests/integration/test_api_strategies.py`

**Step 1: Write the failing test**

Require these endpoints:
- `GET /api/strategies`
- `GET /api/backtests/runs`
- `GET /api/backtests/runs/{run_id}`
- `POST /api/backtests/compare`
- compatibility: `GET /api/backtests/latest`

`GET /api/backtests/runs` should support light filters such as:
- `strategy_id`
- `dataset`
- `profile_id`
- `limit`

`POST /api/backtests/compare` should accept a small list of run ids and return a compare payload that includes at least summary metrics.

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --extra dev pytest tests/integration/test_api_backtests.py tests/integration/test_api_strategies.py -q
```

Expected:
- FAIL because only the latest endpoint exists today.

**Step 3: Write minimal implementation**

Implement the smallest read API surface needed for listing, detail, and compare.

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --extra dev pytest tests/integration/test_api_backtests.py tests/integration/test_api_strategies.py -q
```

Expected:
- PASS

---

## Task 2: Add API schemas and routes

**Files:**
- Modify: `src/quant_os/api/routes/backtests.py`
- Modify: `src/quant_os/api/schemas.py`
- Create if needed: `src/quant_os/api/routes/strategies.py`

**Step 1: Add strategy enumeration**

`GET /api/strategies` should return catalog-backed strategy metadata only.

Suggested fields:
- `strategy_id`
- `kind`
- `version`
- `description`
- `dataset_default`
- `tags`

**Step 2: Add run listing and detail**

Listing should be summary-first.
Detail may combine strategy-run metadata and artifact content.

**Step 3: Add compare**

Keep compare narrow:
- summary metrics only
- no fancy chart overlays required
- small request payload only

---

## Task 3: Keep existing frontend and clients compatible

**Files:**
- Verify only, or minimally update frontend tests if needed

**Step 1: Preserve `latest`**

Current frontend and manual workflows that call `GET /api/backtests/latest` must not break.

**Step 2: Defer UI expansion if needed**

If frontend wiring becomes too large, keep it out of this phase and document it as follow-up work.

---

## Acceptance criteria

- current clients using `/api/backtests/latest` keep working
- at least two runs can be listed and fetched individually
- compare can summarize multiple runs from the catalog
- no live-execution behavior changed in order to support the API
