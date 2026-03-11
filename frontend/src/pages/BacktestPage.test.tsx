import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";

import { BacktestPage } from "./BacktestPage";

function createJsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

describe("BacktestPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
        const url = input.toString();

        if (url.endsWith("/strategies")) {
          return Promise.resolve(
            createJsonResponse({
              items: [
                {
                  strategy_id: "kr_etf_momo_20_60_v1",
                  kind: "daily_momentum",
                  version: "v1",
                  description: "국내 ETF 일봉 20/60 모멘텀 참조 전략",
                  dataset_default: "krx_etf_daily",
                  tags: ["krx", "momentum"],
                },
                {
                  strategy_id: "kr_etf_momo_30_90_v1",
                  kind: "daily_momentum",
                  version: "v1",
                  description: "국내 ETF 일봉 30/90 모멘텀 변형 전략",
                  dataset_default: "krx_etf_daily",
                  tags: ["krx", "momentum"],
                },
              ],
            }),
          );
        }

        if (url.includes("/backtests/runs/run_1")) {
          return Promise.resolve(
            createJsonResponse({
              summary: {
                run_id: "run_1",
                strategy_id: "kr_etf_momo_20_60_v1",
                strategy_name: "국내 ETF 일봉 20/60 모멘텀 참조 전략",
                strategy_kind: "daily_momentum",
                strategy_version: "v1",
                dataset: "krx_etf_daily",
                profile_id: "baseline",
                generated_at: "2026-03-10T00:00:00+00:00",
                as_of: "2026-03-09T00:00:00+00:00",
                initial_cash: "10000000.0000",
                final_nav: "10500000.0000",
                total_return: "0.0500",
                max_drawdown: "-0.0200",
                total_turnover: "0.1200",
                total_commission: "1234.0000",
                total_tax: "0.0000",
                total_slippage_cost: "456.0000",
                total_traded_notional: "12000000.0000",
                trade_count: 12,
                loaded_symbols: ["069500", "114800"],
                missing_symbols: [],
              },
              equity_curve: [
                { timestamp: "2026-03-08T00:00:00+00:00", nav: "10000000.0000", cash: "10000000.0000" },
                { timestamp: "2026-03-09T00:00:00+00:00", nav: "10500000.0000", cash: "2500000.0000" },
              ],
              drawdown_curve: [
                { timestamp: "2026-03-08T00:00:00+00:00", drawdown: "0.0000" },
                { timestamp: "2026-03-09T00:00:00+00:00", drawdown: "-0.0200" },
              ],
              position_path: [
                { timestamp: "2026-03-08T00:00:00+00:00", positions: [] },
                {
                  timestamp: "2026-03-09T00:00:00+00:00",
                  positions: [
                    {
                      symbol: "069500",
                      quantity: "10.0000",
                      market_price: "100.0000",
                      market_value: "1000.0000",
                      weight: "0.1000",
                    },
                  ],
                },
              ],
              trades: [
                {
                  timestamp: "2026-03-09T00:00:00+00:00",
                  symbol: "069500",
                  side: "buy",
                  quantity: "10.0000",
                  price: "100.0000",
                  notional: "1000.0000",
                },
              ],
              parameter_report: {
                request: { strategy_id: "kr_etf_momo_20_60_v1" },
                profile: { profile_id: "baseline" },
              },
            }),
          );
        }

        if (url.includes("/backtests/runs/run_2")) {
          return Promise.resolve(
            createJsonResponse({
              summary: {
                run_id: "run_2",
                strategy_id: "kr_etf_momo_30_90_v1",
                strategy_name: "국내 ETF 일봉 30/90 모멘텀 변형 전략",
                strategy_kind: "daily_momentum",
                strategy_version: "v1",
                dataset: "krx_etf_daily",
                profile_id: "stress_10bps",
                generated_at: "2026-03-11T00:00:00+00:00",
                as_of: "2026-03-10T00:00:00+00:00",
                initial_cash: "10000000.0000",
                final_nav: "10300000.0000",
                total_return: "0.0300",
                max_drawdown: "-0.0300",
                total_turnover: "0.0900",
                total_commission: "1000.0000",
                total_tax: "0.0000",
                total_slippage_cost: "300.0000",
                total_traded_notional: "9000000.0000",
                trade_count: 8,
                loaded_symbols: ["069500"],
                missing_symbols: [],
              },
              equity_curve: [],
              drawdown_curve: [],
              position_path: [],
              trades: [],
              parameter_report: {
                request: { strategy_id: "kr_etf_momo_30_90_v1" },
                profile: { profile_id: "stress_10bps" },
              },
            }),
          );
        }

        if (url.includes("/backtests/runs")) {
          return Promise.resolve(
            createJsonResponse({
              items: [
                {
                  run_id: "run_1",
                  strategy_id: "kr_etf_momo_20_60_v1",
                  strategy_name: "국내 ETF 일봉 20/60 모멘텀 참조 전략",
                  strategy_kind: "daily_momentum",
                  strategy_version: "v1",
                  dataset: "krx_etf_daily",
                  profile_id: "baseline",
                  status: "succeeded",
                  started_at: "2026-03-10T00:00:00+00:00",
                  finished_at: "2026-03-10T00:01:00+00:00",
                  final_nav: "10500000.0000",
                  total_return: "0.0500",
                  max_drawdown: "-0.0200",
                  total_turnover: "0.1200",
                  total_tax: "0.0000",
                  trade_count: 12,
                },
                {
                  run_id: "run_2",
                  strategy_id: "kr_etf_momo_30_90_v1",
                  strategy_name: "국내 ETF 일봉 30/90 모멘텀 변형 전략",
                  strategy_kind: "daily_momentum",
                  strategy_version: "v1",
                  dataset: "krx_etf_daily",
                  profile_id: "stress_10bps",
                  status: "succeeded",
                  started_at: "2026-03-11T00:00:00+00:00",
                  finished_at: "2026-03-11T00:01:00+00:00",
                  final_nav: "10300000.0000",
                  total_return: "0.0300",
                  max_drawdown: "-0.0300",
                  total_turnover: "0.0900",
                  total_tax: "0.0000",
                  trade_count: 8,
                },
              ],
            }),
          );
        }

        if (url.endsWith("/backtests/compare") && init?.method === "POST") {
          return Promise.resolve(
            createJsonResponse({
              items: [
                {
                  run_id: "run_1",
                  strategy_id: "kr_etf_momo_20_60_v1",
                  strategy_name: "국내 ETF 일봉 20/60 모멘텀 참조 전략",
                  strategy_kind: "daily_momentum",
                  strategy_version: "v1",
                  dataset: "krx_etf_daily",
                  profile_id: "baseline",
                  generated_at: "2026-03-10T00:00:00+00:00",
                  as_of: "2026-03-09T00:00:00+00:00",
                  initial_cash: "10000000.0000",
                  final_nav: "10500000.0000",
                  total_return: "0.0500",
                  max_drawdown: "-0.0200",
                  total_turnover: "0.1200",
                  total_commission: "1234.0000",
                  total_tax: "0.0000",
                  total_slippage_cost: "456.0000",
                  total_traded_notional: "12000000.0000",
                  trade_count: 12,
                  loaded_symbols: ["069500"],
                  missing_symbols: [],
                },
                {
                  run_id: "run_2",
                  strategy_id: "kr_etf_momo_30_90_v1",
                  strategy_name: "국내 ETF 일봉 30/90 모멘텀 변형 전략",
                  strategy_kind: "daily_momentum",
                  strategy_version: "v1",
                  dataset: "krx_etf_daily",
                  profile_id: "stress_10bps",
                  generated_at: "2026-03-11T00:00:00+00:00",
                  as_of: "2026-03-10T00:00:00+00:00",
                  initial_cash: "10000000.0000",
                  final_nav: "10300000.0000",
                  total_return: "0.0300",
                  max_drawdown: "-0.0300",
                  total_turnover: "0.0900",
                  total_commission: "1000.0000",
                  total_tax: "0.0000",
                  total_slippage_cost: "300.0000",
                  total_traded_notional: "9000000.0000",
                  trade_count: 8,
                  loaded_symbols: ["069500"],
                  missing_symbols: [],
                },
              ],
            }),
          );
        }

        return Promise.reject(new Error(`unexpected request: ${url}`));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders run list, selected detail, and compare summary", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <BacktestPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("저장된 백테스트")).toBeInTheDocument();
    expect((await screen.findAllByText("kr_etf_momo_20_60_v1")).length).toBeGreaterThan(0);
    expect(await screen.findByText("실행 ID")).toBeInTheDocument();
    expect((await screen.findAllByText("run_1")).length).toBeGreaterThan(0);

    fireEvent.click(await screen.findByLabelText("run_1 비교 선택"));
    fireEvent.click(await screen.findByLabelText("run_2 비교 선택"));

    expect(await screen.findByText("비교 선택")).toBeInTheDocument();
    expect(await screen.findByText("10,300,000")).toBeInTheDocument();
    expect((await screen.findAllByText("stress_10bps")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("누적 회전율")).length).toBeGreaterThan(0);
    expect(await screen.findByText("실행 파라미터")).toBeInTheDocument();
  });
});
