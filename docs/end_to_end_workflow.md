# End-to-End Workflow

기준일: 2026-03-10

이 문서는 현재 `quant-os` 저장소의 전체 워크플로우를 한 번에 정리합니다.

범위는 다음을 포함합니다.

- 개발자 실행 흐름
- 데이터 수집 흐름
- 전략/리스크/의사결정 흐름
- execution / ledger / reconciliation / kill-switch 흐름
- API / 프론트 연결 흐름
- live 전환 전 반드시 충족해야 하는 조건

## 1. 시스템 목표

현재 시스템은 아래 순서를 따르는 개인용 quant operating system MVP입니다.

```text
Research data
  -> Strategy
  -> Risk review
  -> Intent generation
  -> Execution adapter
  -> Order/Fill events
  -> Ledger/PnL projection
  -> Reconciliation
  -> Kill switch
  -> Report / Dashboard
```

핵심 원칙:

- `Strategy`는 `OrderIntent`를 만들지 않고 `TargetExposure`만 반환합니다.
- 주문/체결은 append-only 이벤트로 다룹니다.
- `orders`는 projection입니다.
- fail-open보다 fail-closed를 우선합니다.
- `paper / shadow / live`는 같은 execution interface를 공유합니다.

## 2. 저장소 기준 실행 순서

프로젝트 준비:

```bash
uv sync --extra dev
```

전체 테스트:

```bash
uv run --extra dev pytest -q
```

DB migration:

```bash
uv run python -m alembic upgrade head
```

기본 설정 및 runtime 점검:

```bash
uv run quant-os doctor --config conf/base.yaml
```

## 3. 설정 로드 워크플로우

설정 입력:

- [base.yaml](/home/lia/repos/my-projects/quant/conf/base.yaml)

설정 로드 흐름:

```text
conf/base.yaml
  -> quant_os.config.loader.load_settings()
  -> AppSettings
  -> SystemConfig
  -> build_app_runtime()
```

핵심 구성 결과:

- trading mode
- strategy definition
- risk policy
- intent policy
- backtest / execution cost
- reconciliation / stale-market-data controls
- storage path / DB URL

관련 코드:

- [loader.py](/home/lia/repos/my-projects/quant/src/quant_os/config/loader.py)
- [models.py](/home/lia/repos/my-projects/quant/src/quant_os/config/models.py)
- [wiring.py](/home/lia/repos/my-projects/quant/src/quant_os/services/wiring.py)

## 4. 데이터 수집 워크플로우

현재 회원가입 없이 바로 붙은 공식 API는 `Upbit Quotation API`입니다.

수집 흐름:

```text
CLI
  -> UpbitQuotationClient
  -> fetch daily bars
  -> ResearchStore.write_bars()
  -> Parquet 저장
  -> DuckDB view로 조회
```

실행:

```bash
uv run quant-os ingest-upbit-daily --config conf/base.yaml --market KRW-BTC --count 30
```

출력:

```text
source=upbit_quotation
market=KRW-BTC
dataset=upbit_krw_btc_daily
path=/abs/path/to/bars.parquet
```

저장 위치:

- `data/normalized/<dataset>/bars.parquet`

관련 코드:

- [upbit.py](/home/lia/repos/my-projects/quant/src/quant_os/data_ingestion/upbit.py)
- [store.py](/home/lia/repos/my-projects/quant/src/quant_os/research_store/store.py)
- [main.py](/home/lia/repos/my-projects/quant/src/quant_os/cli/main.py)

## 5. 리서치/백테스트 워크플로우

리서치 데이터가 들어오면 아래 흐름을 탑니다.

```text
ResearchStore.load_bars()
  -> Strategy.generate_targets()
  -> RiskManager.review()
  -> IntentGenerator.diff_to_intents()
  -> Backtest executor
```

현재 전략/리스크/의사결정 경계:

- 전략: 모멘텀 기반 `TargetExposure` 생성
- 리스크: 단일 종목 비중, 현금 버퍼, turnover 제한
- intent generator: 현재 포트폴리오와 target diff를 `OrderIntent`로 변환

관련 코드:

- [momentum.py](/home/lia/repos/my-projects/quant/src/quant_os/strategy/momentum.py)
- [simple.py](/home/lia/repos/my-projects/quant/src/quant_os/risk/simple.py)
- [generator.py](/home/lia/repos/my-projects/quant/src/quant_os/intent/generator.py)
- [simple.py](/home/lia/repos/my-projects/quant/src/quant_os/backtest/simple.py)

## 6. 실행 워크플로우

주문 실행 흐름:

```text
OrderIntent
  -> ExecutionAdapter.submit_intent()
  -> OrderStateMachine.plan/transition
  -> OrderEvent append
  -> FillEvent append
  -> Order projection update
```

현재 mode별 adapter:

- `paper` -> `PaperAdapter`
- `shadow` -> `ShadowAdapter`
- `live` -> `StubLiveAdapter`

주의:

- 현재 `live`는 실제 broker에 연결되지 않았습니다.
- `StubLiveAdapter`는 fail-closed stub이며 실거래를 수행하지 않습니다.

현재 execution behavior:

- market intent 처리
- partial fill 지원
- uncertain submit -> `RECONCILE_PENDING`
- shadow venue-rule precheck
- duplicate fill / out-of-order event reject

관련 코드:

- [paper.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/paper.py)
- [shadow.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/shadow.py)
- [live.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/live.py)
- [state_machine.py](/home/lia/repos/my-projects/quant/src/quant_os/execution/state_machine.py)

## 7. 원장 / PnL 워크플로우

체결 이후 흐름:

```text
FillEvent
  -> LedgerProjector.apply_fill_event()
  -> Cash ledger entry
  -> Position lots
  -> Ledger snapshot
  -> PnL snapshot
```

산출물:

- cash balance
- positions
- realized / unrealized / total PnL
- NAV

관련 코드:

- [projector.py](/home/lia/repos/my-projects/quant/src/quant_os/ledger/projector.py)

## 8. 운영 persistence 워크플로우

현재 운영 데이터는 `OperationalStore`를 통해 저장됩니다.

```text
OrderEvent/FillEvent/Ledger/Reconciliation/KillSwitch
  -> OperationalStore
  -> SQLite/SQLAlchemy tables
```

현재 저장되는 핵심 테이블:

- `strategy_runs`
- `orders`
- `order_events`
- `fills`
- `positions_snapshot`
- `cash_ledger`
- `pnl_snapshot`
- `reconciliation_log`
- `kill_switch_events`

관련 코드:

- [schema.py](/home/lia/repos/my-projects/quant/src/quant_os/db/schema.py)
- [store.py](/home/lia/repos/my-projects/quant/src/quant_os/db/store.py)

## 9. reconciliation 워크플로우

운영 상태 비교 흐름:

```text
Local portfolio state
  + external snapshot
  + local open orders
    -> PortfolioReconciler.reconcile()
    -> ReconciliationResult
    -> reconciliation_log 저장
```

현재 비교 항목:

- base currency
- cash balance
- position quantity
- open order projection

관련 코드:

- [service.py](/home/lia/repos/my-projects/quant/src/quant_os/reconciliation/service.py)

## 10. kill switch 워크플로우

kill switch는 아래 이벤트로 활성화될 수 있습니다.

- daily loss limit
- stale market data
- reconciliation failure
- event write failure
- duplicate intent
- unknown open order

흐름:

```text
Ops signal
  -> KillSwitch.evaluate_...
  -> KillSwitchEvent
  -> kill_switch_events 저장
  -> 신규 주문 차단
```

관련 코드:

- [kill_switch.py](/home/lia/repos/my-projects/quant/src/quant_os/risk/kill_switch.py)

## 11. daily report 워크플로우

리포트 생성 흐름:

```text
LedgerSnapshot
  + ReconciliationResult
  + active KillSwitchEvents
    -> DailyReportGenerator.generate()
    -> markdown body + summary fields
```

현재는 저장형 report engine이 아니라 생성형입니다.

관련 코드:

- [daily.py](/home/lia/repos/my-projects/quant/src/quant_os/reporting/daily.py)

## 12. 프론트 연결 워크플로우

현재 권장 프론트 구조:

```text
Browser SPA
  -> Thin FastAPI backend
    -> build_app_runtime()
    -> ResearchStore
    -> OperationalStore
    -> UpbitQuotationClient
```

왜 이렇게 해야 하는가:

- 브라우저가 DB를 직접 다루면 안 됩니다.
- 브라우저가 broker/API key를 직접 다루면 안 됩니다.
- 현재 Python runtime과 store가 이미 있으므로, 얇은 HTTP layer가 가장 경제적입니다.

현재 프론트에 열어도 되는 기능:

- system/runtime summary
- latest ops summary
- recent orders 조회
- research dataset 조회
- Upbit ingestion 실행
- daily report 조회
- reconciliation / kill-switch 조회

현재 프론트에 열면 안 되는 기능:

- live submit
- broker cancel / modify
- broker account mutation

관련 문서:

- [frontend_ops_dashboard_design.md](/home/lia/repos/my-projects/quant/docs/frontend_ops_dashboard_design.md)
- [frontend_fastapi_api_design.md](/home/lia/repos/my-projects/quant/docs/frontend_fastapi_api_design.md)
- [2026-03-10-frontend-ops-dashboard-implementation.md](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-frontend-ops-dashboard-implementation.md)

## 13. 현재 가능한 운영 루프

현재 구현 기준으로 가능한 루프는 다음입니다.

```text
1. config 검증
2. migration 적용
3. 테스트 실행
4. read-only 시세 수집
5. research/backtest 입력 데이터 저장
6. paper/shadow execution 검증
7. ledger/pnl/reconciliation/kill-switch 확인
8. daily report 생성
9. frontend dashboard에서 조회
```

## 14. 현재 막혀 있는 지점

아직 없는 것:

- 실제 broker용 `LiveAdapter`
- broker 기준 external sync
  - open orders
  - fills
  - positions
  - cash
- live reconciliation 실연결
- tiny live 운영 경로

따라서 현재 결론은 명확합니다.

- `paper`: 가능
- `shadow`: skeleton 수준으로 가능
- `live`: 불가

## 15. live 전환 전 필수 조건

실제 live에 들어가기 전에 반드시 필요한 것:

1. 사용할 broker/venue 하나 확정
2. 해당 broker용 `LiveAdapter` 구현
3. external sync/reconciliation 연결
4. timeout / duplicate / out-of-order / restart-recovery integration test
5. 최소 30거래일 shadow 검증
6. 이상 없을 때 tiny live

## 16. 추천 구현 우선순위

현 시점에서 가장 합리적인 다음 순서는 아래입니다.

1. FastAPI backend 추가
2. React ops dashboard 추가
3. Overview / Research 화면 구현
4. Orders / Reports 화면 구현
5. broker 1개 선택
6. live adapter + external sync 구현

## 17. 한 줄 요약

현재 `quant-os`의 전체 워크플로우는 `read-only market data -> strategy/risk/intent -> paper/shadow execution -> append-only ops persistence -> reconciliation/kill-switch/reporting -> dashboard` 까지는 닫혀 있고, `실제 broker live execution`만 아직 비어 있습니다.
