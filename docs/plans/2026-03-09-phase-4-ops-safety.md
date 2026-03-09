# Quant OS Phase 4 Operations Safety Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Phase 4 operational safety layer so the system can reconcile local state against external state, fail closed through a kill switch when critical conditions occur, and generate a daily operating report from ledger and reconciliation outputs.

**Architecture:** Keep reconciliation, kill switch, and reporting downstream of execution and ledger. Reconciliation compares local portfolio/order projections to external snapshots and emits structured mismatch results. Kill switch evaluates those results plus PnL/data freshness thresholds and blocks new orders when active. Daily reports summarize positions, cash, PnL, reconciliation health, and active kill-switch state without coupling back into strategy or execution code.

**Tech Stack:** Python 3.12+, Pydantic v2, pytest

---

### Task 1: Write failing safety/reporting tests

**Files:**
- Create: `tests/unit/test_reconciliation.py`
- Create: `tests/unit/test_kill_switch.py`
- Create: `tests/unit/test_daily_report.py`

**Step 1: Write the failing test**

Require:
- reconciliation match/mismatch detection
- fail-closed kill switch activation and reset
- daily report generation from ledger snapshot, reconciliation result, and kill switch events

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/unit/test_reconciliation.py tests/unit/test_kill_switch.py tests/unit/test_daily_report.py -q`
Expected: FAIL because Phase 4 modules do not exist yet.

**Step 3: Write minimal implementation**

Implement the smallest reconciliation service, kill switch service, and daily report generator that satisfy the tests and align with the spec.

**Step 4: Run test to verify it passes**

Run: `uv run --extra dev pytest tests/unit/test_reconciliation.py tests/unit/test_kill_switch.py tests/unit/test_daily_report.py -q`
Expected: PASS.

### Task 2: Extend config/runtime only where needed

**Files:**
- Modify: `conf/base.yaml`
- Modify: `src/quant_os/config/models.py`
- Modify: `src/quant_os/domain/models.py`
- Modify: `src/quant_os/services/wiring.py`

**Step 1: Add explicit control thresholds**

Expose only the thresholds needed now:
- reconciliation cash tolerance
- reconciliation position tolerance
- stale market data threshold

**Step 2: Keep fail-closed behavior explicit**

Kill switch should default to blocking new orders whenever an active event exists.

### Task 3: Verify the Phase 1-4 runtime

**Files:**
- Verify only

**Step 1: Run the full suite**

Run: `uv run --extra dev pytest -q`
Expected: all tests pass.

**Step 2: Run runtime verification**

Run: `uv run quant-os doctor --config conf/base.yaml`
Expected: runtime still validates and surfaces reconciliation/kill-switch/reporting wiring.
