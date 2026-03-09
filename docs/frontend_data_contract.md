# Frontend Data Contract

기준일: 2026-03-10

이 문서는 프론트와 FastAPI backend 사이의 데이터 계약을 정의합니다.

상태:

- 설계 기준 문서
- 일부 endpoint는 아직 구현 전

## 1. 공통 규칙

### 1.1 Base URL

- 개발: `http://localhost:8000/api`

### 1.2 Content Type

- request: `application/json`
- response: `application/json`

### 1.3 숫자 / 날짜 / enum

- `Decimal` -> 문자열
- `datetime` -> ISO-8601 UTC 문자열
- enum -> 문자열 value

예시:

```json
{
  "nav": "100145.0000",
  "updated_at": "2026-03-10T00:00:00+00:00",
  "status": "matched"
}
```

### 1.4 에러 응답

공통 형식:

```json
{
  "error": "dataset not found",
  "code": "dataset_not_found"
}
```

## 2. System Contracts

### `GET /api/system/doctor`

response:

```json
{
  "system_name": "quant-os-mvp",
  "mode": "paper",
  "strategy": "daily_momentum",
  "research_dataset": "krx_etf_daily",
  "intent_lot_size": "1",
  "execution_adapter": "PaperAdapter",
  "required_tables": [
    "cash_ledger",
    "fills",
    "kill_switch_events",
    "order_events",
    "orders",
    "pnl_snapshot",
    "positions_snapshot",
    "reconciliation_log",
    "strategy_runs"
  ]
}
```

### `GET /api/system/runtime`

response:

```json
{
  "mode": "paper",
  "venue": "krx",
  "strategy": "daily_momentum",
  "execution_adapter": "PaperAdapter",
  "base_currency": "KRW",
  "research_dataset": "krx_etf_daily"
}
```

TypeScript:

```ts
export type RuntimeResponse = {
  mode: "paper" | "shadow" | "live";
  venue: string;
  strategy: string;
  execution_adapter: string;
  base_currency: string;
  research_dataset: string;
};
```

## 3. Ops Contracts

### `GET /api/ops/summary`

response:

```json
{
  "nav": "100145.0000",
  "cash_balance": "99425.0000",
  "realized_pnl": "31.0000",
  "unrealized_pnl": "114.0000",
  "total_pnl": "145.0000",
  "reconciliation_status": "matched",
  "reconciliation_summary": "reconciliation matched",
  "active_kill_switch_reasons": []
}
```

TypeScript:

```ts
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
```

### `GET /api/ops/orders`

query:

- `limit?: number`

response:

```json
{
  "items": [
    {
      "order_id": "order_123",
      "symbol": "AAA",
      "side": "buy",
      "status": "partially_filled",
      "quantity": "10.0000",
      "filled_quantity": "5.0000",
      "updated_at": "2026-03-10T00:00:00+00:00"
    }
  ]
}
```

TypeScript:

```ts
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
```

### `GET /api/ops/orders/{order_id}`

response:

```json
{
  "projection": {
    "order_id": "order_123",
    "intent_id": "intent_123",
    "strategy_run_id": "run_123",
    "symbol": "AAA",
    "side": "buy",
    "order_type": "market",
    "time_in_force": "day",
    "quantity": "10.0000",
    "status": "partially_filled",
    "created_at": "2026-03-10T00:00:00+00:00",
    "updated_at": "2026-03-10T00:00:10+00:00",
    "filled_quantity": "5.0000",
    "broker_order_id": "paper-order_123",
    "last_event_at": "2026-03-10T00:00:10+00:00"
  },
  "events": [
    {
      "event_id": "ordevt_1",
      "order_id": "order_123",
      "status": "planned",
      "event_type": "state_transition",
      "occurred_at": "2026-03-10T00:00:00+00:00",
      "reason": null
    }
  ],
  "fills": [
    {
      "fill_id": "fill_1",
      "order_id": "order_123",
      "symbol": "AAA",
      "side": "buy",
      "quantity": "5.0000",
      "price": "100.0000",
      "fee": "0.0000",
      "tax": "0.0000",
      "occurred_at": "2026-03-10T00:00:09+00:00"
    }
  ]
}
```

### `GET /api/ops/reconciliation/latest`

response:

```json
{
  "reconciliation_id": "recon_1",
  "occurred_at": "2026-03-10T00:00:00+00:00",
  "status": "matched",
  "mismatch_count": 0,
  "requires_manual_intervention": false,
  "summary": "reconciliation matched",
  "issues": []
}
```

### `GET /api/ops/kill-switch/active`

response:

```json
{
  "items": [
    {
      "event_id": "killsw_1",
      "reason": "reconciliation_failure",
      "triggered_at": "2026-03-10T00:00:00+00:00",
      "trigger_value": "1.000000",
      "threshold_value": "0.000000",
      "details": {
        "summary": "cash mismatch"
      },
      "is_active": true,
      "cleared_at": null
    }
  ]
}
```

TypeScript:

```ts
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
```

## 4. Research Contracts

### `GET /api/research/datasets`

response:

```json
{
  "items": [
    {
      "dataset": "upbit_krw_btc_daily",
      "row_count": 30,
      "latest_timestamp": "2026-03-09T00:00:00+00:00"
    }
  ]
}
```

TypeScript:

```ts
export type DatasetSummary = {
  dataset: string;
  row_count: number;
  latest_timestamp: string | null;
};
```

### `GET /api/research/datasets/{dataset}/bars`

query:

- `symbol?: string`
- `limit?: number`

response:

```json
{
  "dataset": "upbit_krw_btc_daily",
  "symbol": "KRW-BTC",
  "items": [
    {
      "symbol": "KRW-BTC",
      "timestamp": "2026-03-09T00:00:00+00:00",
      "open": "150000000",
      "high": "151000000",
      "low": "149000000",
      "close": "150500000",
      "volume": "123.45"
    }
  ]
}
```

TypeScript:

```ts
export type MarketBarDto = {
  symbol: string;
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
};
```

### `POST /api/research/ingestion/upbit/daily`

request:

```json
{
  "market": "KRW-BTC",
  "count": 30,
  "dataset": "upbit_krw_btc_daily"
}
```

response:

```json
{
  "source": "upbit_quotation",
  "market": "KRW-BTC",
  "dataset": "upbit_krw_btc_daily",
  "path": "/abs/path/to/bars.parquet"
}
```

TypeScript:

```ts
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
```

## 5. Reports Contracts

### `GET /api/reports/daily/latest`

response:

```json
{
  "as_of": "2026-03-10T00:00:00+00:00",
  "base_currency": "KRW",
  "nav": "100145.0000",
  "cash_balance": "99425.0000",
  "realized_pnl": "31.0000",
  "unrealized_pnl": "114.0000",
  "total_pnl": "145.0000",
  "reconciliation_status": "matched",
  "active_kill_switch_reasons": [],
  "body_markdown": "# Daily Report 2026-03-10\n..."
}
```

TypeScript:

```ts
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
```

## 6. 프론트 Query Key 제안

- `["runtime"]`
- `["ops-summary"]`
- `["orders", limit]`
- `["order-detail", orderId]`
- `["reconciliation-latest"]`
- `["kill-switch-active"]`
- `["datasets"]`
- `["dataset-bars", dataset, symbol, limit]`
- `["daily-report-latest"]`

## 7. Mutation 제안

- `POST /api/research/ingestion/upbit/daily`

mutation 성공 후 invalidate:

- `["datasets"]`
- `["dataset-bars", dataset, symbol, limit]`

## 8. 프론트 구현시 주의

- Decimal을 number로 즉시 변환하지 말고, formatting helper를 거쳐서 처리하는 편이 안전합니다.
- timestamp는 항상 UTC로 들어온다고 가정하고 로컬 렌더링 시만 timezone 변환합니다.
- enum badge 색은 문자열 mapping으로 처리합니다.
- optional 필드는 null-safe 렌더링을 강제합니다.

## 9. 현재 비어 있는 계약

다음은 아직 설계상만 존재하거나 backend helper가 필요한 항목입니다.

- `GET /api/ops/orders`
  - recent order listing helper 필요
- `GET /api/research/datasets`
  - dataset enumeration helper 필요
- `GET /api/reports/daily/latest`
  - latest snapshot 기반 on-demand 조합 필요

## 10. 승인 기준

프론트 구현 전 이 문서가 충족해야 하는 목적은 단순합니다.

- 화면이 어떤 shape의 JSON을 기대하는지 명확할 것
- Decimal / datetime / enum 표현 규칙이 고정되어 있을 것
- 아직 없는 endpoint도 구현 목표가 구체적일 것
