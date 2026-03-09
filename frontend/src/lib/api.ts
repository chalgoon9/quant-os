type ApiBaseUrlOptions = {
  envApiBaseUrl?: string | undefined;
  protocol: string;
  hostname: string;
};

export function resolveApiBaseUrl(options: ApiBaseUrlOptions): string {
  if (options.envApiBaseUrl) {
    return options.envApiBaseUrl.replace(/\/$/, "");
  }
  return `${options.protocol}//${options.hostname}:8000/api`;
}

export const API_BASE_URL = resolveApiBaseUrl({
  envApiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  protocol: window.location.protocol,
  hostname: window.location.hostname || "localhost",
});

export type RuntimeResponse = {
  mode: "paper" | "shadow" | "live";
  venue: string;
  strategy: string;
  execution_adapter: string;
  base_currency: string;
  research_dataset: string;
};

export type OpsSummaryResponse = {
  nav: string;
  cash_balance: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_pnl: string;
  reconciliation_status: "matched" | "mismatch" | "error";
  reconciliation_summary: string;
  active_kill_switch_reasons: string[];
};

export type OrderListItem = {
  order_id: string;
  symbol: string;
  side: "buy" | "sell";
  status: string;
  quantity: string;
  filled_quantity: string;
  updated_at: string;
};

export type OrdersResponse = {
  items: OrderListItem[];
};

export type OrderEventDto = {
  event_id: string;
  order_id: string;
  status: string;
  event_type: string;
  occurred_at: string;
  reason: string | null;
};

export type FillDto = {
  fill_id: string;
  order_id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: string;
  price: string;
  fee: string;
  tax: string;
  occurred_at: string;
};

export type OrderProjectionDto = {
  order_id: string;
  intent_id: string;
  strategy_run_id: string | null;
  symbol: string;
  side: "buy" | "sell";
  order_type: string;
  time_in_force: string;
  quantity: string;
  status: string;
  created_at: string;
  updated_at: string;
  filled_quantity: string;
  broker_order_id: string | null;
  last_event_at: string | null;
};

export type OrderDetailResponse = {
  projection: OrderProjectionDto;
  events: OrderEventDto[];
  fills: FillDto[];
};

export type ReconciliationIssueDto = {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
};

export type ReconciliationResponse = {
  reconciliation_id: string;
  occurred_at: string;
  status: "matched" | "mismatch" | "error";
  mismatch_count: number;
  requires_manual_intervention: boolean;
  summary: string;
  issues: ReconciliationIssueDto[];
};

export type KillSwitchEventDto = {
  event_id: string;
  reason: string;
  triggered_at: string;
  trigger_value: string | null;
  threshold_value: string | null;
  details: Record<string, unknown> | null;
  is_active: boolean;
  cleared_at: string | null;
};

export type KillSwitchResponse = {
  items: KillSwitchEventDto[];
};

export type DatasetSummary = {
  dataset: string;
  row_count: number;
  latest_timestamp: string | null;
};

export type DatasetsResponse = {
  items: DatasetSummary[];
};

export type MarketBarDto = {
  symbol: string;
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
};

export type DatasetBarsResponse = {
  dataset: string;
  symbol: string | null;
  items: MarketBarDto[];
};

export type UpbitIngestionRequest = {
  market: string;
  count: number;
  dataset?: string;
};

export type UpbitIngestionResponse = {
  source: "upbit_quotation";
  market: string;
  dataset: string;
  path: string;
};

export type DailyReportResponse = {
  as_of: string;
  base_currency: string;
  nav: string;
  cash_balance: string;
  realized_pnl: string;
  unrealized_pnl: string;
  total_pnl: string;
  reconciliation_status: "matched" | "mismatch" | "error";
  active_kill_switch_reasons: string[];
  body_markdown: string;
};

export type BacktestSummaryDto = {
  run_id: string;
  strategy_name: string;
  dataset: string;
  generated_at: string;
  as_of: string;
  initial_cash: string;
  final_nav: string;
  total_return: string;
  max_drawdown: string;
  trade_count: number;
  loaded_symbols: string[];
  missing_symbols: string[];
};

export type BacktestEquityPointDto = {
  timestamp: string;
  nav: string;
  cash: string;
};

export type BacktestTradeDto = {
  timestamp: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: string;
  price: string;
  notional: string;
};

export type BacktestDetailResponse = {
  summary: BacktestSummaryDto;
  equity_curve: BacktestEquityPointDto[];
  trades: BacktestTradeDto[];
};

type ErrorBody = {
  error?: string;
  code?: string;
};

export class ApiError extends Error {
  code: string | null;
  status: number;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

function buildUrl(path: string, params?: Record<string, string | number | undefined>) {
  const url = new URL(`${API_BASE_URL}${path}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === "") {
        return;
      }
      url.searchParams.set(key, String(value));
    });
  }

  return url.toString();
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let errorBody: ErrorBody | null = null;
    try {
      errorBody = (await response.json()) as ErrorBody;
    } catch {
      errorBody = null;
    }

    throw new ApiError(
      errorBody?.error ?? `request failed: ${response.status}`,
      response.status,
      errorBody?.code ?? null,
    );
  }

  return (await response.json()) as T;
}

export function getRuntime() {
  return requestJson<RuntimeResponse>("/system/runtime");
}

export function getOpsSummary() {
  return requestJson<OpsSummaryResponse>("/ops/summary");
}

export function getKillSwitchActive() {
  return requestJson<KillSwitchResponse>("/ops/kill-switch/active");
}

export function getReconciliationLatest() {
  return requestJson<ReconciliationResponse>("/ops/reconciliation/latest");
}

export function getOrders(limit = 25) {
  return requestJson<OrdersResponse>("/ops/orders", undefined, { limit });
}

export function getOrderDetail(orderId: string) {
  return requestJson<OrderDetailResponse>(`/ops/orders/${orderId}`);
}

export function getDatasets() {
  return requestJson<DatasetsResponse>("/research/datasets");
}

export function getDatasetBars(dataset: string, symbol?: string, limit = 25) {
  return requestJson<DatasetBarsResponse>(
    `/research/datasets/${dataset}/bars`,
    undefined,
    { symbol, limit },
  );
}

export function postUpbitDailyIngestion(payload: UpbitIngestionRequest) {
  return requestJson<UpbitIngestionResponse>("/research/ingestion/upbit/daily", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getDailyReportLatest() {
  return requestJson<DailyReportResponse>("/reports/daily/latest");
}

export function getBacktestLatest() {
  return requestJson<BacktestDetailResponse>("/backtests/latest");
}
