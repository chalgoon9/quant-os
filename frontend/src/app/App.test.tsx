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

    expect(await screen.findByRole("link", { name: "개요" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "리서치" })).toBeInTheDocument();
    expect(await screen.findByText("킬 스위치 활성화")).toBeInTheDocument();
    expect(await screen.findByText("섀도 검증 실행")).toBeInTheDocument();
    expect(await screen.findByText("daily_momentum")).toBeInTheDocument();
    expect(await screen.findByText("처음 시작하기")).toBeInTheDocument();
    expect(await screen.findByText("순자산가치(NAV)")).toBeInTheDocument();
    expect(
      await screen.findByText(
        "신규 주문이 중단되어 있습니다. 원인: 안전 점검에서 기록 불일치가 확인됨.",
        { exact: false },
      ),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "섀도 모드는 실제 주문 없이 의사결정 흐름만 따라가며 결과를 점검하는 용도입니다.",
      ),
    ).toBeInTheDocument();
  });
});
