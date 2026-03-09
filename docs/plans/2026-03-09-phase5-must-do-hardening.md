# Phase 5 Must-Do Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the minimum remaining gaps that matter before meaningful shadow validation or tiny-live preparation.

**Architecture:** Keep the modular-monolith structure and existing contracts. Add only small extensions to the shadow adapter, state machine, and kill switch so simulation tests and venue-rule checks exist without introducing a new framework.

**Tech Stack:** Python 3.12+, pytest, Pydantic, SQLAlchemy

---

### Task 1: Add failing tests for shadow venue rules and simulation edge cases

**Files:**
- Modify: `tests/shadow/test_shadow_adapter.py`
- Create: `tests/simulation/test_execution_simulation.py`
- Modify: `tests/unit/test_kill_switch.py`

**Step 1: Write failing tests**
- Shadow rejects orders that violate lot-size or minimum-notional venue rules.
- Simulation covers timeout, duplicate fill, out-of-order events, restart/recovery, and kill-switch trigger.
- Kill switch supports event-write-failure and duplicate-intent reasons.

**Step 2: Run tests to verify failure**

Run: `uv run --extra dev pytest tests/shadow/test_shadow_adapter.py tests/simulation/test_execution_simulation.py tests/unit/test_kill_switch.py -q`

Expected: FAIL because venue constraints and the extra kill-switch/state-machine behaviors do not exist yet.

### Task 2: Implement minimal shadow venue checks and simulation guards

**Files:**
- Modify: `src/quant_os/adapters/shadow.py`
- Modify: `src/quant_os/execution/state_machine.py`
- Modify: `src/quant_os/services/wiring.py`

**Step 1: Write minimal implementation**
- Add lot-size and minimum-notional checks in shadow mode.
- Reject duplicate fill IDs.
- Reject out-of-order transitions and fills.
- Keep restart/recovery validation store-based, not via a new replay framework.

**Step 2: Run targeted tests**

Run: `uv run --extra dev pytest tests/shadow/test_shadow_adapter.py tests/simulation/test_execution_simulation.py -q`

Expected: PASS

### Task 3: Extend kill switch with must-have fail-closed reasons

**Files:**
- Modify: `src/quant_os/risk/kill_switch.py`
- Modify: `tests/unit/test_kill_switch.py`

**Step 1: Write minimal implementation**
- Add explicit trigger helpers for event-write-failure, duplicate-intent, and unknown-open-order paths.

**Step 2: Run targeted tests**

Run: `uv run --extra dev pytest tests/unit/test_kill_switch.py -q`

Expected: PASS

### Task 4: Full verification and docs touch-up

**Files:**
- Modify: `README.md`

**Step 1: Verify**

Run: `uv run --extra dev pytest -q`
Run: `uv run quant-os doctor --config conf/base.yaml`

Expected: PASS
