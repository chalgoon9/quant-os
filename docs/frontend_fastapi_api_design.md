# Frontend FastAPI API Design

기준일: 2026-03-10

## 1. 목적

이 문서는 현재 `quant-os`에 프론트를 붙이기 위한 최소 FastAPI 백엔드 설계를 정의합니다.

목표는 다음입니다.

- 기존 Python runtime / store / ingestion 코드를 재사용
- read-mostly 운영 대시보드용 API 제공
- destructive action은 최대한 배제
- live trading UI를 위한 API는 이번 범위에서 제외

## 2. 범위

이번 API에서 포함할 것:

- 시스템/런타임 요약
- 운영 상태 요약
- 주문 조회
- 리서치 dataset 조회
- Upbit 일봉 수집 실행
- daily report / reconciliation / kill-switch 조회

이번 API에서 제외할 것:

- 실제 live order submit / cancel
- broker credential 관리
- websocket streaming
- 사용자 인증/권한

## 3. 권장 파일 구조

```text
src/quant_os/api/
├─ __init__.py
├─ main.py
├─ deps.py
├─ schemas.py
└─ routes/
   ├─ __init__.py
   ├─ system.py
   ├─ ops.py
   ├─ research.py
   └─ reports.py
```

### 파일 역할

- `main.py`
  - FastAPI app 생성
  - router 등록
  - CORS / basic metadata
- `deps.py`
  - settings 로드
  - runtime singleton/cache
  - store accessor
- `schemas.py`
  - API response/request Pydantic schema
- `routes/system.py`
  - doctor/runtime 계열
- `routes/ops.py`
  - summary/orders/reconciliation/kill-switch
- `routes/research.py`
  - datasets/bars/ingestion
- `routes/reports.py`
  - daily report 관련

## 4. 아키텍처 원칙

- API layer는 orchestration만 담당
- business rule은 기존 `services`, `store`, `reporting`, `ingestion`에 둠
- route handler 안에 SQLAlchemy query를 직접 쓰지 않음
- 파일/DB 경로는 모두 settings와 runtime을 통해 접근
- live mode라도 API는 read-mostly로 유지

## 5. Runtime / Dependency 설계

### 5.1 settings 주입

기본 config path:

- `conf/base.yaml`

환경변수로 override 가능한 값 권장:

- `QUANT_OS_CONFIG`

권장 dependency:

```python
def get_settings() -> AppSettings:
    ...
```

### 5.2 runtime 캐싱

`build_app_runtime()`는 request마다 새로 만들기보다 process 단위 캐싱이 낫습니다.

권장:

```python
@lru_cache(maxsize=1)
def get_runtime(config_path: str) -> AppRuntime:
    ...
```

이유:

- store/duckdb/sqlalchemy engine 재생성을 줄일 수 있음
- 운영 대시보드 polling 부하를 줄일 수 있음

### 5.3 API service wrapper 권장

가능하면 thin wrapper를 둡니다.

예시:

- `OpsReadService`
- `ResearchReadService`
- `IngestionService`

단, 현재 단계에서는 route에서 runtime/store를 직접 호출해도 괜찮습니다.  
wrapper는 구현량이 커질 때만 추가합니다.

## 6. Endpoint 설계

기본 prefix:

- `/api`

### 6.1 System Routes

#### `GET /api/system/doctor`

용도:

- CLI `doctor`와 유사한 한 번에 보는 요약

응답 예시:

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
    "kill_switch_events"
  ]
}
```

#### `GET /api/system/runtime`

용도:

- 프론트 header/status bar용

응답 필드:

- `mode`
- `venue`
- `strategy`
- `execution_adapter`
- `base_currency`
- `research_dataset`

### 6.2 Ops Routes

#### `GET /api/ops/summary`

용도:

- Overview 화면의 top-level summary

응답 필드:

- latest pnl snapshot
- latest reconciliation status
- active kill switch events

응답 예시:

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

#### `GET /api/ops/orders`

용도:

- recent orders table

필요한 백엔드 보강:

- `OperationalStore.list_recent_orders(limit: int = 100)`

응답 필드:

- `order_id`
- `symbol`
- `side`
- `status`
- `quantity`
- `filled_quantity`
- `updated_at`

#### `GET /api/ops/orders/{order_id}`

용도:

- order detail drawer

응답 필드:

- `projection`
- `events`
- `fills`

현재 구현 가능 근거:

- `get_order_projection`
- `list_order_events`
- `list_fills`

#### `GET /api/ops/reconciliation/latest`

용도:

- latest reconciliation detail

현재 구현 가능 근거:

- `OperationalStore.latest_reconciliation_result()`

#### `GET /api/ops/kill-switch/active`

용도:

- active kill switch panel

현재 구현 가능 근거:

- `OperationalStore.active_kill_switch_events()`

### 6.3 Research Routes

#### `GET /api/research/datasets`

용도:

- dataset 목록

필요한 백엔드 보강:

- `ResearchStore.list_datasets()`
- 각 dataset의 `row_count`, `latest_timestamp` helper

응답 필드:

- `dataset`
- `row_count`
- `latest_timestamp`

#### `GET /api/research/datasets/{dataset}/bars`

query params:

- `symbol`
- `limit`

용도:

- bars preview table / chart

현재 구현 가능 근거:

- `ResearchStore.load_bars(dataset, symbol=...)`

추가 권장:

- limit slicing helper

#### `POST /api/research/ingestion/upbit/daily`

request body:

```json
{
  "market": "KRW-BTC",
  "count": 30,
  "dataset": "upbit_krw_btc_daily"
}
```

용도:

- 프론트에서 Upbit 일봉 수집 실행

현재 구현 가능 근거:

- `UpbitQuotationClient`
- `ingest_upbit_daily_bars(...)`

응답 예시:

```json
{
  "source": "upbit_quotation",
  "market": "KRW-BTC",
  "dataset": "upbit_krw_btc_daily",
  "path": "/abs/path/to/bars.parquet"
}
```

### 6.4 Reports Routes

#### `GET /api/reports/daily/latest`

용도:

- Reports 화면 markdown viewer

필요한 백엔드 처리:

- 최신 `LedgerSnapshot`
- 최신 `ReconciliationResult`
- active kill switch events
- `DailyReportGenerator.generate(...)`

주의:

- 현재 daily report persistence는 없으므로 “on-demand generation”이 맞습니다.

응답 필드:

- `as_of`
- `nav`
- `cash_balance`
- `realized_pnl`
- `unrealized_pnl`
- `total_pnl`
- `reconciliation_status`
- `active_kill_switch_reasons`
- `body_markdown`

## 7. Schema 설계

권장 schema 집합:

- `DoctorResponse`
- `RuntimeResponse`
- `OpsSummaryResponse`
- `OrderListItem`
- `OrderDetailResponse`
- `DatasetSummary`
- `BarsResponse`
- `UpbitIngestionRequest`
- `UpbitIngestionResponse`
- `DailyReportResponse`
- `ApiErrorResponse`

원칙:

- Decimal은 문자열로 반환
- datetime은 ISO-8601 UTC 문자열
- enum은 value 문자열

## 8. 에러 처리

기본 규칙:

- not found -> `404`
- validation error -> `422`
- unsupported operation -> `400`
- config/runtime failure -> `500`
- external data source failure -> `502`

응답 예시:

```json
{
  "error": "dataset not found",
  "code": "dataset_not_found"
}
```

## 9. Polling 전략

현재는 websocket 대신 polling을 권장합니다.

- `/api/ops/summary`: 10초
- `/api/ops/orders`: 5초
- `/api/ops/kill-switch/active`: 5초
- `/api/research/datasets`: 30초 또는 수동 refresh
- `/api/reports/daily/latest`: 수동 refresh

## 10. CORS / 배포 가정

개발 환경:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`

권장:

- 개발환경에서만 CORS 허용
- 운영에서는 reverse proxy 뒤 단일 origin 우선

## 11. 최소 구현 순서

1. `GET /api/system/runtime`
2. `GET /api/ops/summary`
3. `GET /api/ops/reconciliation/latest`
4. `GET /api/ops/kill-switch/active`
5. `POST /api/research/ingestion/upbit/daily`
6. `GET /api/research/datasets/{dataset}/bars`
7. `GET /api/ops/orders`
8. `GET /api/ops/orders/{order_id}`
9. `GET /api/reports/daily/latest`

## 12. 구현 전 필수 보강점

FastAPI를 붙이기 전에 아래 helper는 추가되는 편이 좋습니다.

- `OperationalStore.list_recent_orders()`
- `ResearchStore.list_datasets()`
- `ResearchStore.latest_timestamp(dataset)`
- `ResearchStore.sample_bars(dataset, symbol, limit)`

이 보강은 API를 얇게 유지하기 위한 최소 수준입니다.

## 13. 최종 판단

현재 코드베이스는 FastAPI 기반 read-mostly backend를 붙일 준비가 되어 있습니다.

다만 다음은 여전히 제외해야 합니다.

- live submit endpoint
- broker account mutation endpoint
- realtime trading websocket control panel

즉, 이번 프론트용 API는 “운영 관측 및 수집 실행”까지가 적절합니다.
