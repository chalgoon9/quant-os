# Quant OS Phase 3 Execution And Ledger Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Phase 3 execution layer so approved `OrderIntent` values can flow through a paper adapter, emit append-only order and fill events, update an order-state projection, and produce ledger/PnL projections from fills.

**Architecture:** Keep the source of truth append-only by modeling `order_events` and `fills` as immutable domain events and treating current order state as a projection. Implement a deterministic paper adapter that emits a valid state transition chain and fill events through the shared execution interface. Add a ledger projector that consumes events, tracks cash and inventory lots, and produces PnL snapshots without coupling strategy or intent logic to execution details.

**Tech Stack:** Python 3.12+, Pydantic v2, pytest

---

### Task 1: Write failing execution tests

**Files:**
- Create: `tests/unit/test_state_machine.py`
- Create: `tests/unit/test_paper_adapter.py`
- Create: `tests/unit/test_ledger.py`

**Step 1: Write the failing test**

Require:
- valid and invalid state transitions
- order projection derived from append-only order events and fills
- paper adapter submit/sync/portfolio flow
- ledger projector cash, positions, realized, unrealized, and total PnL output

**Step 2: Run test to verify it fails**

Run: `uv run --extra dev pytest tests/unit/test_state_machine.py tests/unit/test_paper_adapter.py tests/unit/test_ledger.py -q`
Expected: FAIL because Phase 3 modules do not exist yet.

**Step 3: Write minimal implementation**

Implement state machine, paper adapter, and ledger projector with only the behavior required by the tests.

**Step 4: Run test to verify it passes**

Run: `uv run --extra dev pytest tests/unit/test_state_machine.py tests/unit/test_paper_adapter.py tests/unit/test_ledger.py -q`
Expected: PASS.

### Task 2: Keep interfaces and projections aligned

**Files:**
- Modify: `src/quant_os/domain/models.py`
- Modify: `src/quant_os/domain/interfaces.py`
- Modify: `src/quant_os/cli/main.py`

**Step 1: Extend domain events/projections**

Add the smallest set of models needed for:
- order projection snapshots
- cash ledger entries
- position lots
- pnl snapshots

**Step 2: Keep source/projection separation explicit**

Ensure:
- order statuses still come from append-only events
- fills remain separate events
- strategy and risk layers stay unchanged

### Task 3: Verify the end-to-end paper path

**Files:**
- Verify only

**Step 1: Run the full suite**

Run: `uv run --extra dev pytest -q`
Expected: all Phase 1-3 tests pass.

**Step 2: Run runtime verification**

Run: `uv run quant-os doctor --config conf/base.yaml`
Expected: the runtime still validates after Phase 3 changes.
