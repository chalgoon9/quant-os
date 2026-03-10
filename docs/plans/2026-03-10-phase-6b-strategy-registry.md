# Quant OS Phase 6b Strategy Registry

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce a research-oriented strategy registry and strategy spec files so multiple strategies can be selected for backtesting without changing the current live runtime configuration path.

**Architecture:** Keep `conf/base.yaml` and `SystemConfig.strategy` for the current runtime path. Add a separate research/backtest strategy catalog under `conf/strategies/` and a small registry keyed by strategy `kind`. This is not a plugin framework; it is a typed in-repo registry.

**Tech Stack:** Pydantic v2, PyYAML, pytest

---

## Task 1: Write failing strategy registry tests

**Files:**
- Create: `tests/unit/test_strategy_registry.py`
- Modify if needed: `tests/unit/test_strategy_pipeline.py`

**Step 1: Write the failing test**

Require:
- loading a strategy spec from `conf/strategies/*.yaml`
- registry lookup by `kind`
- building a concrete strategy instance from the spec
- preserving `TargetExposure`-only output behavior
- loading at least two strategy specs simultaneously

Recommended first two specs:
- `kr_etf_momo_20_60_v1`
- `btc_4h_trend_volcap_v1`

If the second strategy is too large for this phase, start with two variants of momentum under distinct strategy ids.

**Step 2: Run test to verify it fails**

Run:
```bash
uv run --extra dev pytest tests/unit/test_strategy_registry.py tests/unit/test_strategy_pipeline.py -q
```

Expected:
- FAIL because registry/spec loading does not exist yet.

**Step 3: Write minimal implementation**

Implement only the registry/spec layer required by the tests.

**Step 4: Run test to verify it passes**

Run:
```bash
uv run --extra dev pytest tests/unit/test_strategy_registry.py tests/unit/test_strategy_pipeline.py -q
```

Expected:
- PASS

---

## Task 2: Add typed strategy specs without replacing runtime config

**Files:**
- Create: `src/quant_os/strategy/specs.py`
- Create: `src/quant_os/strategy/registry.py`
- Modify: `src/quant_os/strategy/__init__.py`
- Create: `conf/strategies/kr_etf_momo_20_60_v1.yaml`
- Create: `conf/strategies/kr_etf_momo_30_90_v1.yaml`

**Step 1: Define a narrow strategy spec model**

At minimum include:
- `strategy_id`
- `kind`
- `version`
- `description`
- `dataset_default`
- `universe`
- `rebalance_calendar`
- `params`
- `tags`

**Step 2: Keep registry simple**

Recommended shape:
- static in-code registry dictionary
- `register(kind, builder)`
- `build(spec, bars_by_symbol)`
- no runtime code loading
- no import strings in YAML

**Step 3: Preserve runtime separation**

Do not refactor the current live runtime to load these specs yet. The registry is for research/backtest selection first.

---

## Task 3: Make daily momentum a registry-backed reference strategy

**Files:**
- Modify: `src/quant_os/strategy/momentum.py`
- Create if useful: `src/quant_os/strategy/builders.py`

**Step 1: Keep the existing daily momentum strategy as the reference implementation**

Registry-backed construction should be able to produce the current momentum strategy from a spec.

**Step 2: Avoid leaking order logic**

Even with the registry in place, strategy output must remain `TargetExposure` only.

---

## Acceptance criteria

- current runtime config continues to work unchanged
- strategy specs can coexist under `conf/strategies/`
- at least two specs can be backtested without editing Python code
- registry remains explicit and in-repo, not plugin-like
