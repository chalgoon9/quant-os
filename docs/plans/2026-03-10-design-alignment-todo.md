# Design Alignment TODO

기준일: 2026-03-10

이 문서는 [quant-os-mvp-design-spec.md](/home/lia/repos/my-projects/quant/quant-os-mvp-design-spec.md)를 기준으로, 현재 코드와의 차이를 메우기 위한 실제 작업 목록을 정리한다.

우선순위는 아래 기준으로 정한다.

- `P0`: 설계의 의미를 훼손하는 차이. 먼저 메워야 한다.
- `P1`: 실거래 직전 수준으로 가기 위해 필요한 차이. `P0` 다음.
- `P2`: 운영성/완성도를 높이지만 지금 당장 핵심은 아닌 차이.

현재 원칙:

- 새 프론트 polish 작업은 중단한다.
- 새 기능 추가보다 설계 정렬을 우선한다.
- `paper -> shadow -> tiny live` 승급 경로를 강화하는 작업만 진행한다.

## P0

### 1. raw payload 선보존 경로 추가

목표:

- 수집 단계에서 정규화 전에 raw payload를 먼저 저장한다.
- ingestion log, source metadata, fetch timestamp를 함께 남긴다.

현재 차이:

- 현재는 [upbit.py](/home/lia/repos/my-projects/quant/src/quant_os/data_ingestion/upbit.py)에서 바로 `MarketBar`로 정규화해서 research store에 쓴다.

완료 기준:

- `data/raw/...` 아래에 원본 응답이 저장된다.
- 정규화 실패 시 raw는 남고 normalized overwrite는 되지 않는다.
- 최소 1개 ingestion integration test가 추가된다.

### 2. normalization / validation / quarantine 계층 구현

목표:

- raw -> normalized 변환을 별도 계층으로 분리한다.
- validation report와 quarantine record를 남긴다.

현재 차이:

- [normalization/__init__.py](/home/lia/repos/my-projects/quant/src/quant_os/normalization/__init__.py)는 placeholder다.

완료 기준:

- symbol, timestamp, numeric 필드 검증 실패를 quarantine 처리할 수 있다.
- silent fix 없이 hard fail 또는 quarantine가 동작한다.
- 단위 테스트와 integration test가 추가된다.

### 3. strategy run registry를 실제로 구현

목표:

- `strategy_runs`를 placeholder가 아니라 실제 실행 기록으로 사용한다.
- strategy name, mode, started/completed/failed status, dataset, config fingerprint를 남긴다.

현재 차이:

- [store.py](/home/lia/repos/my-projects/quant/src/quant_os/db/store.py#L374)에서 `unspecified/running`으로 자동 생성하는 수준이다.

완료 기준:

- backtest run, paper run, shadow run이 모두 명시적 strategy run row를 남긴다.
- 실패한 run도 `FAILED` 상태로 남는다.

### 4. 백테스트 시그널 시점과 체결 시점 분리

목표:

- 같은 종가로 시그널을 만들고 같은 종가로 체결하는 단순화를 제거한다.
- 최소한 “신호 생성 시점”과 “체결 시점”을 한 칸 분리한다.

현재 차이:

- [simple.py](/home/lia/repos/my-projects/quant/src/quant_os/backtest/simple.py#L62)에서 같은 루프 안에서 시그널과 체결이 일어난다.

완료 기준:

- 다음 바 또는 다음 실행 시점 가격으로 체결하도록 바뀐다.
- 관련 회귀 테스트가 추가된다.

## P1

### 5. 실제 live adapter 1개 연결

목표:

- fail-closed stub를 넘어서 실제 broker/exchange adapter 하나를 연결한다.

현재 차이:

- [live.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/live.py#L54)는 stub다.

완료 기준:

- submit / cancel / sync / portfolio state를 실제 외부 API와 연결한다.
- broker raw payload를 저장한다.
- tiny live 전 smoke test 경로가 생긴다.

### 6. shadow-live 완성

목표:

- 실제 제출 없는 dry-run 경로를 유지하되, 실제 시장 데이터와 venue rule을 더 엄밀히 반영한다.
- shadow 결과와 실거래 경로를 비교하는 report를 만든다.

현재 차이:

- [shadow.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/shadow.py) 는 paper wrapper 성격이 강하다.

완료 기준:

- shadow report에 intent, simulated order/fill, venue-rule result, local-vs-external 차이가 정리된다.
- shadow 전용 test가 강화된다.

### 7. reconciliation 범위 확장

목표:

- balances, positions, open orders뿐 아니라 broker fills까지 비교한다.
- severity, incident log, manual intervention 사유를 더 명확히 남긴다.

현재 차이:

- [service.py](/home/lia/repos/my-projects/quant/src/quant_os/reconciliation/service.py#L31)는 현금/포지션/오픈오더 비교만 한다.

완료 기준:

- broker fills 비교가 추가된다.
- mismatch severity와 incident-friendly summary가 저장된다.
- unknown open order, unknown fill을 kill switch와 연결한다.

### 8. kill switch 조건 보강

목표:

- 설계에 적힌 최소 조건을 모두 커버한다.

현재 차이:

- reject rate spike, unexpected exposure 등은 아직 없다.

완료 기준:

- `unexpected exposure`
- `reject rate spike`
- `unknown open order 지속`
- `event write failure`
- `duplicate intent`
- `reconciliation unresolved`
  를 모두 평가 가능하다.

## P2

### 9. 운영 DB 기본값을 PostgreSQL 기준으로 정리

목표:

- 문서와 실행 기본값의 차이를 줄인다.

현재 차이:

- [base.yaml](/home/lia/repos/my-projects/quant/conf/base.yaml#L40)는 SQLite를 기본값으로 둔다.

완료 기준:

- 운영 예시는 PostgreSQL URL 기준으로 바뀐다.
- 로컬 개발용 SQLite는 별도 dev config로 분리된다.

### 10. daily report 외 운영 리포트 확장

목표:

- weekly review, alert-ready summary를 추가한다.

현재 차이:

- [reports.py](/home/lia/repos/my-projects/quant/src/quant_os/api/routes/reports.py#L14)는 daily latest만 제공한다.

완료 기준:

- weekly review artifact 또는 API가 추가된다.
- alerting에 바로 쓸 수 있는 compact summary가 생긴다.

### 11. scheduler / runbook / replay 계층 보강

목표:

- 수동 실행 중심 구조에서 정해진 배치 실행 구조로 한 단계 올린다.

현재 차이:

- [scheduler/__init__.py](/home/lia/repos/my-projects/quant/src/quant_os/scheduler/__init__.py)는 placeholder다.

완료 기준:

- 최소 일일 배치 entrypoint가 생긴다.
- replay test 골격이 실제 scenario를 담게 된다.
- 운영 runbook 문서가 추가된다.

## 지금 하지 않을 것

- 차트 시스템 확장
- 화려한 실시간 프론트
- 다전략/다브로커 확장
- 멀티마켓 동시 완성
- 예쁜 백테스트 UI 우선 작업

## 추천 실행 순서

1. `P0-1 raw payload`
2. `P0-2 normalization/quarantine`
3. `P0-3 strategy run registry`
4. `P0-4 backtest timing realism`
5. `P1-7 reconciliation 확장`
6. `P1-8 kill switch 보강`
7. `P1-5 live adapter 1개`
8. `P1-6 shadow-live 완성`
9. `P2-9 PostgreSQL 기본값 정리`
10. `P2-10/11 report + scheduler + replay`

## 판단

현재 가장 중요한 것은 새 기능이 아니라 `설계 의도 회복`이다.

즉, 앞으로의 작업 기준은 아래와 같다.

- 사용자 표면 확장보다 설계 정합성 우선
- 빠른 편의보다 raw/event/source-of-truth 우선
- live 준비 전 raw 저장, reconciliation, kill switch를 먼저 고정
