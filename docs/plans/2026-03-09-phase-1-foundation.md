# Quant OS Phase 1 Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Phase 1 project skeleton for Quant OS so the package imports, base config loads into domain models, the operational DB schema is migratable, and the codebase is ready for backtest/paper execution work.

**Architecture:** Use a modular-monolith Python package with a strict domain-first boundary. Keep strategy output limited to `TargetExposure`, model order/fill persistence as append-only events with `orders` as a projection, and wire configuration through explicit YAML parsed into typed domain/config objects. SQLAlchemy models and Alembic migration define the operational schema.

**Tech Stack:** Python 3.12, Pydantic v2, SQLAlchemy 2.x, Alembic, PyYAML, Typer, pytest

---

### Task 1: Package And Test Skeleton

**Files:**
- Create: `tests/unit/test_imports.py`
- Create: `tests/unit/test_config_loader.py`
- Create: `tests/unit/test_db_schema.py`
- Create: `tests/conftest.py`

**Step 1: Write the failing test**

Add tests that import `quant_os`, load `conf/base.yaml` through a public loader, and assert the SQLAlchemy metadata exposes the required tables.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_imports.py tests/unit/test_config_loader.py tests/unit/test_db_schema.py -q`
Expected: failures because package modules do not exist yet.

**Step 3: Write minimal implementation**

Create the package layout, public exports, and configuration/schema modules needed to satisfy the tests.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_imports.py tests/unit/test_config_loader.py tests/unit/test_db_schema.py -q`
Expected: all selected tests pass.

### Task 2: Domain Models And Config

**Files:**
- Create: `src/quant_os/domain/enums.py`
- Create: `src/quant_os/domain/ids.py`
- Create: `src/quant_os/domain/types.py`
- Create: `src/quant_os/domain/models.py`
- Create: `src/quant_os/config/models.py`
- Create: `src/quant_os/config/loader.py`
- Create: `conf/base.yaml`

**Step 1: Write the failing test**

Extend config tests to assert YAML values map into typed config/domain objects and that `TargetExposure` exists while strategy config does not produce `OrderIntent`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_config_loader.py -q`
Expected: failures on missing modules/classes.

**Step 3: Write minimal implementation**

Implement enums, IDs, core domain dataclasses/Pydantic models, and a fail-closed config loader.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_config_loader.py -q`
Expected: PASS.

### Task 3: DB Schema And Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/20260309_0001_phase1_foundation.py`
- Create: `src/quant_os/db/base.py`
- Create: `src/quant_os/db/schema.py`

**Step 1: Write the failing test**

Add a DB test that asserts required operational tables exist and a migration can be applied to a temporary SQLite database.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_db_schema.py -q`
Expected: FAIL because schema/migration are missing.

**Step 3: Write minimal implementation**

Define SQLAlchemy models and a matching initial Alembic revision.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_db_schema.py -q`
Expected: PASS.

### Task 4: CLI And README

**Files:**
- Create: `src/quant_os/cli/main.py`
- Create: `src/quant_os/__main__.py`
- Create: `README.md`
- Create: `pyproject.toml`

**Step 1: Write the failing test**

Add/import tests that require the package entrypoints to exist.

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_imports.py -q`
Expected: FAIL until entrypoints/package metadata are present.

**Step 3: Write minimal implementation**

Add the Typer CLI, package metadata, dependencies, README draft, and test configuration.

**Step 4: Run test to verify it passes**

Run: `pytest -q`
Expected: PASS for the Phase 1 unit skeleton.

### Task 5: Verification

**Files:**
- Verify only

**Step 1: Run package verification**

Run: `python -c "import quant_os; print(quant_os.__version__)"`
Expected: package imports successfully.

**Step 2: Run test verification**

Run: `pytest -q`
Expected: all Phase 1 tests pass.

**Step 3: Run migration verification**

Run: `python -m alembic upgrade head`
Expected: migration applies against the configured test/local database.
