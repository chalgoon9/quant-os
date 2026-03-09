# Frontend Korean Localization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 프론트의 사용자 노출 문구를 영어 중심에서 한국어 중심으로 바꿔 처음 보는 사용자도 한글만으로 화면을 이해할 수 있게 만든다.

**Architecture:** 백엔드 API 계약과 내부 식별자는 유지하고, 프론트의 사용자 노출 텍스트만 한국어로 치환한다. 티커, strategy id, adapter class name, raw value 같은 시스템 식별자는 그대로 두고, 제목/설명/버튼/empty state/help text만 번역한다. 오버엔지니어링을 피하기 위해 i18n 프레임워크는 도입하지 않고 기존 페이지/컴포넌트 파일 안에서 직접 치환한다.

**Tech Stack:** React, TypeScript, Vite, TanStack Query, Vitest, Testing Library

---

### Task 1: 전역 공통 UI 문구 한글화

**Files:**
- Modify: `frontend/src/components/SidebarNav.tsx`
- Modify: `frontend/src/components/StatusBar.tsx`
- Modify: `frontend/src/components/KillSwitchBanner.tsx`
- Modify: `frontend/src/components/StatePanel.tsx`
- Modify: `frontend/src/components/PageIntro.tsx`
- Test: `frontend/src/app/App.test.tsx`

**Step 1: Write the failing test**

`frontend/src/app/App.test.tsx`에 아래 기대값을 추가한다.
- `Overview` 대신 `개요`
- `Research` 대신 `리서치`
- `Getting Started` 대신 `시작 가이드`
- 상태 설명문이 한국어로 노출되는지 확인

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- FAIL because current UI still renders English labels.

**Step 3: Write minimal implementation**

Update:
- `frontend/src/components/SidebarNav.tsx`
- `frontend/src/components/StatusBar.tsx`
- `frontend/src/components/KillSwitchBanner.tsx`
- `frontend/src/components/StatePanel.tsx`
- `frontend/src/components/PageIntro.tsx`

Translate only user-facing text:
- navigation labels
- page intro labels
- status bar labels
- kill switch banner action labels
- retry / close / generic state labels

Do not translate:
- `daily_momentum`
- `PaperAdapter`
- ticker symbols
- raw numeric values

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
git add frontend/src/components/SidebarNav.tsx frontend/src/components/StatusBar.tsx frontend/src/components/KillSwitchBanner.tsx frontend/src/components/StatePanel.tsx frontend/src/components/PageIntro.tsx frontend/src/app/App.test.tsx
git commit -m "feat: localize shared frontend chrome to korean"
```

### Task 2: Overview / Research / Orders 화면 한글화

**Files:**
- Modify: `frontend/src/pages/OverviewPage.tsx`
- Modify: `frontend/src/pages/ResearchPage.tsx`
- Modify: `frontend/src/pages/OrdersPage.tsx`
- Modify: `frontend/src/components/IngestionForm.tsx`
- Modify: `frontend/src/components/OrderDetailDrawer.tsx`
- Test: `frontend/src/components/OrderDetailDrawer.test.tsx`
- Test: `frontend/src/app/App.test.tsx`

**Step 1: Write the failing test**

Add expectations for Korean text:
- `Portfolio Snapshot` -> `포트폴리오 요약`
- `Market Data Preview` -> `시장 데이터 미리보기`
- `Recent Orders` -> `최근 주문`
- drawer 설명문 한국어 노출

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- FAIL on English page copy.

**Step 3: Write minimal implementation**

Update:
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/ResearchPage.tsx`
- `frontend/src/pages/OrdersPage.tsx`
- `frontend/src/components/IngestionForm.tsx`
- `frontend/src/components/OrderDetailDrawer.tsx`

Translate:
- section titles
- help text
- empty states
- form labels
- drawer guidance

Keep as-is:
- dataset names
- symbol filter raw input
- order ids / intent ids / fill ids

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
git add frontend/src/pages/OverviewPage.tsx frontend/src/pages/ResearchPage.tsx frontend/src/pages/OrdersPage.tsx frontend/src/components/IngestionForm.tsx frontend/src/components/OrderDetailDrawer.tsx frontend/src/components/OrderDetailDrawer.test.tsx frontend/src/app/App.test.tsx
git commit -m "feat: localize overview research and orders pages to korean"
```

### Task 3: Reports / Controls / 리스크 문구 한글화

**Files:**
- Modify: `frontend/src/pages/ReportsPage.tsx`
- Modify: `frontend/src/pages/ControlsPage.tsx`
- Modify: `frontend/src/lib/format.ts`
- Test: `frontend/src/app/App.test.tsx`

**Step 1: Write the failing test**

Add expectations for:
- `Reports` 설명 블록의 한국어 문구
- kill switch reason humanized Korean text
- controls mode guide 한국어 문구

**Step 2: Run test to verify it fails**

Run:
```bash
cd frontend
npm test -- --run
```

Expected:
- FAIL because the screen still contains English headings or English humanized reasons.

**Step 3: Write minimal implementation**

Update:
- `frontend/src/pages/ReportsPage.tsx`
- `frontend/src/pages/ControlsPage.tsx`
- `frontend/src/lib/format.ts`

Translate:
- report/help blocks
- reconciliation issue labels
- kill switch reason messages
- controls page mode guide

Keep as-is:
- API field semantics
- adapter names and strategy ids shown as raw identifiers where needed

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
git add frontend/src/pages/ReportsPage.tsx frontend/src/pages/ControlsPage.tsx frontend/src/lib/format.ts frontend/src/app/App.test.tsx
git commit -m "feat: localize reports and controls copy to korean"
```

### Task 4: 최종 정리와 실제 렌더 확인

**Files:**
- Modify: `frontend/src/styles/app.css` (only if Korean text wrapping causes layout issues)
- Test: `frontend/src/app/App.test.tsx`
- Test: `frontend/src/components/OrderDetailDrawer.test.tsx`

**Step 1: Run full frontend verification**

Run:
```bash
cd frontend
npm test -- --run
npm run build
```

Expected:
- PASS
- build succeeds

**Step 2: Start the integrated server**

Run:
```bash
uv run quant-os serve-api --config conf/base.yaml --host 0.0.0.0 --port 8000
```

Expected:
- frontend and API are served together

**Step 3: Manual walkthrough**

Check:
- 개요 / 주문 / 리서치 / 리포트 / 제어 화면 제목이 모두 한글인지
- 초면 사용자가 영어 없이도 의미를 이해할 수 있는지
- 긴 한국어 문장 때문에 카드 높이나 줄바꿈이 무너지는지

**Step 4: Minimal layout fix only if needed**

Touch only:
- `frontend/src/styles/app.css`

No new components, no new state, no i18n framework.

**Step 5: Commit**

```bash
git add frontend/src/styles/app.css frontend/src/app/App.test.tsx frontend/src/components/OrderDetailDrawer.test.tsx
git commit -m "feat: finalize korean localization polish"
```
