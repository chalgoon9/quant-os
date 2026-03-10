# Quant OS Phase 6 Multi-Strategy Research / Backtest Expansion Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand `quant-os` from a single-strategy MVP into a multi-strategy **research/backtest** system, while preserving the current operational core and keeping live execution scope intentionally narrow.

**Architecture:** Keep the current modular-monolith and fail-closed boundaries. Do **not** turn the runtime into a multi-strategy live allocator. Instead, add a research-oriented strategy catalog, backtest request/profile abstraction, run catalog, and read APIs for list/detail/compare. Preserve `TargetExposure -> risk -> intent -> execution` and keep `paper / shadow / live` runtime behavior stable.

**Tech Stack:** Python 3.12+, Pydantic v2, SQLAlchemy 2.x, Alembic, DuckDB, PyArrow/Parquet, FastAPI, Typer, pytest

---

## Why this phase exists

The current repo intentionally optimized for one market / one strategy / one codebase. That was correct for the MVP. The next bottleneck is no longer the operational core itself, but the inability to register multiple strategies and compare them cleanly through the backtest path.

Current limitations that this phase addresses:
- `conf/base.yaml` contains one inlined `strategy` section.
- `run_configured_backtest()` instantiates `DailyMomentumStrategy` directly.
- backtest artifacts are effectively treated as `latest.json` first.
- API exposure is centered on `GET /api/backtests/latest`.

This phase deliberately changes **research/backtest ergonomics**, not live-trading scope.

---

## Non-goals

This phase does **not** do the following:
- multi-strategy live trading
- portfolio allocator across multiple active live strategies
- live hardening / restart-recovery deepening
- event bus / queue / microservice split
- plugin marketplaces or dynamic code loading
- replacing the current `conf/base.yaml` runtime path

---

## Hard invariants

1. Strategy code must continue to return `TargetExposure`, never submit orders directly.
2. `conf/base.yaml` must remain usable for the current doctor / paper / shadow / live runtime path.
3. `GET /api/backtests/latest` must keep working for compatibility.
4. The new work is additive first: schema widening, registry introduction, catalog APIs.
5. Multi-strategy research is allowed; multi-strategy live execution is deferred.
6. Avoid broad refactors that disturb paper/shadow/live behavior.

---

## Implementation order

Implement in this exact order:

1. **Phase 6a — schema migration for strategy/backtest catalog metadata**
2. **Phase 6b — strategy registry and strategy spec files**
3. **Phase 6c — backtest request/profile/orchestrator/catalog**
4. **Phase 6d — API list/detail/compare surface**

Do not start the next sub-phase until tests for the current one pass.

---

## Compatibility targets

After this phase, the following old paths must still work:

```bash
uv run quant-os doctor --config conf/base.yaml
uv run quant-os run-backtest --config conf/base.yaml --dataset krx_etf_daily
```

And this endpoint must still resolve:

```text
GET /api/backtests/latest
```

Legacy behavior may internally map to a catalog-backed default strategy/profile, but outward behavior should remain compatible.

---

## Deliverables

### Required deliverables
- widened `strategy_runs` schema and domain/store support
- strategy spec catalog under `conf/strategies/`
- explicit registry keyed by strategy `kind`
- backtest profiles under `conf/backtests/`
- `BacktestRequest` and orchestrator entrypoint
- artifact store that supports list/detail/compare in addition to `latest`
- read APIs for strategies and backtest runs
- tests for compatibility and new behavior

### Nice-to-have, but not required in this phase
- frontend run explorer wiring
- API-triggered backtest execution endpoint
- chart overlays for compare

---

## Suggested review checklist

Before merging, verify all of the following:
- legacy CLI still passes
- legacy `/api/backtests/latest` still passes
- at least 2 strategy specs can coexist without touching runtime live config
- at least 2 backtest profiles can compare the same strategy under different cost assumptions
- run metadata can answer: strategy / kind / dataset / profile / artifact path / config fingerprint
- no strategy layer gained order-submission power
- no live adapter behavior was broadened accidentally

---

## Sub-phase references

- `docs/plans/2026-03-10-phase-6a-schema-migration-for-backtest-catalog.md`
- `docs/plans/2026-03-10-phase-6b-strategy-registry.md`
- `docs/plans/2026-03-10-phase-6c-backtest-request-catalog.md`
- `docs/plans/2026-03-10-phase-6d-backtest-api-list-detail-compare.md`
