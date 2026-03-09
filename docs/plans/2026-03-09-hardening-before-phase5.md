# Quant OS Hardening Before Phase 5 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the minimum operational hardening needed before Phase 5 so append-only execution/ledger/reconciliation/kill-switch data is actually persisted, and paper execution can exercise non-ideal paths such as partial fills and reconcile-pending states.

**Architecture:** Keep the existing modular-monolith shape and avoid new services or abstractions that do not directly improve operational fidelity. Add a small SQLAlchemy-backed operational store that persists domain events and projections into the existing schema, wire it into the paper adapter and safety services as an optional dependency, and extend the paper adapter with only two extra modes: partial fill and uncertain submit.

**Tech Stack:** Python 3.12+, SQLAlchemy 2.x, pytest

---

### Task 1: Write failing hardening tests

**Files:**
- Create: `tests/unit/test_operational_store.py`
- Modify: `tests/unit/test_paper_adapter.py`
- Modify: `tests/unit/test_reconciliation.py`

**Step 1: Write the failing test**

Require:
- append-only order/fill persistence and projection persistence in the operational DB
- paper adapter partial-fill path
- paper adapter reconcile-pending path for uncertain submit
- reconciliation and kill-switch events persisted to the operational DB

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/unit/test_operational_store.py tests/unit/test_paper_adapter.py tests/unit/test_reconciliation.py -q`
Expected: FAIL because the persistence layer and new execution paths do not exist yet.

**Step 3: Write minimal implementation**

Implement the smallest operational store and optional wiring needed to satisfy the tests.

**Step 4: Run test to verify it passes**

Run: `uv run --extra dev pytest tests/unit/test_operational_store.py tests/unit/test_paper_adapter.py tests/unit/test_reconciliation.py -q`
Expected: PASS.

### Task 2: Keep hardening scope tight

**Files:**
- Create: `src/quant_os/db/store.py`
- Modify: `src/quant_os/adapters/paper.py`
- Modify: `src/quant_os/reconciliation/service.py`
- Modify: `src/quant_os/risk/kill_switch.py`
- Modify: `src/quant_os/services/wiring.py`

**Step 1: Persist only the operational records already present in the schema**

Do not introduce queues, background workers, or event buses.

**Step 2: Expose only the minimal execution knobs**

Support:
- full fill
- partial fill
- uncertain submit -> `RECONCILE_PENDING`

### Task 3: Verify everything still holds

**Files:**
- Verify only

**Step 1: Run the full suite**

Run: `uv run --extra dev pytest -q`
Expected: all tests pass.

**Step 2: Run runtime verification**

Run: `uv run quant-os doctor --config conf/base.yaml`
Expected: runtime still validates after the hardening changes.
