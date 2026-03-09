# Phase 5 Shadow Live Skeleton Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a minimal Phase 5 shadow/live execution skeleton without over-engineering the existing paper-first architecture.

**Architecture:** Keep the existing `ExecutionAdapter` contract as the single execution seam. Add one shadow adapter that simulates orders without real submission and one fail-closed live stub that preserves the same interface. Wire runtime selection off `trading.mode` and add only the minimum reporting needed to validate shadow execution paths.

**Tech Stack:** Python 3.12+, Pydantic, SQLAlchemy, Typer, pytest

---

### Task 1: Add failing tests for shadow and live execution modes

**Files:**
- Create: `tests/shadow/test_shadow_adapter.py`
- Create: `tests/unit/test_live_adapter.py`
- Modify: `tests/unit/test_imports.py`

**Step 1: Write the failing test**
- Assert `ShadowAdapter` implements the same submit/sync/portfolio path and emits a dry-run report.
- Assert `StubLiveAdapter` fails closed on submit and keeps the interface stable.
- Assert runtime selection respects `trading.mode=shadow|live`.

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/shadow/test_shadow_adapter.py tests/unit/test_live_adapter.py tests/unit/test_imports.py -q`

Expected: FAIL because `ShadowAdapter`, `StubLiveAdapter`, and runtime mode wiring do not exist yet.

### Task 2: Add minimal execution adapters

**Files:**
- Create: `src/quant_os/adapters/shadow.py`
- Create: `src/quant_os/adapters/live.py`
- Modify: `src/quant_os/adapters/__init__.py`

**Step 1: Write minimal implementation**
- `ShadowAdapter` wraps `PaperAdapter`, preserves the `ExecutionAdapter` contract, and records a minimal shadow run report.
- `LiveAdapterBase` provides a small shared base for event log and portfolio state.
- `StubLiveAdapter` rejects submissions fail-closed until a real broker adapter exists.

**Step 2: Run tests**

Run: `uv run --extra dev pytest tests/shadow/test_shadow_adapter.py tests/unit/test_live_adapter.py -q`

Expected: PASS

### Task 3: Wire runtime selection by mode

**Files:**
- Modify: `src/quant_os/services/wiring.py`
- Modify: `src/quant_os/cli/main.py`

**Step 1: Write minimal implementation**
- Rename runtime field to `execution_adapter`.
- Select `PaperAdapter`, `ShadowAdapter`, or `StubLiveAdapter` from `trading.mode`.
- Keep `doctor` output mode-aware and report the chosen adapter class.

**Step 2: Run tests**

Run: `uv run --extra dev pytest tests/unit/test_imports.py -q`

Expected: PASS

### Task 4: Update documentation and re-run full verification

**Files:**
- Modify: `README.md`

**Step 1: Update docs**
- Describe the new Phase 5 skeleton scope and clarify that live remains stubbed and fail-closed.

**Step 2: Run verification**

Run: `uv run --extra dev pytest -q`
Run: `uv run quant-os doctor --config conf/base.yaml`

Expected: PASS and doctor reports the execution adapter for the current mode.
