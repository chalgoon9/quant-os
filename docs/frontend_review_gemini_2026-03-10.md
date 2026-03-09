# Gemini Frontend Review

Date: 2026-03-10  
Reviewer: Gemini CLI  
Requested model: `gemini 3.1 pro`  
Applied model: `gemini-3.1-pro-preview`

## Setup Note

- Gemini CLI was installed locally at `/home/lia/.local/node_modules/.bin/gemini`.
- Gemini CLI auth/model defaults were configured via `~/.gemini/.env`.
- The Google API key was sourced from the local `opencode` auth store and not copied into this repository.
- `gemini-3.1-pro` was not exposed as a valid `generateContent` model for this API key on 2026-03-10, so the closest available model `gemini-3.1-pro-preview` was used instead.

## Review Scope

This review pass covered the frontend app shell and API client boundary:

- `frontend/src/app/App.tsx`
- `frontend/src/lib/api.ts`

## Gemini Output

### Findings

*   **Architecture & Tech Stack:** The frontend is a React application built with TypeScript and Vite, interacting with a backend (likely FastAPI, running on port 8000 by default). It uses `react-router-dom` for routing.
*   **API Client Design:** `frontend/src/lib/api.ts` implements a custom, strongly-typed HTTP client wrapping the native `fetch` API. It defines comprehensive TypeScript types for domain entities like Orders, Fills, Reconciliation, and Kill Switch events.
*   **State Management:** The custom hooks (`useRuntime`, `useKillSwitchActive`) return objects with properties like `.isLoading`, `.isError`, `.data`, and `.refetch()`. This API signature strongly suggests the use of a data-fetching library like TanStack Query (React Query) or SWR to manage server state.
*   **Resilient UI:** `App.tsx` uses conditional rendering to gracefully handle different loading states, displaying skeletons (`skeleton--status`) during fetch, an actionable error boundary (`StatePanel` with a retry button) on failure, and the actual `StatusBar` on success.
*   **Environment Configuration:** The API base URL correctly attempts to resolve from environment variables (`import.meta.env.VITE_API_BASE_URL`) before falling back to a constructed `localhost:8000` URL, facilitating easy transitions between local development, paper trading, and live deployments.

### Open Questions

*   **Real-time Updates:** Trading and operations dashboards rely heavily on real-time data. Are the hooks (like `useOrders` or `useKillSwitchActive`) currently using long polling, or is there an intention to add a WebSocket integration to stream updates for order events and kill switches?
*   **Authentication & Security:** There is no explicit handling of authentication headers (like Bearer tokens) or credential inclusions in the `requestJson` base function. Is this system intended to run purely locally/in a VPN without application-level auth, or does it rely on session cookies?
*   **Pagination:** The `getOrders` API function currently only accepts a `limit` parameter. How is historical data pagination (e.g., offsets or cursors) going to be handled as the order history grows?
*   **Timezone Handling:** The API DTOs use string-based timestamps (e.g., `occurred_at: string`). Is the frontend doing local timezone conversion, or is the backend strictly enforcing UTC ISO 8601 strings?

### Strengths

*   **Type Safety:** The domain models in `api.ts` (`OrderProjectionDto`, `ReconciliationResponse`, etc.) are well-defined and closely mirror what one would expect from a sophisticated trading backend, minimizing runtime data mapping errors.
*   **Clean Separation of Concerns:** API communication details (URL construction, HTTP methods, error parsing) are entirely decoupled from the UI components.
*   **Robust Error Handling:** The custom `ApiError` class safely attempts to parse backend JSON error structures while falling back to HTTP status codes. The `App.tsx` properly consumes these states to inform the user instead of breaking silently.
*   **Business-Focused Layout:** The routing and high-level component hierarchy (Overview, Orders, Research, Reports, Controls, KillSwitchBanner) perfectly aligns with the operational needs of an automated trading system (Ops Safety, Execution Ledger, etc., as outlined in the directory structure).

### Suggested Next Steps

*   **Add Pagination/Filtering Support:** Expand the `getOrders` (and similarly list-based) API calls to support `offset`, `cursor`, and filtering parameters (like `symbol` or `status`) to prepare for large datasets.
*   **Implement Global Error Intercepts:** While component-level error handling exists, consider adding a global API interceptor or query client config to handle cross-cutting concerns like displaying toasts for `500 Internal Server Error` or handling unauthorized states.
*   **Consider WebSocket/SSE Integration:** For features like the `KillSwitchBanner` and live `StatusBar`, migrate from simple fetching to WebSockets or Server-Sent Events (SSE) to ensure latency-sensitive alerts are pushed to the frontend immediately.
*   **Extend Testing:** Ensure `api.test.ts` covers the URL builder logic (especially edge cases with/without trailing slashes in env vars) and the JSON error parser inside `requestJson`.
