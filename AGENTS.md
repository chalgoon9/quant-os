# AGENTS.md

이 파일은 이 저장소에서 작업하는 개발 에이전트를 위한 실행 지침이다.
상세 설계는 `docs/specs/quant-os-mvp-design-spec.md`를 참고하되, 구현 중 판단이 필요할 때는 이 파일의 원칙을 우선 적용한다.

## 1. 프로젝트 목적

이 프로젝트는 기관용 트레이딩 시스템이 아니라, **혼자 만들고 혼자 운영 가능한 개인용 퀀트 운영체제(quant operating system)** 의 MVP를 구현하는 것이다.

핵심 목표는 아래 네 가지다.

- 구조가 올바를 것
- 상태 복원이 가능할 것
- 테스트가 가능할 것
- 나중에 실거래 adapter를 붙일 수 있을 것

수익률 최적화, 고빈도 경쟁, 화려한 실시간성은 이번 프로젝트의 우선순위가 아니다.

## 2. 기본 가정

질문이 있더라도 아래 기본값으로 먼저 전진한다.

- 사용자: 개인 개발자/개인 투자자
- 개발 역량: Python 중급 이상, 백엔드/API 경험 있음
- 금융공학 배경: 약함
- 거주/규제 환경: 대한민국
- 운영 스타일: 반자동 선호, 자동화는 점진적 확대
- 초기 목표: 하나의 시장, 하나의 전략, 하나의 코드베이스
- 초기 운영 모드: 하루 1~2시간 운영 가능 구조
- 초기 MVP 기본 시장: 국내 ETF 일봉
- 초기 전략: 단순 추세/모멘텀 기반 target exposure 전략
- 실행 모드: paper -> shadow-live -> tiny live
- 코드베이스: modular monolith
- 기술 기준: Python + Parquet/DuckDB + PostgreSQL

## 3. 절대 바꾸면 안 되는 원칙

1. 전략은 주문을 직접 넣지 않는다. 전략의 출력은 반드시 `TargetExposure` 다.
2. 주문 생성은 별도 계층이 담당한다. 현재 포지션과 target exposure의 차이를 계산해 `OrderIntent` 를 만든다.
3. 리스크 엔진은 전략 위에 있다. 전략이 낸 target exposure는 clip/reject/cap 될 수 있어야 한다.
4. 주문/체결은 append-only 이벤트로 저장한다. `orders` 는 projection 이고, 진실의 원천은 `order_events` 와 `fills` 다.
5. raw payload를 먼저 저장한다. 브로커/거래소 응답은 정규화 전에 보존 가능해야 한다.
6. fail-open 금지, fail-closed 우선. 상태가 불확실하면 신규 주문을 중단한다.
7. research storage 와 operational storage 를 분리한다.
8. paper / shadow-live / live 는 동일한 내부 인터페이스를 사용한다.
9. 초기 구현은 배치 우선이다. 스트리밍은 주문 상태 추적 같은 경계에만 둔다.
10. microservice, queue, 과도한 async, 과도한 실시간성은 도입하지 않는다.

## 4. 이번 MVP의 범위

이번 MVP는 아래 파이프라인이 end-to-end 로 동작하면 된다.

`시장 데이터 수집/정규화 -> 리서치 저장소 적재 -> 일봉 전략 실행 -> TargetExposure 생성 -> 리스크 엔진 검토 -> OrderIntent 생성 -> Paper Execution -> OrderEvent/FillEvent 기록 -> Ledger/PnL projection -> 리콘실리에이션 -> Daily report 생성`

이번 MVP에서 구현할 최소 범위:

- 프로젝트 골격
- 핵심 도메인 모델
- 운영용 DB 스키마
- Parquet/DuckDB + PostgreSQL 계층
- 일봉 전략 1개
- 리스크 엔진
- 주문 의도 생성기
- PaperAdapter
- ShadowLiveAdapter skeleton
- LiveAdapter base/stub
- 주문 상태 머신
- ledger / pnl projection
- reconciliation
- daily report
- unit / integration / simulation test 골격

## 5. 비목표

이번 작업에서 하지 않는다.

- 틱 데이터 기반 엔진
- HFT/초단타
- 옵션/선물/고레버리지
- 멀티전략 최적화
- 멀티브로커 동시 완성
- Kafka, Celery, Redis Queue, Kubernetes
- 복잡한 실시간 웹 프론트엔드
- ML/DL 기반 시그널링 우선 도입
- 과한 체결 시뮬레이터

## 6. 추천 기술 스택

- Python 3.12
- pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- DuckDB
- pandas 우선, 필요 시 polars 일부
- pytest
- CLI 는 `typer` 또는 `argparse`
- scheduler 는 cron 친화 구조 또는 APScheduler
- FastAPI 는 꼭 필요해질 때 skeleton 정도만

## 7. 저장소 구조

아래 구조를 기본으로 구현한다.

```text
quant_os/
├─ pyproject.toml
├─ README.md
├─ .env.example
├─ conf/
│  ├─ base.yaml
│  ├─ venues/
│  ├─ strategies/
│  ├─ risk/
│  └─ scheduler/
├─ data/
│  ├─ raw/
│  ├─ normalized/
│  ├─ features/
│  └─ artifacts/
├─ research/
│  ├─ notebooks/
│  ├─ experiments/
│  └─ reports/
├─ sql/
│  ├─ migrations/
│  └─ views/
├─ src/quant_os/
│  ├─ domain/
│  ├─ data_ingestion/
│  ├─ normalization/
│  ├─ research_store/
│  ├─ backtest/
│  ├─ strategy/
│  ├─ portfolio/
│  ├─ risk/
│  ├─ intent/
│  ├─ execution/
│  ├─ adapters/
│  ├─ ledger/
│  ├─ reconciliation/
│  ├─ reporting/
│  ├─ scheduler/
│  ├─ dashboard/
│  ├─ services/
│  └─ cli/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ simulation/
│  ├─ replay/
│  └─ shadow/
├─ scripts/
└─ docs/
```

## 8. 핵심 인터페이스 규약

반드시 아래 의미를 유지한다.

- `Strategy.generate_targets(asof) -> list[TargetExposure]`
- `RiskManager.review(targets, portfolio) -> list[TargetExposure]`
- `IntentGenerator.diff_to_intents(approved_targets, portfolio) -> list[OrderIntent]`
- `ExecutionAdapter.submit_intent(intent) -> SubmitResult`
- `ExecutionAdapter.cancel_order(order_uid)`
- `ExecutionAdapter.sync_events(since) -> iterable[OrderEvent | FillEvent]`
- `ExecutionAdapter.get_portfolio_state() -> PortfolioState`
- `LedgerProjector.apply_order_event(event)`
- `LedgerProjector.apply_fill_event(event)`

중요:

- `Strategy` 는 절대 `OrderIntent` 를 반환하지 않는다.
- `ExecutionAdapter` 는 paper/shadow/live 공통 계약을 만족해야 한다.
- `Ledger` 는 projection 이며, 원본 이벤트는 별도로 보존해야 한다.

## 9. 주문 상태 머신 요구사항

최소한 아래 상태 전이를 지원한다.

`PLANNED -> PRECHECK_REJECTED -> APPROVED -> SUBMITTING -> ACKNOWLEDGED -> WORKING -> PARTIALLY_FILLED -> FILLED -> CANCEL_REQUESTED -> CANCELLED -> CANCELLED_PARTIAL -> EXPIRED -> BROKER_REJECTED -> RECONCILE_PENDING -> MANUAL_INTERVENTION -> BUSTED`

필수 규칙:

- 상태 변경은 `order_events` 에 append 한다.
- `fills` 는 별도로 append 한다.
- `orders.status` 는 projection 이다.
- submit 결과가 불확실하면 재전송하지 말고 `RECONCILE_PENDING` 으로 보낸다.
- 같은 intent 의 중복 제출 방지 규칙을 둔다.

## 10. kill switch 요구사항

kill switch 는 선택 기능이 아니다.
최소한 아래 조건을 지원한다.

- 일일 손실 한도 초과
- 예상 외 포지션 또는 익스포저 발생
- stale market data
- 리콘실리에이션 불일치 해소 실패
- DB/event write 실패
- 동일 intent 중복 제출 감지
- 주문 reject rate 급증
- 상태 불명 open order 지속

기본 동작은 신규 주문 중단이며, 수동 reset 가능 구조로 둔다.

## 11. DB 요구사항

최소 테이블:

- `strategy_runs`
- `orders`
- `order_events`
- `fills`
- `positions_snapshot`
- `cash_ledger`
- `pnl_snapshot`
- `reconciliation_log`
- `kill_switch_events`

추가 규칙:

- `broker_order_id` / `broker_fill_id` dedupe 고려
- numeric precision 충분히 크게 설정
- projection 과 source of truth 구분

## 12. 구현 순서

아래 순서로 구현한다.

### Phase 1
- 프로젝트 골격
- 도메인 모델
- enum / id / types
- DB 스키마
- config
- CLI 골격
- README 초안
- 최소 unit test 골격

### Phase 2
- research storage
- simple backtest
- strategy
- risk
- intent generation

### Phase 3
- paper adapter
- order state machine
- ledger
- pnl projection

### Phase 4
- reconciliation
- kill switch
- daily report

### Phase 5
- shadow-live skeleton
- live adapter base/stub
- docs 정리
- 테스트 보강

각 phase 마다 남길 것:

- 추가/수정 파일 목록
- 핵심 설계 결정 이유
- 실행 방법
- 테스트 결과
- 남은 리스크 / TODO

## 13. 코드 스타일

- 복잡한 추상화보다 명시적 코드를 선호한다.
- 과도한 generic framework 를 만들지 않는다.
- 금융 도메인 이름을 명확히 쓴다.
- pure calculation 과 side effect 를 가능한 한 분리한다.
- magic number 는 config 또는 상수로 분리한다.
- 예외는 조용히 삼키지 말고 의미 있게 승격한다.
- 로깅은 사고 복기가 가능한 수준으로 남긴다.
- “추후 확장 가능성”을 이유로 현재 구조를 과하게 복잡하게 만들지 않는다.

## 14. 개발 에이전트 출력 형식

항상 아래 형식으로 응답한다.

1. 이번 단계의 목표
2. 명시적 가정
3. 구현 계획
4. 생성/수정할 파일 목록
5. 실제 코드 또는 패치
6. 실행 방법
7. 테스트 방법과 예상 결과
8. 남은 리스크 / 다음 단계

질문이 있더라도 먼저 합리적 기본값으로 전진한다.
설계 토론만 하지 말고 실제 코드, 파일 구조, 마이그레이션, 테스트를 생성한다.

## 15. 첫 작업 지시

지금 시작점은 Phase 1 이다.

완료 기준:

- 프로젝트가 import 가능할 것
- 기본 테스트가 실행 가능할 것
- DB schema 가 적용 가능할 것
- config 를 읽어 domain model 로 변환 가능할 것
- 다음 단계(backtest, paper execution)로 바로 들어갈 수 있을 것

상세 설계와 맥락은 `docs/specs/quant-os-mvp-design-spec.md` 를 참고하라.
