# Frontend Usability Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 처음 보는 사용자도 대시보드의 목적, 각 페이지의 역할, 다음 행동, 현재 제한사항을 이해할 수 있도록 프론트의 설명성과 안내 흐름을 다듬는다.

**Architecture:** 백엔드 계약은 유지하고, 프론트의 정보 위계와 카피, empty state, glossary/help block, 상태 설명을 중심으로 다듬는다. 새 기능을 과하게 늘리지 않고 기존 `PageIntro`, `SectionCard`, `StatePanel`, `OrderDetailDrawer`를 중심으로 사용자 언어를 일관되게 적용한다.

**Tech Stack:** React, TypeScript, Vite, TanStack Query, Testing Library, Vitest

---

### Task 1: Human-Friendly Copy Primitives

**Files:**
- Create: `frontend/src/lib/copy.ts`
- Modify: `frontend/src/components/StatusBar.tsx`
- Modify: `frontend/src/components/KillSwitchBanner.tsx`
- Modify: `frontend/src/components/StatePanel.tsx`
- Modify: `frontend/src/components/KpiCard.tsx`
- Test: `frontend/src/lib/api.test.ts`

**Step 1: Write the failing test**

Add copy helper tests for:
- mode explanation text
- humanized kill-switch reason labels
- glossary labels used by KPI cards

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- Fail because `frontend/src/lib/copy.ts` does not exist or exports are missing.

**Step 3: Write minimal implementation**

Create `frontend/src/lib/copy.ts` with pure helpers:
- `getModeExplanation(mode)`
- `humanizeKillSwitchReason(reason)`
- `KPI_COPY`

Then update:
- `frontend/src/components/StatusBar.tsx`
- `frontend/src/components/KillSwitchBanner.tsx`
- `frontend/src/components/StatePanel.tsx`
- `frontend/src/components/KpiCard.tsx`

So shared copy stops being duplicated across pages.

**Step 4: Run test to verify it passes**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/lib/copy.ts frontend/src/components/StatusBar.tsx frontend/src/components/KillSwitchBanner.tsx frontend/src/components/StatePanel.tsx frontend/src/components/KpiCard.tsx frontend/src/lib/api.test.ts
git commit -m "feat: centralize frontend copy helpers"
```

### Task 2: First-Run Guidance On Overview And Research

**Files:**
- Modify: `frontend/src/pages/OverviewPage.tsx`
- Modify: `frontend/src/pages/ResearchPage.tsx`
- Modify: `frontend/src/components/IngestionForm.tsx`
- Modify: `frontend/src/styles/app.css`
- Test: `frontend/src/app/App.test.tsx`

**Step 1: Write the failing test**

Add assertions that the app renders:
- a first-run checklist on Overview
- clearer data-ingestion wording on Research
- unit-specific label text for the ingestion form

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- FAIL on missing onboarding/help text.

**Step 3: Write minimal implementation**

Update:
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/ResearchPage.tsx`
- `frontend/src/components/IngestionForm.tsx`
- `frontend/src/styles/app.css`

Specific changes:
- keep the existing `Getting Started` block
- add one compact “What happens next” block to Research
- ensure all empty states on these pages end with a next action or expectation
- remove the remaining technical phrases like “records”, “projection”, “stub” where user-facing

**Step 4: Run test to verify it passes**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/OverviewPage.tsx frontend/src/pages/ResearchPage.tsx frontend/src/components/IngestionForm.tsx frontend/src/styles/app.css frontend/src/app/App.test.tsx
git commit -m "feat: improve first-run guidance on overview and research"
```

### Task 3: Make Orders Legible To Non-Experts

**Files:**
- Modify: `frontend/src/pages/OrdersPage.tsx`
- Modify: `frontend/src/components/OrderDetailDrawer.tsx`
- Test: `frontend/src/components/OrderDetailDrawer.test.tsx`

**Step 1: Write the failing test**

Extend drawer/page tests to assert:
- summary, timeline, and fills each explain what they mean
- no engineering-only wording remains in empty states

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- FAIL on missing help text or wording mismatch.

**Step 3: Write minimal implementation**

Update:
- `frontend/src/pages/OrdersPage.tsx`
- `frontend/src/components/OrderDetailDrawer.tsx`

Specific changes:
- add one short “How to read this page” sentence near the orders table
- explain timeline vs fills in plain language
- change remaining “recorded”/“append-only” wording if it reads like internal implementation rather than user guidance

**Step 4: Run test to verify it passes**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/OrdersPage.tsx frontend/src/components/OrderDetailDrawer.tsx frontend/src/components/OrderDetailDrawer.test.tsx
git commit -m "feat: improve order explainability for first-time users"
```

### Task 4: Clarify Reports And Controls

**Files:**
- Modify: `frontend/src/pages/ReportsPage.tsx`
- Modify: `frontend/src/pages/ControlsPage.tsx`
- Modify: `frontend/src/components/KillSwitchBanner.tsx`
- Modify: `frontend/src/components/StatusBar.tsx`
- Test: `frontend/src/app/App.test.tsx`

**Step 1: Write the failing test**

Add expectations for:
- report-reading guidance
- clearer controls/mode explanations
- humanized kill-switch text

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- FAIL because wording/help blocks are not yet present or have changed.

**Step 3: Write minimal implementation**

Update:
- `frontend/src/pages/ReportsPage.tsx`
- `frontend/src/pages/ControlsPage.tsx`
- `frontend/src/components/KillSwitchBanner.tsx`
- `frontend/src/components/StatusBar.tsx`

Specific changes:
- add “how to read reports” and “mode guide” sections
- map technical reasons into clearer user language
- make kill-switch alerts say what the user cannot do and where to look next

**Step 4: Run test to verify it passes**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/ReportsPage.tsx frontend/src/pages/ControlsPage.tsx frontend/src/components/KillSwitchBanner.tsx frontend/src/components/StatusBar.tsx frontend/src/app/App.test.tsx
git commit -m "feat: clarify reports and controls for new users"
```

### Task 5: Final Visual And Build Verification

**Files:**
- Modify: `frontend/src/styles/app.css`
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/components/OrderDetailDrawer.test.tsx`

**Step 1: Write the failing test**

If needed, add a final assertion that the new onboarding/help blocks render without breaking layout-critical content.

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- FAIL only if final copy/layout block is missing.

**Step 3: Write minimal implementation**

Polish spacing and hierarchy in:
- `frontend/src/styles/app.css`

Keep the UI read-mostly and avoid adding complex interaction patterns.

**Step 4: Run test to verify it passes**

Run:
```bash
cd frontend
npm test -- --run
npm run build
```

Expected:
- PASS
- build succeeds

**Step 5: Commit**

```bash
git add frontend/src/styles/app.css frontend/src/app/App.test.tsx frontend/src/components/OrderDetailDrawer.test.tsx
git commit -m "feat: finalize frontend usability polish"
```

### Task 6: Human Review Against The Running App

**Files:**
- No code required unless issues are found
- Reference: `docs/frontend_review_gemini_ux_2026-03-10.md`
- Reference: `docs/frontend_review_gemini_2026-03-10.md`

**Step 1: Start the app**

Run:
```bash
uv run quant-os serve-api --config conf/base.yaml --host 0.0.0.0 --port 8000
```

Expected:
- FastAPI serves both `/api` and the built frontend.

**Step 2: Open the running dashboard**

Open:
- `http://100.120.51.9:8000`
- or `http://lia-server.taila8b64d.ts.net:8000`

**Step 3: Check these scenarios manually**

- first load: can a new user tell where to start?
- empty state: does each page explain the next action?
- mode/status: is `paper/shadow/live` understandable?
- reports/controls: do the pages explain their purpose?
- order detail: is timeline vs fills understandable?

**Step 4: Fix only high-signal issues**

Touch:
- `frontend/src/pages/*.tsx`
- `frontend/src/components/*.tsx`
- `frontend/src/styles/app.css`

Then rerun:
```bash
cd frontend
npm test -- --run
npm run build
```

**Step 5: Commit**

```bash
git add frontend
git commit -m "feat: polish frontend copy after manual walkthrough"
```
