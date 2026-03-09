# Gemini UX Review For Frontend

Date: 2026-03-10  
Reviewer: Gemini CLI  
Requested model: `gemini 3.1 pro`  
Applied model: `gemini-3.1-pro-preview`

## Setup Note

- Gemini CLI was installed locally at `/home/lia/.local/node_modules/.bin/gemini`.
- Gemini auth/model defaults were configured via `~/.gemini/.env`.
- The Google API key was sourced from the local `opencode` auth store and was not copied into this repository.
- `gemini-3.1-pro` was not available as a usable `generateContent` model for this API key on 2026-03-10, so `gemini-3.1-pro-preview` was used.

## Review Scope

This pass focused on first-time user friendliness and explanatory clarity.

- `docs/frontend_screen_spec.md`
- `frontend/src/app/App.tsx`
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/ResearchPage.tsx`
- `frontend/src/pages/OrdersPage.tsx`
- `frontend/src/pages/ReportsPage.tsx`
- `frontend/src/pages/ControlsPage.tsx`
- `frontend/src/components/SidebarNav.tsx`
- `frontend/src/components/StatusBar.tsx`
- `frontend/src/components/KillSwitchBanner.tsx`
- `frontend/src/components/IngestionForm.tsx`
- `frontend/src/components/StatePanel.tsx`
- `frontend/src/components/SectionCard.tsx`
- `frontend/src/components/KpiCard.tsx`

## Gemini Output

### 1. Findings

**High Severity: Dense, Unexplained Domain Jargon**
- `frontend/src/pages/OverviewPage.tsx`: The KPI cards use heavy financial jargon without tooltips or explanations (e.g., "NAV", "Realized PnL", "Unrealized PnL"). Non-expert users will not know what these acronyms stand for.
- `frontend/src/pages/ResearchPage.tsx`: The term "Bars Preview" uses domain-specific trading terminology. A layperson is unlikely to know that "Bars" refers to market data rows or candlestick data.
- `frontend/src/pages/OrdersPage.tsx`: The empty state text reads "No order projection rows are available yet." "Projection rows" is technical implementation language rather than user-facing terminology.
- `frontend/src/pages/ControlsPage.tsx`: The mode notice states, "Live mode is currently a fail-closed stub." This is backend engineering jargon that will confuse users trying to understand if they can trade.

**High Severity: Dead-End Empty States**
- `frontend/src/pages/OverviewPage.tsx`: Several empty states tell the user something is missing but fail to provide a next step. For example, "Position API is not connected yet" and "No reconciliation log has been written yet." A first-time user won't know if they need to click a button, wait for a cron job, or change a configuration file.
- `frontend/src/pages/OrdersPage.tsx`: "No orders yet" doesn't explain how orders are generated (e.g., "Orders will appear here automatically when your strategy executes").

**Medium Severity: Missing Form Field Context**
- `frontend/src/components/IngestionForm.tsx`: The "Count" input field has a default of "30", but no unit of measurement is provided. The user does not know if they are requesting 30 days, 30 minutes, or 30 individual data points.

**Medium Severity: Lack of Page-Level Context**
- `frontend/src/components/SidebarNav.tsx`: While there is a brief global description ("Read-mostly dashboard..."), individual pages lack introductory text.
- `frontend/src/pages/ReportsPage.tsx`: Users are dropped into "Reconciliation Detail" without an explanation of what the system is reconciling (e.g., internal ledger vs. external broker).

### 2. Open Questions

- **Actionability of Integrations:** For empty states like "External broker sync is not yet connected" and "Position API is not connected yet", are these configurations meant to be handled via the UI eventually, or are they strictly backend `.env` configurations? If the latter, should the UI provide instructions on which file to edit?
- **Ingestion Units:** What exactly does the `count` parameter map to in the Upbit ingestion job? Days? Hours?
- **Trigger Mechanisms:** Are reconciliation logs and daily reports generated on an automated schedule, or is there a missing manual "Generate" button that the user is supposed to click?
- **Financial Literacy Expectations:** Can we assume some basic financial knowledge over time, or should we include a permanent glossary/tooltip system for terms like NAV and PnL?

### 3. Strengths

- **Consistent and Actionable Error Handling:** The use of the `StatePanel` component across all pages ensures that whenever data fails to load, the user receives a clean, consistent error message paired with a functional "Retry" button.
- **Highly Visible System State:** The global `StatusBar` and `KillSwitchBanner` provide exceptional situational awareness. The color-coding strategy (paper/shadow/live) outlined in the spec makes it very clear to users what environment they are operating in, reducing the risk of accidental live trades.
- **Approachable Information Hierarchy:** The use of `SectionCard` with clear "eyebrow" tags and titles breaks dense data into digestible, scannable blocks.
- **Helpful "Next Step" in Research:** The Research page has a great empty state: "Run an ingestion job to create a dataset." This clearly tells the user exactly what to do to populate the view.

### 4. Suggested UX Fixes

- **Translate Jargon:**
  - Change "Bars Preview" to "Market Data Preview" or "Price History".
  - Change "fail-closed stub" to "Live trading is currently disabled for safety."
  - Change "order projection rows" to simply "orders".
- **Add Tooltips to KPIs:** Introduce a small info icon next to labels like "NAV" and "PnL" that explains them on hover (e.g., "Net Asset Value: The total value of all cash and open positions").
- **Clarify Ingestion Inputs:** Update the `IngestionForm` field label to include units, such as `Count (days)` or `Number of records`.
- **Improve Dead-End Empty States:** Update non-actionable empty states to explain why they are empty and how they get filled. For example, change "No reconciliation log has been written yet" to "Reconciliation logs will appear here after the daily system audit runs."
- **Add Page Introductions:** Add a brief subtitle or introductory text block to complex pages (like Reports and Controls) explaining the goal of the page (e.g., "Review daily performance summaries and system audit logs.").
