# Frontend Ops Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a minimal frontend-ready ops dashboard stack for `quant-os` with a thin FastAPI backend and a read-mostly React frontend.

**Architecture:** Add a small FastAPI layer inside `src/quant_os/api` that reuses existing runtime, `ResearchStore`, `OperationalStore`, reporting, and Upbit ingestion code. Add a separate `frontend/` app that consumes only those internal HTTP endpoints and focuses on overview, research, and report views first.

**Tech Stack:** FastAPI, Pydantic, Typer-compatible runtime wiring, React, Vite, TypeScript, TanStack Query

---

### Task 1: Add failing tests for the first backend API surface

**Files:**
- Create: `tests/integration/test_api_system_ops.py`
- Modify: `pyproject.toml`

**Step 1: Write the failing test**

Test these routes:

- `GET /api/system/runtime`
- `GET /api/ops/summary`
- `GET /api/ops/kill-switch/active`
- `GET /api/ops/reconciliation/latest`

Use FastAPI `TestClient` and assert:

- JSON payload exists
- mode/adapter/runtime values are correct
- error handling is explicit when snapshots are missing

**Step 2: Run test to verify it fails**

Run:

```bash
uv run --extra dev pytest tests/integration/test_api_system_ops.py -q
```

Expected:

- FAIL because `quant_os.api.main` and backend routes do not exist yet.

**Step 3: Write minimal implementation**

Add FastAPI app skeleton, route files, and minimal response schemas.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run --extra dev pytest tests/integration/test_api_system_ops.py -q
```

Expected:

- PASS

### Task 2: Add research API and Upbit ingestion API

**Files:**
- Create: `tests/integration/test_api_research.py`
- Create: `src/quant_os/api/routes/research.py`
- Modify: `src/quant_os/research_store/store.py`
- Modify: `src/quant_os/api/schemas.py`

**Step 1: Write the failing test**

Cover:

- `GET /api/research/datasets`
- `GET /api/research/datasets/{dataset}/bars`
- `POST /api/research/ingestion/upbit/daily`

Assert:

- dataset enumeration works
- bar preview is limited and ordered
- ingestion endpoint returns dataset/path payload

**Step 2: Run test to verify it fails**

Run:

```bash
uv run --extra dev pytest tests/integration/test_api_research.py -q
```

Expected:

- FAIL because dataset enumeration helpers and research routes do not exist yet.

**Step 3: Write minimal implementation**

Add:

- `ResearchStore.list_datasets()`
- `ResearchStore.sample_bars(...)`
- research routes and request/response schemas

**Step 4: Run test to verify it passes**

Run:

```bash
uv run --extra dev pytest tests/integration/test_api_research.py -q
```

Expected:

- PASS

### Task 3: Add order and report API surface

**Files:**
- Create: `tests/integration/test_api_orders_reports.py`
- Create: `src/quant_os/api/routes/ops.py`
- Create: `src/quant_os/api/routes/reports.py`
- Modify: `src/quant_os/db/store.py`
- Modify: `src/quant_os/api/schemas.py`

**Step 1: Write the failing test**

Cover:

- `GET /api/ops/orders`
- `GET /api/ops/orders/{order_id}`
- `GET /api/reports/daily/latest`

Assert:

- recent order list loads from persisted projections
- order detail includes projection/events/fills
- daily report endpoint returns markdown and top-level fields

**Step 2: Run test to verify it fails**

Run:

```bash
uv run --extra dev pytest tests/integration/test_api_orders_reports.py -q
```

Expected:

- FAIL because recent order listing and daily report endpoint do not exist yet.

**Step 3: Write minimal implementation**

Add:

- `OperationalStore.list_recent_orders(limit=...)`
- report route that generates latest daily report on demand

**Step 4: Run test to verify it passes**

Run:

```bash
uv run --extra dev pytest tests/integration/test_api_orders_reports.py -q
```

Expected:

- PASS

### Task 4: Add frontend app skeleton

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/app/App.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useRuntime.ts`
- Create: `frontend/src/hooks/useOpsSummary.ts`
- Create: `frontend/src/styles/app.css`

**Step 1: Create the frontend shell**

Add:

- Vite React TypeScript app
- app frame
- top navigation
- API base URL config

**Step 2: Verify it boots**

Run:

```bash
cd frontend && npm install
cd frontend && npm run build
```

Expected:

- build succeeds

### Task 5: Implement Overview page

**Files:**
- Create: `frontend/src/pages/OverviewPage.tsx`
- Create: `frontend/src/components/KpiCard.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Modify: `frontend/src/app/App.tsx`

**Step 1: Build the overview screen**

Render:

- mode / strategy / venue / execution adapter
- NAV / cash / PnL cards
- reconciliation summary
- kill switch badge

**Step 2: Verify manually**

Run:

```bash
cd frontend && npm run dev
```

Expected:

- overview page renders against local backend

### Task 6: Implement Research page

**Files:**
- Create: `frontend/src/pages/ResearchPage.tsx`
- Create: `frontend/src/hooks/useDatasets.ts`
- Create: `frontend/src/hooks/useDatasetBars.ts`
- Create: `frontend/src/hooks/useIngestUpbitDaily.ts`
- Create: `frontend/src/components/IngestionForm.tsx`

**Step 1: Build research page**

Render:

- dataset list
- latest bar table
- Upbit ingestion form

**Step 2: Verify manually**

Run:

```bash
cd frontend && npm run dev
```

Expected:

- dataset list loads
- ingestion form triggers backend mutation

### Task 7: Implement Orders and Reports pages

**Files:**
- Create: `frontend/src/pages/OrdersPage.tsx`
- Create: `frontend/src/pages/ReportsPage.tsx`
- Create: `frontend/src/hooks/useOrders.ts`
- Create: `frontend/src/hooks/useOrderDetail.ts`
- Create: `frontend/src/hooks/useDailyReport.ts`

**Step 1: Build pages**

Orders:

- recent order table
- order detail drawer

Reports:

- daily report markdown
- reconciliation summary

**Step 2: Verify manually**

Run:

```bash
cd frontend && npm run dev
```

Expected:

- orders and reports pages load

### Task 8: Add docs and run full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/frontend_ops_dashboard_design.md`

**Step 1: Update docs**

Add:

- backend start command
- frontend start command
- screen scope

**Step 2: Run backend verification**

Run:

```bash
uv run --extra dev pytest -q
uv run quant-os doctor --config conf/base.yaml
```

Expected:

- PASS

**Step 3: Run frontend verification**

Run:

```bash
cd frontend && npm run build
```

Expected:

- PASS
