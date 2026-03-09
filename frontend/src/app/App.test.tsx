import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "./App";

function createJsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString();

        if (url.endsWith("/system/runtime")) {
          return Promise.resolve(
            createJsonResponse({
              mode: "shadow",
              venue: "upbit",
              strategy: "daily_momentum",
              execution_adapter: "ShadowAdapter",
              base_currency: "KRW",
              research_dataset: "upbit_krw_btc_daily",
            }),
          );
        }

        if (url.endsWith("/ops/summary")) {
          return Promise.resolve(
            createJsonResponse({
              nav: "100145.0000",
              cash_balance: "99425.0000",
              realized_pnl: "31.0000",
              unrealized_pnl: "114.0000",
              total_pnl: "145.0000",
              reconciliation_status: "matched",
              reconciliation_summary: "reconciliation matched",
              active_kill_switch_reasons: ["reconciliation_failure"],
            }),
          );
        }

        if (url.endsWith("/ops/kill-switch/active")) {
          return Promise.resolve(
            createJsonResponse({
              items: [
                {
                  event_id: "killsw_1",
                  reason: "reconciliation_failure",
                  triggered_at: "2026-03-10T00:00:00+00:00",
                  trigger_value: "1.000000",
                  threshold_value: "0.000000",
                  details: { summary: "cash mismatch" },
                  is_active: true,
                  cleared_at: null,
                },
              ],
            }),
          );
        }

        if (url.endsWith("/ops/reconciliation/latest")) {
          return Promise.resolve(
            createJsonResponse({
              reconciliation_id: "recon_1",
              occurred_at: "2026-03-10T00:00:00+00:00",
              status: "mismatch",
              mismatch_count: 1,
              requires_manual_intervention: true,
              summary: "cash mismatch",
              issues: [
                {
                  code: "cash_mismatch",
                  message: "cash mismatch",
                  details: { expected: "100", actual: "99" },
                },
              ],
            }),
          );
        }

        return Promise.resolve(createJsonResponse({ items: [] }));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders global navigation, runtime status, and kill switch banner", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter
          future={{
            v7_relativeSplatPath: true,
            v7_startTransition: true,
          }}
          initialEntries={["/"]}
        >
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("link", { name: "Overview" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Research" })).toBeInTheDocument();
    expect(await screen.findByText("KILL SWITCH ACTIVE")).toBeInTheDocument();
    expect(await screen.findByText("ShadowAdapter")).toBeInTheDocument();
    expect(await screen.findByText("daily_momentum")).toBeInTheDocument();
  });
});
