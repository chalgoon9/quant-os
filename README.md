# Quant OS

혼자 만들고 혼자 운영하는 개인용 퀀트 운영체제 MVP입니다. 이 저장소는 아래 방향을 의도적으로 우선합니다.

- 마이크로서비스보다 모듈형 모놀리스
- 불필요한 async보다 배치 우선 워크플로
- fail-open 편의보다 fail-closed 통제
- `orders`를 projection으로 두고 주문/체결 이벤트는 append-only로 보존
- `paper`, `shadow`, `live` 전반에서 공통 실행 인터페이스 유지

## 현재 범위

현재까지 구현된 내용:

- import 가능한 Python 패키지와 프로젝트 골격
- 핵심 도메인 enum, ID, type, model
- SQLAlchemy/Alembic 기반 운영 DB 스키마
- fail-closed 방식으로 typed domain model에 적재되는 YAML config
- Typer 기반 CLI 골격
- DuckDB 인덱싱을 사용하는 Parquet 기반 research storage
- `TargetExposure`를 생성하는 단순 일봉 모멘텀 전략
- 단일 종목 한도, 현금 버퍼, turnover clipping을 포함한 fail-closed risk review
- target과 현재 상태 차이를 이용한 intent 생성
- 전략, 리스크, intent 로직을 재사용하는 단순 배치 backtest
- 최신 백테스트 결과를 저장하는 artifact 경로와 조회 API/프론트 화면
- append-only 주문/체결 이벤트를 내보내는 paper adapter
- order events와 fills로부터 projection을 구성하는 주문 상태 머신
- cash ledger, inventory lots, PnL snapshot을 지원하는 ledger projector
- 내부 상태와 외부 상태를 비교하는 reconciliation 서비스
- 일일 손실, stale market data, reconciliation failure, unexpected exposure, reject rate spike에 반응하는 fail-closed kill switch
- NAV, 현금, 손익, reconciliation, kill-switch 상태를 요약하는 daily report generator
- paper 실행 경로를 재사용하면서 venue-rule precheck, external state comparison, shadow reporting을 제공하는 shadow adapter
- Upbit venue에 대해 submit/cancel/sync/portfolio state를 연결하는 live adapter와 fail-closed fallback stub
- 회원가입 없이 쓸 수 있는 Upbit Quotation API 기반 read-only 일봉 데이터 수집
- Upbit 수집 시 raw payload 선보존, validation report, quarantine artifact 기록
- import, config, migration, research store, strategy pipeline, backtest, execution, reconciliation, kill switch, reporting, shadow, simulation에 대한 pytest 검증

핵심 경계는 그대로 유지됩니다. 전략의 출력은 `OrderIntent`가 아니라 `TargetExposure`입니다.

## 파일 구조

```text
quant/
├─ alembic/
├─ conf/
│  └─ base.yaml
├─ data/
├─ docs/
│  └─ plans/
├─ research/
├─ src/quant_os/
│  ├─ adapters/
│  ├─ backtest/
│  ├─ cli/
│  ├─ config/
│  ├─ dashboard/
│  ├─ data_ingestion/
│  ├─ db/
│  ├─ domain/
│  ├─ execution/
│  ├─ intent/
│  ├─ ledger/
│  ├─ normalization/
│  ├─ portfolio/
│  ├─ reconciliation/
│  ├─ reporting/
│  ├─ research_store/
│  ├─ risk/
│  ├─ scheduler/
│  ├─ services/
│  └─ strategy/
├─ tests/
│  ├─ integration/
│  ├─ replay/
│  ├─ shadow/
│  ├─ simulation/
│  └─ unit/
├─ AGENTS.md
├─ pyproject.toml
└─ quant-os-mvp-design-spec.md
```

## 설정 모델

`conf/base.yaml`은 `quant_os.config.models.AppSettings`로 로드된 뒤 `quant_os.domain.models.SystemConfig`로 변환됩니다.

현재 기본값은 아래를 가정합니다.

- 시장: KRX ETF
- 모드: `paper`
- 전략: lookback을 조절할 수 있는 일봉 모멘텀
- 리스크: 명시적 현금 버퍼와 turnover cap을 포함한 fail-closed 한도
- intent 생성: minimum notional과 lot size를 갖는 기본 시장가 주문
- backtest: 초기 현금과 bps 비용 모델 명시
- 제어: reconciliation 허용 오차와 stale market data 기준
- 저장소: operational DB와 로컬 research/data 경로

## DB 모델

운영 스키마에는 아래 테이블이 포함됩니다.

- `strategy_runs`
- `orders`
- `order_events`
- `fills`
- `positions_snapshot`
- `cash_ledger`
- `pnl_snapshot`
- `reconciliation_log`
- `kill_switch_events`

스키마 설계에서 강제하는 규칙:

- `order_events`와 `fills`는 append-only source-of-truth 테이블
- `orders`는 projection 테이블
- broker 식별자는 dedupe를 고려
- numeric 컬럼은 명시적 precision 사용

## CLI

현재 CLI는 아래 명령을 제공합니다.

```bash
quant-os doctor --config conf/base.yaml
quant-os ingest-upbit-daily --config conf/base.yaml --market KRW-BTC --count 30
quant-os run-backtest --config conf/base.yaml --dataset krx_etf_daily
quant-os serve-api --config conf/base.yaml --host 127.0.0.1 --port 8000
```

이 명령들은 base config를 검증하고 domain config로 변환한 뒤, 현재 research/risk/intent/ledger/execution/reconciliation/kill-switch/reporting runtime surface와 필요한 operational table 목록을 출력합니다.

실행 adapter 선택은 모드에 따라 달라집니다.

- `paper` -> `PaperAdapter`
- `shadow` -> `ShadowAdapter`
- `live` -> `UpbitLiveAdapter` 또는 `StubLiveAdapter`

`live` 모드는 기본적으로 fail-closed입니다. `venue=upbit` 이고 필요한 환경변수가 있으면 `UpbitLiveAdapter`를 사용하고, 그렇지 않으면 `StubLiveAdapter`가 append-only order event를 남기며 거절합니다.

현재 simulation 검증 범위:

- partial-fill과 timeout 후 `RECONCILE_PENDING`
- duplicate-fill과 out-of-order event 거절
- store 기반 restart/recovery readback
- operational kill-switch trigger 경로

백테스트 실행 결과는 `artifacts_root/backtests/latest.json`에 저장되며, API와 프론트에서 조회할 수 있습니다.
또한 `strategy_runs`에는 명시적 run row가 남고, 백테스트는 같은 종가 신호/체결이 아니라 다음 실행 시점 가격으로 체결됩니다.

## API 참고 문서

검토한 API 후보와 현재 연결된 무가입 API는 [api_reference.md](/home/lia/repos/my-projects/quant/docs/api_reference.md)에 정리되어 있습니다.

## 사용 가이드

실행 순서와 사용 방법은 [usage_guide.md](/home/lia/repos/my-projects/quant/docs/usage_guide.md)에 정리되어 있습니다.

## End-to-End 워크플로

전체 시스템 워크플로는 [end_to_end_workflow.md](/home/lia/repos/my-projects/quant/docs/end_to_end_workflow.md)에 정리되어 있습니다.

## 프론트엔드 설계

현재 프론트 중심 아키텍처와 대시보드 범위는 [frontend_ops_dashboard_design.md](/home/lia/repos/my-projects/quant/docs/frontend_ops_dashboard_design.md)에 정리되어 있습니다.

화면별 명세는 [frontend_screen_spec.md](/home/lia/repos/my-projects/quant/docs/frontend_screen_spec.md)에 있습니다.

프론트/백엔드 데이터 계약은 [frontend_data_contract.md](/home/lia/repos/my-projects/quant/docs/frontend_data_contract.md)에 있습니다.

대시보드용 FastAPI API 설계는 [frontend_fastapi_api_design.md](/home/lia/repos/my-projects/quant/docs/frontend_fastapi_api_design.md)에 있습니다.

구현 계획은 [2026-03-10-frontend-ops-dashboard-implementation.md](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-frontend-ops-dashboard-implementation.md)에 있습니다.

## 빠른 시작

1. 개발 환경 준비:

```bash
uv sync --extra dev
```

2. 테스트 실행:

```bash
uv run --extra dev pytest -q
```

3. migration 적용:

```bash
uv run python -m alembic upgrade head
```

4. config와 패키지 wiring 확인:

```bash
uv run quant-os doctor --config conf/base.yaml
```

5. 백테스트 실행:

```bash
uv run quant-os run-backtest --config conf/base.yaml --dataset krx_etf_daily
```

6. 대시보드 서버 실행:

```bash
uv run quant-os serve-api --config conf/base.yaml --host 127.0.0.1 --port 8000
```

7. 대시보드 접속:

```bash
http://127.0.0.1:8000
```

같은 프로세스가 아래 둘을 함께 서빙합니다.

- frontend SPA: `/`
- API: `/api`

프론트의 `백테스트` 화면에서는 가장 최근에 저장된 백테스트 결과를 확인할 수 있습니다.

다른 기기에서 접속해야 하면 `0.0.0.0`으로 bind하고, 사용하는 네트워크 경로에 맞는 방식으로 연결하십시오.

## 재부팅 후 자동 실행

이 머신에서 재부팅 후에도 대시보드 서버를 계속 실행하려면 user-level systemd service를 설치하십시오.

```bash
chmod +x scripts/install_user_service.sh
./scripts/install_user_service.sh
```

서비스 템플릿은 [quant-os.service.in](/home/lia/repos/my-projects/quant/deploy/systemd/quant-os.service.in)에 있고, 실제 설치 위치는 `~/.config/systemd/user/quant-os.service`입니다.

## 다음 작업 우선순위

이후 우선순위는 아래에 두는 것이 맞습니다.

### 먼저 할 것: multi-strategy research/backtest 확장

설계자 리뷰 기준 다음 단계의 최우선 작업은 live scope 확장이 아니라 연구/백테스트 확장입니다.

다음 순서로 진행합니다.

1. schema migration
2. strategy registry
3. backtest request / catalog
4. API list / detail / compare

상세 계획:
- [Phase 6 Umbrella](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-phase-6-multi-strategy-research-backtest-expansion.md)
- [Phase 6a Schema Migration](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-phase-6a-schema-migration-for-backtest-catalog.md)
- [Phase 6b Strategy Registry](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-phase-6b-strategy-registry.md)
- [Phase 6c Backtest Request/Catalog](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-phase-6c-backtest-request-catalog.md)
- [Phase 6d API List/Detail/Compare](/home/lia/repos/my-projects/quant/docs/plans/2026-03-10-phase-6d-backtest-api-list-detail-compare.md)

### 그 다음 할 것: 운영성 보강

- PostgreSQL 운영 기본값 정리
- weekly review / alert-ready summary 추가
- scheduler / replay / runbook 보강
- timeout, duplicate, out-of-order event 경로에 대한 simulation 확대
- shadow/live 비교 리포트 보강
- execution recovery를 위한 restart/replay 보강
