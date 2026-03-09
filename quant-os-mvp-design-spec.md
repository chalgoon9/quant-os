# Quant OS MVP Design Spec

위에 처음 기본 가정부터 명시하겠습니다.

이 문서는 “개인용 퀀트 운영체제(quant operating system)”를 구현할 때의 상세 설계 기준 문서다.
대상은 기관이 아니라 **혼자 만들고 혼자 운영 가능한 개인용 운용 시스템**이다. 따라서 이론적으로 멋진 구조보다 실제로 덜 망가지고, 복구 가능하며, 운영 가능한 구조를 우선한다.

---

## 1. 기본 가정

아래 조건을 기본값으로 둔다.

- 개발자는 Python 중급 이상이고, 백엔드/API 경험은 있으나 금융공학 배경은 약하다.
- 거주/규제 환경은 대한민국 기준이다.
- 운영 스타일은 기본적으로 반자동 선호이며, 자동화는 점진적으로 확대한다.
- 목표는 직접 운용이 1순위이고, 나중에 툴/리포트/데이터 서비스 같은 우회 수익화 가능성도 고려한다.
- 초기 시스템은 하나의 시장, 하나의 전략, 하나의 코드베이스를 원칙으로 한다.

초기 기본 추천은 다음과 같다.

- 하루 1~2시간 / 반자동 / 500만~3000만 원: 국내 ETF 또는 대형주 기반의 일봉/주봉 저회전 전략
- 자동화 지향 / 개발 역량 강함 / 3000만 원 이상: 업비트 현물의 4시간봉~일봉 추세/모멘텀
- 선물/옵션/고레버리지: 첫 시스템 대상으로 비추천

---

## 2. 핵심 결론

현실적인 개인용 퀀트 운영체제의 기본 형태는 아래와 같다.

- modular monolith
- batch-first
- event ledger
- internal paper / shadow-live / live 3모드

가장 중요한 설계 방향은 다음이다.

- 전략은 주문을 직접 넣지 않고 target exposure(목표 익스포저/목표 비중)만 제안한다.
- 주문, 체결, 원장, 리콘실리에이션, 리포트는 전략과 분리된 별도 계층이 책임진다.
- 브로커 샌드박스를 시스템의 기반으로 삼지 말고, 내부 paper adapter + shadow-live + 초소액 live 구조를 기본으로 본다.
- 초기에는 하나의 시장, 하나의 전략, 하나의 코드베이스에 집중한다.

---

## 3. 시스템 목표와 비목표

### 3.1 목표

이 시스템의 목표는 “좋은 시그널 찾기” 자체가 아니다. 진짜 목표는 아래와 같다.

- 리서치 결과를 재현 가능한 방식으로 저장할 것
- 전략이 낸 목표 비중을 리스크 한도 안에서 주문 의도로 변환할 것
- 체결, 잔고, 현금, PnL을 사후에 다시 계산할 수 있게 만들 것
- 장애가 나도 무슨 일이 있었는지 복원 가능하게 만들 것
- 하루가 끝나면 포지션, 현금, 손익, 이상 징후를 설명할 수 있게 만들 것

### 3.2 비목표

- 기관과 경쟁하는 초단타/HFT
- 시작부터 멀티마켓, 멀티전략, 멀티계정
- 복잡한 옵션/파생 구조
- 마이크로서비스, Kafka, Kubernetes, 분산 스트리밍
- 예쁜 백테스트를 우선하는 구조

---

## 4. 왜 이 구조가 개인에게 현실적인가

첫째, 실제 배포 단위를 하나로 유지할 수 있기 때문이다.
모듈은 분리하되 서비스는 쪼개지 않는 modular monolith가 개인에게 가장 관리 가능하다.

둘째, 전략과 주문을 분리하면 시장 규칙, 최소주문수량, 슬리피지, 리스크 컷, 계좌 상태 문제가 전략 코드에 섞이지 않는다.
리서치 코드와 실거래 코드가 함께 망가지는 상황을 줄일 수 있다.

셋째, append-only 이벤트 중심이면 현재 상태가 깨져도 재구성할 수 있다.
실거래에서 가장 위험한 것은 손실 자체보다 “현재 상태를 모르는 것”이다.

넷째, 리서치 저장소와 운영 저장소를 분리하면 분석 속도와 정합성을 동시에 가져갈 수 있다.
Parquet/DuckDB는 대량 시계열 분석에, PostgreSQL은 주문/체결/잔고 정합성에 적합하다.

다섯째, 같은 인터페이스로 paper -> shadow-live -> live를 밟게 하면 코드 경로가 덜 갈라지고 실거래 괴리가 줄어든다.

여섯째, 내부 알파 코어를 숨기고 외부에는 대시보드, 거래일지, 리포트, 데이터 QA 같은 비알파 계층만 노출할 수 있어 상품화 여지도 남는다.

---

## 5. 시스템 아키텍처 개요

```text
Control Plane:
config / secrets / scheduler / run registry / kill switch / notifications

Research Plane:
data ingestion -> normalization/validation -> Parquet data lake <-> DuckDB research store -> backtest engine -> strategy run artifacts

Decision Flow:
Target exposure proposals -> portfolio construction / risk engine -> order intent generator / diff

Execution Plane:
paper adapter / shadow-live adapter / live broker or exchange adapter -> normalized order API -> order submit/cancel/poll/websocket sync

State & Accounting:
order events + fills + balances + positions -> ledger / PnL + reconciliation -> reports / alerts / dashboard
```

이 구조에서 중요한 것은 전략이 시스템의 중심이 아니라, 전략이 운영 시스템 위에 얹혀 있다는 점이다.

---

## 6. 필수 모듈과 책임

### 6.1 데이터 수집

책임:
- 원천 데이터를 가져오고, 정규화 전에 raw payload를 먼저 보존한다.

입력:
- API key, 심볼 목록, 수집 주기, 마지막 커서/타임스탬프

출력:
- raw JSON/CSV/XML, ingestion log, source metadata

실패 시 처리:
- 부분 실패 시 마지막 정상 데이터를 덮어쓰지 않는다.
- quarantine 또는 재시도 경로를 둔다.

### 6.2 데이터 정규화/검증

책임:
- 심볼 매핑, 타임존 정렬, 단위 통일, instrument rule 표준화

입력:
- raw payload, instrument master, 참조 데이터

출력:
- normalized market data, validation report, quarantine records

실패 시 처리:
- 불확실한 보정은 silent fix 하지 않는다.
- 필요 시 hard fail 또는 격리 처리한다.

### 6.3 리서치 저장소

책임:
- 시계열, feature, 실험 결과, 파라미터, 리포트를 저장

입력:
- normalized market data, feature pipeline outputs, 백테스트 결과

출력:
- Parquet datasets, DuckDB views, experiment artifacts

실패 시 처리:
- live trading의 단기 중단 사유는 아니지만, 새로운 전략 승급은 중단한다.

### 6.4 백테스트 엔진

책임:
- target exposure를 과거 데이터에 재생하고 비용/라운딩/최소주문규칙을 반영

입력:
- market data, strategy config, commission/slippage model, risk rules

출력:
- equity curve, trade list, position path, turnover, drawdown, parameter report

실패 시 처리:
- 불완전한 백테스트 결과를 저장하지 않는다.

### 6.5 시그널 엔진

책임:
- 최종적으로 `TargetExposure[]` 를 생성

입력:
- features, current market state, strategy config

출력:
- `TargetExposure[]`

실패 시 처리:
- 기본 동작은 신규 주문 금지

### 6.6 포트폴리오/리스크 엔진

책임:
- 전략 출력에 종목/현금/손실/회전율/거래 가능 여부 한도를 적용

입력:
- target exposures, current positions, cash, risk config

출력:
- approved targets, clipped targets, rejected targets, rejection reasons

실패 시 처리:
- fail-closed. 신규 주문 없음.

### 6.7 주문 의도 생성기

책임:
- 승인된 target과 현재 포지션 차이를 계산해 `OrderIntent[]` 생성

입력:
- approved targets, current positions, account cash, instrument rules

출력:
- `OrderIntent[]`

실패 시 처리:
- 수량 계산/라운딩이 불확실하면 해당 intent를 폐기하거나 0주문 처리

### 6.8 브로커/거래소 어댑터

책임:
- 내부 주문 의도를 외부 API 호출로 변환하고, 외부 응답을 내부 표준 이벤트로 변환

입력:
- OrderIntent, credentials, account metadata, venue rules

출력:
- submit ack/nack, normalized order events, normalized fill events, normalized balance snapshots

실패 시 처리:
- submit 결과가 불확실하면 재전송하지 않는다.
- 먼저 주문 조회/미체결 조회/리콘실리에이션으로 상태를 확인한다.

### 6.9 주문 집행 및 체결 추적

책임:
- REST polling과 WebSocket 이벤트를 합쳐 주문 상태 머신 관리

입력:
- adapter responses, polling results, websocket streams

출력:
- order state transitions, fill records, execution metrics

실패 시 처리:
- 이벤트 누락, 중복, 역순 도착을 전제로 설계한다.
- 추론 불가능한 상태는 `RECONCILE_PENDING` 으로 보낸다.

### 6.10 원장(ledger)

책임:
- 현금 이동, 수수료, 세금, 체결 기반 포지션 inventory, realized/unrealized PnL 계산 근거 보존

입력:
- fills, fees, tax rules, 입출금, corporate action

출력:
- cash ledger entries, inventory lots, pnl snapshots

실패 시 처리:
- 원장 계산이 늦더라도 raw order/fill event는 반드시 보존한다.
- raw event 저장 실패는 kill switch 사유다.

### 6.11 리콘실리에이션

책임:
- 로컬 상태와 외부 브로커/거래소 상태를 비교

입력:
- local projections, broker balances, broker open orders, broker fills

출력:
- reconciliation diff, severity, auto-fix actions, incident log

실패 시 처리:
- 설명 불가능한 차이는 신규 주문 중단 사유

### 6.12 리포트/알림/대시보드

책임:
- 하루/주간 단위 운영 보고서, 이상 탐지, 체결 품질, drawdown, exposure, cash, mismatch 요약

입력:
- strategy runs, pnl snapshots, reconciliation logs, kill switch events

출력:
- daily report, weekly review, alerts, dashboard views

실패 시 처리:
- 리포트 실패만으로 live를 중단할 필요는 없지만, 장기적인 알림 부재는 운영 리스크로 관리한다.

---

## 7. 핵심 설계 원칙

1. 전략은 주문을 직접 넣지 않고 target exposure만 제안한다.
2. 포트폴리오 엔진과 리스크 엔진은 전략 위에 있다.
3. 주문/체결은 append-only 이벤트로 저장한다.
4. raw broker/exchange payload를 먼저 저장한다.
5. fail-open보다 fail-closed를 우선한다.
6. 배치 우선, 스트리밍은 실행 경계에서만 사용한다.
7. 연구 저장소와 운영 저장소를 분리한다.
8. paper/shadow/live는 하나의 코드베이스와 하나의 인터페이스를 공유한다.
9. notebook -> research backtest -> promotion backtest -> paper -> shadow-live -> tiny live -> scaled live 승급 절차를 강제한다.
10. 수동 개입은 허용하되 항상 기록한다.
11. 설정은 코드보다 명시적 config를 우선한다.
12. 자본 보호가 시그널 신선도보다 우선한다.

---

## 8. 추천 기술 스택

- 핵심 언어: Python
- 도메인 모델: dataclass 또는 Pydantic
- DB access: SQLAlchemy 2.x
- 분석: DuckDB SQL + pandas 중심
- 테스트: pytest
- 내부 대시보드: 필요 시 Streamlit
- 내부 control API: FastAPI는 2단계 이후 선택적으로 도입
- scheduler: cron/systemd timer 또는 APScheduler
- queue: 초기에는 사용하지 않음

### 저장소 분리 원칙

- Parquet + DuckDB: 시장 데이터, feature, 백테스트 결과, 리서치 아티팩트
- PostgreSQL: orders, order_events, fills, positions_snapshot, cash_ledger, pnl_snapshot, strategy_runs, reconciliation_log, kill_switch_events

---

## 9. 추천하지 않는 설계

- 틱 단위 초반 설계
- 옵션부터 시작
- 마이크로서비스부터 시작
- 리스크 엔진 없는 자동주문
- 예쁜 백테스트 우선
- 외부 샌드박스 의존 구조

---

## 10. 운영 시간별 설계 차이

### 10.1 하루 1~2시간 운영 모드

- 국내 ETF/대형주 또는 crypto 일봉
- 하루 1회 또는 주 1~3회 의사결정
- 장 종료 후 시그널 생성
- 다음 세션에 한 번만 주문
- 반자동 승인
- 예외 알림 위주
- 로컬 + 저가 VPS 수준 인프라

핵심은 운영 마찰 최소화다.

### 10.2 전업 운영 모드

- crypto 현물 4시간~1시간 또는 국내주식 일중 신호
- 항상 켜진 executor daemon 가능
- 더 자주 리콘실리에이션
- 로그/메트릭/헬스체크 강화
- 자동 비중 확대

핵심은 속도보다 운영 깊이다.

---

## 11. 자본 규모별 현실적 차이

### 11.1 500만 원

- 운영 체계 검증이 우선
- 거래 빈도와 회전율을 낮게
- 종목 수도 적게 유지
- 수익 극대화보다 검증된 운영 루틴 확보가 중요

### 11.2 3000만 원

- 하나의 코어 전략 + 하나의 리스크 오버레이 정도가 현실적
- 정기 리콘, 체결 품질, 월간 성과 관리가 정당화됨

### 11.3 1억 원

- 여전히 기관이 아니므로 멀티마켓/멀티브로커 동시 시작은 피함
- 리콘, 원장, 세금 export, 모니터링, 실행 정책 문서화가 필수 수준

---

## 12. 직접 매매 외 수익화 구조

### 12.1 내부 비공개 코어

- 전략 규칙
- feature 생성식
- 파라미터
- live risk rules
- execution policy
- strategy selection logic
- shadow-live 비교 리포트 원본

### 12.2 외부 공개용 제품 계층

- 트레이딩 저널
- 포트폴리오 대시보드
- 리스크 체크리스트
- 리포트 자동 생성기
- 데이터 품질 검증기
- broker abstraction 툴
- 리콘실리에이션 템플릿

### 12.3 알파 유출 방지 구조

- 내부 코어 DB와 외부 제품 DB 분리
- 외부 공개 데이터는 지연 공개
- 실시간 target/position 노출 금지
- 요약 통계 중심 공개
- 전략 버전과 파라미터 비공개
- 체결 로그 익명화 또는 버킷화

---

## 13. 단계별 개발 로드맵

### 13.1 30일

- 시장 하나 선택
- 전략 하나 선택
- Parquet raw/normalized 레이어 구축
- DuckDB 환경 구축
- 핵심 도메인 모델 정의
- backtest v0
- paper adapter v0
- PostgreSQL 기본 운영 테이블
- 일일 리포트 템플릿

목표: 리서치 -> target exposure -> paper order -> ledger -> report 가 한 번 끝까지 돈다.

### 13.2 90일

- live adapter 1개 연결 또는 skeleton
- shadow-live 완성
- 리스크 엔진 완성
- 주문 상태 머신 구현
- 리콘실리에이션 구현
- 내부 대시보드
- 예외 알림
- 백테스트/실거래 공통 비용 모델 일치
- tiny live 테스트

목표: 실거래 직전 수준

### 13.3 6개월

- restart/replay 가능
- raw payload archive 안정화
- 리콘 자동화 강화
- drawdown/kill switch 튜닝
- 월간 운영 회고 루틴 정착
- 외부 공개용 저널/리포트 계층 초안

목표: 망가져도 복구되는 시스템

### 13.4 12개월

- 두 번째 전략 또는 시장 검토
- 내부/외부 DB 분리
- replay 기반 simulation test set 확보
- 세금/월간 원장 export 자동화
- 문서화 및 runbook 정리

목표: 확장 가능한 운영체제

---

## 14. DB 스키마 초안

최소 엔티티는 아래와 같다.

- orders
- order_events
- fills
- positions_snapshot
- cash_ledger
- pnl_snapshot
- strategy_runs
- reconciliation_log
- kill_switch_events

핵심 규칙:

- `orders` 는 현재 상태 projection
- 진실의 원천은 `order_events` 와 `fills`
- `broker_order_id` / `broker_fill_id` 기반 dedupe 고려
- numeric precision 충분히 크게 설정

---

## 15. 권장 폴더 구조

```text
quant_os/
- conf/
- data/
- research/
- sql/
- src/quant_os/domain
- src/quant_os/data_ingestion
- src/quant_os/normalization
- src/quant_os/research_store
- src/quant_os/backtest
- src/quant_os/strategy
- src/quant_os/portfolio
- src/quant_os/risk
- src/quant_os/intent
- src/quant_os/execution
- src/quant_os/adapters
- src/quant_os/ledger
- src/quant_os/reconciliation
- src/quant_os/reporting
- src/quant_os/scheduler
- src/quant_os/dashboard
- src/quant_os/services
- src/quant_os/cli
- tests/unit
- tests/integration
- tests/simulation
- tests/replay
- tests/shadow
- docs/
```

핵심은 `strategy/` 와 `execution/` 을 강하게 분리하는 것이다.

---

## 16. 핵심 Python 인터페이스 설계 기준

다음 의미를 유지한다.

- `Strategy.generate_targets(asof) -> list[TargetExposure]`
- `RiskManager.review(targets, portfolio) -> list[TargetExposure]`
- `IntentGenerator.diff_to_intents(approved_targets, portfolio) -> list[OrderIntent]`
- `ExecutionAdapter.submit_intent(intent) -> SubmitResult`
- `ExecutionAdapter.cancel_order(order_uid)`
- `ExecutionAdapter.sync_events(since) -> iterable[OrderEvent | FillEvent]`
- `ExecutionAdapter.get_portfolio_state() -> PortfolioState`
- `LedgerProjector.apply_order_event(event)`
- `LedgerProjector.apply_fill_event(event)`

가장 중요한 인터페이스 원칙은 세 가지다.

- `Strategy` 는 절대 주문을 만들지 않고 `TargetExposure` 만 반환한다.
- `ExecutionAdapter` 는 paper/shadow/live 모두 같은 계약을 따른다.
- `Ledger` 는 이벤트를 받아 projection만 만들며, 원본 이벤트는 별도로 보존한다.

---

## 17. 주문 상태 머신 설계

최소 지원 상태:

- PLANNED
- PRECHECK_REJECTED
- APPROVED
- SUBMITTING
- ACKNOWLEDGED
- WORKING
- PARTIALLY_FILLED
- FILLED
- CANCEL_REQUESTED
- CANCELLED
- CANCELLED_PARTIAL
- EXPIRED
- BROKER_REJECTED
- RECONCILE_PENDING
- MANUAL_INTERVENTION
- BUSTED

운영 규칙:

- 상태 변경은 전부 `order_events` 에 append 한다.
- `fills` 는 주문 상태와 분리해 append 한다.
- `orders.status` 는 projection 이다.
- submit 결과가 불확실하면 재전송하지 말고 `RECONCILE_PENDING` 으로 보낸다.
- 같은 intent에 대한 중복 제출 방지 규칙(idempotency)을 둔다.

---

## 18. kill switch 설계

kill switch는 자동매매 자격 요건이다.
최소한 아래 조건을 지원한다.

- 일일 손실이 NAV 한도 초과
- 예상 외 포지션 또는 익스포저 발생
- stale market data
- 리콘실리에이션 불일치 해소 실패
- DB 또는 event write 실패
- 동일 intent 중복 제출 감지
- 주문 reject rate 급증
- 상태 불명 open order 지속

초기에는 민감한 threshold를 config로 두고, 기본 동작은 신규 주문 중단 + 수동 reset 필요로 설계한다.

---

## 19. 백테스트와 실거래 괴리 축소 체크리스트

- survivorship bias 제거 여부
- delisting/거래정지 반영 여부
- 조정주가/비조정주가 혼용 여부
- 배당/분할/합병 반영 여부
- 리밸런싱 시점과 체결 시점 분리 여부
- 종가로 시그널 만들고 같은 종가로 체결시키는 오류 여부
- 최소주문수량/호가단위/최소주문금액 반영 여부
- 수수료/세금/슬리피지/환전 비용 반영 여부
- 부분체결 가능성 반영 여부
- 미체결 이월 규칙 여부
- 주문 거부/인증 실패/장애 재시도 모델 여부
- 타임존/거래일 캘린더 일치 여부
- 전략 데이터와 live adapter 데이터 정의 일치 여부
- 미래 정보 누수 여부
- 시점 당시 기준 universe selection 여부
- cash/buying power 기준 sizing 여부
- backtest와 live의 리스크 룰 일치 여부
- restart 후 상태 복원 가능 여부
- shadow-live와 backtest 결과의 합리적 일치 여부

---

## 20. 테스트 전략

### 20.1 unit test

- indicator/feature
- position sizing
- risk clipping
- order rounding
- fee/tax
- state machine
- PnL projection

### 20.2 integration test

- adapter mapping
- DB read/write
- scheduler flow
- order submit -> event sync -> ledger projection
- reconciliation path

### 20.3 simulation test

- partial fill
- timeout
- duplicate event
- out-of-order event
- restart/recovery
- kill switch trigger

### 20.4 shadow-live 검증

- 실제 제출 없는 dry-run 경로
- 실제 시장 데이터와 venue rule을 적용한 가상 order/fill/ledger 생성
- event/log/report 생성 여부 확인

---

## 21. 최종 판단 기준

### 가능한 경우

- 시장 하나
- 전략 하나
- 저회전
- liquid asset
- 하루 1회 수준 의사결정
- target exposure 기반
- paper -> shadow -> tiny live
- 원장과 리콘 포함한 운영 설계

### 어려운 경우

- 고빈도
- 옵션/복합파생
- 멀티마켓 동시 시작
- 브로커별 체결 로직을 동시에 맞추려는 시도
- 전략보다 인프라를 먼저 파는 구조
- 실시간 알파 판매를 병행하는 구조

### 추천 접근

- modular monolith
- Parquet/DuckDB + PostgreSQL 분리
- 전략은 target exposure만 제안
- 리스크 엔진 중앙집중
- 주문/체결 append-only
- 내부 paper/shadow/live 3모드
- 소액 live로 단계적 검증

### 비추천 접근

- 틱 단위부터 설계
- 옵션부터 시작
- 마이크로서비스부터 시작
- 리스크 엔진 없는 자동주문
- 예쁜 백테스트 우선
- 외부 샌드박스만 믿는 구조

---

## 22. 바로 구현 가능한 MVP 정리

기본 MVP는 아래처럼 생각한다.

- 시장: 국내 ETF
- 빈도: 일봉
- 전략: 단순 추세/모멘텀
- 운영: 반자동
- 코드베이스: 하나
- 모드: paper + shadow + tiny live
- 저장소: Parquet/DuckDB + PostgreSQL

구체 사양:

- universe: 유동성 높은 ETF 5~10개
- 시그널: 20/60일 모멘텀 + 장기 추세 필터
- 출력: target weights only
- 리스크: 종목당 최대 비중, 현금 최소 비중, 리밸런스 turnover 상한, 일일 손실 kill switch
- 집행: 하루 1회 intent 생성, 다음 거래 세션 1회 집행, 지정가/시장가 정책은 config화
- 원장: fills 기반 포지션 lot, 수수료/세금/현금 흐름 기록
- 리콘: 장 종료 후 1회 필수
- 리포트: daily positions/cash/pnl/anomaly report
- 검증 순서: 30거래일 paper -> 30거래일 shadow -> 50만 원 이하 tiny live -> 이상 없으면 점진 확대

자동화 지향 대체 MVP가 필요하면 시장만 바꿔 다음과 같이 볼 수 있다.

- 시장: 업비트 KRW 현물
- 빈도: 4시간봉
- 전략: 추세 + 변동성 캡
- 나머지 구조는 동일

---

## 23. 혼자 만드는 경우 가장 먼저 포기해야 할 욕심 5개

1. 첫 달부터 완전자동 24/7 무인 운영
2. 시장 여러 개를 동시에 잡는 욕심
3. 틱/호가/HFT 흉내
4. 수익률이 예뻐 보이도록 백테스트를 다듬는 욕심
5. 내부 알파 코어와 외부 판매용 제품을 처음부터 같이 만드는 욕심

정말 먼저 포기해야 하는 것은 “멋있어 보이는 설계”다.
혼자 만드는 퀀트 운영체제는 전략 엔진보다 망가지지 않는 운영 루프가 먼저다.

다음 단계로 바로 이어가려면, 이 설계에서 **국내 ETF MVP용 실제 `conf/`, DB migration, Python 인터페이스 코드 골격부터 뽑는 순서**를 추천한다.
