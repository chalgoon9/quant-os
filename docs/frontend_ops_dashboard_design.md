# Frontend Ops Dashboard Design

기준일: 2026-03-10

## 1. 목적

이 문서는 현재 `quant-os` 코드베이스에 프론트를 붙인다면 어디까지를 안전하게 노출할 수 있는지, 어떤 구조로 연결해야 하는지, 어떤 화면과 API가 필요한지를 정리합니다.

현재 결론은 다음입니다.

- 지금 바로 가능한 프론트 범위:
  - 운영 상태 조회
  - 리서치 데이터 조회
  - Upbit read-only 수집 실행
  - reconciliation / kill-switch / daily report 조회
- 지금 하면 안 되는 범위:
  - 실제 live 주문 UI
  - broker 계정 제어 UI
  - 실거래용 execution console

이 문서는 `현재 가능한 범위`만 기준으로 설계합니다.

## 2. 현재 백엔드 상태 요약

이미 존재하는 구성 요소:

- runtime 조립: [wiring.py](/home/lia/repos/my-projects/quant/src/quant_os/services/wiring.py)
- research storage: [store.py](/home/lia/repos/my-projects/quant/src/quant_os/research_store/store.py)
- operational persistence: [store.py](/home/lia/repos/my-projects/quant/src/quant_os/db/store.py)
- paper / shadow / live-stub execution adapter: [paper.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/paper.py), [shadow.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/shadow.py), [live.py](/home/lia/repos/my-projects/quant/src/quant_os/adapters/live.py)
- daily report 생성: [daily.py](/home/lia/repos/my-projects/quant/src/quant_os/reporting/daily.py)
- read-only 시세 수집: [upbit.py](/home/lia/repos/my-projects/quant/src/quant_os/data_ingestion/upbit.py)
- 현재 CLI surface: [main.py](/home/lia/repos/my-projects/quant/src/quant_os/cli/main.py)

현재 프론트가 활용할 수 있는 데이터 소스:

- `ResearchStore`
  - dataset별 Parquet bar 조회
- `OperationalStore`
  - 최신 PnL snapshot
  - 최신 reconciliation result
  - active kill switch event
  - order projection / order events / fills
- runtime 정보
  - mode
  - execution adapter 종류
  - configured strategy / intent / research dataset

즉, 프론트는 이미 “볼 데이터”는 어느 정도 있고, 없는 것은 HTTP API layer입니다.

## 3. 권장 아키텍처

권장 구조는 아래입니다.

```text
Browser SPA
  -> Thin HTTP API (FastAPI 권장)
    -> services.build_app_runtime(...)
    -> ResearchStore
    -> OperationalStore
    -> UpbitQuotationClient
```

핵심 원칙:

- 브라우저가 DB나 외부 API를 직접 치지 않습니다.
- 브라우저는 오직 내부 HTTP API만 호출합니다.
- API layer는 얇게 유지합니다.
- 기존 CLI와 서비스 계층을 재사용합니다.
- “조회”와 “실행”을 분리합니다.

이 구조를 권장하는 이유:

- 현재 저장소는 Python 중심입니다.
- runtime, store, reporting, ingestion 로직이 이미 Python 안에 있습니다.
- 따라서 프론트를 직접 붙이기보다, 얇은 Python API를 먼저 두는 편이 재사용성이 높고 위험이 낮습니다.

## 4. 기술 선택

권장 선택:

- 백엔드 API: `FastAPI`
- 프론트: `React + Vite + TypeScript`
- 데이터 fetching: `TanStack Query`
- 차트: `Recharts` 또는 `Lightweight Charts`
- 스타일: 기존 repo에는 프론트 스타일 체계가 없으므로, 과한 디자인 시스템 대신 작은 CSS module 또는 `vanilla-extract` 수준

선택 이유:

- FastAPI는 현재 Python 서비스와 자연스럽게 맞습니다.
- React/Vite는 작은 운영 대시보드 시작에 가장 무난합니다.
- SSR이 당장 필요하지 않으므로 Next.js까지 갈 이유는 현재 없습니다.

## 5. 범위 정의

### 5.1 이번 프론트에서 포함할 것

- 시스템 개요 대시보드
- latest NAV / cash / PnL 카드
- active kill switch 표시
- latest reconciliation 상태 표시
- open / recent orders 조회
- dataset 목록 조회
- dataset별 latest bars 조회
- Upbit 일봉 수집 실행 폼
- daily report markdown 조회

### 5.2 이번 프론트에서 제외할 것

- 로그인/권한 체계
- 실시간 websocket trading terminal
- broker live 주문 버튼
- 계좌이체/출금/정정/취소 같은 고위험 live control
- multi-user 기능

## 6. 정보 구조

추천 내비게이션:

1. `Overview`
2. `Orders`
3. `Research`
4. `Reports`
5. `Controls`

### 6.1 Overview

목표:

- 운영 상태를 한 화면에서 즉시 확인

구성:

- 상단 status bar
  - mode
  - strategy
  - venue
  - execution adapter
- KPI cards
  - NAV
  - Cash
  - Realized PnL
  - Unrealized PnL
  - Total PnL
- reconciliation card
  - latest status
  - summary
  - mismatch count
- kill switch card
  - clear / active
  - active reasons
- position summary table
  - symbol
  - quantity
  - average cost
  - market price

### 6.2 Orders

목표:

- append-only execution path를 운영 관점에서 볼 수 있게 함

구성:

- recent orders table
  - order_id
  - symbol
  - side
  - status
  - quantity
  - filled_quantity
  - updated_at
- order detail drawer
  - projection
  - order events timeline
  - fills table

중요:

- 이 화면은 조회 전용이 원칙입니다.
- live submit 버튼은 넣지 않습니다.

### 6.3 Research

목표:

- 수집된 dataset 확인과 Upbit 일봉 수집 실행

구성:

- dataset list
  - dataset name
  - latest timestamp
  - row count
- bars preview
  - symbol
  - OHLCV
  - latest N bars
- ingestion form
  - market
  - count
  - optional dataset name
  - run button

### 6.4 Reports

목표:

- daily report와 운영 상태 기록을 빠르게 읽기

구성:

- daily report markdown viewer
- latest reconciliation detail
- latest kill switch history

### 6.5 Controls

목표:

- 위험 상태를 명확히 보이되, destructive action은 노출하지 않음

구성:

- current mode badge
- kill switch active reasons
- external sync 상태 placeholder
- live unavailable notice

## 7. 권장 API surface

프론트가 직접 store를 알 필요가 없도록 아래 정도의 HTTP endpoint를 권장합니다.

### 7.1 System

- `GET /api/system/doctor`
  - `doctor` CLI와 유사한 summary 반환
- `GET /api/system/runtime`
  - mode, strategy, venue, adapter, configured dataset

### 7.2 Ops

- `GET /api/ops/summary`
  - latest pnl snapshot
  - latest reconciliation
  - active kill switch events
- `GET /api/ops/orders`
  - recent order projections
- `GET /api/ops/orders/{order_id}`
  - projection + order events + fills

### 7.3 Research

- `GET /api/research/datasets`
  - dataset names + row counts + latest timestamp
- `GET /api/research/datasets/{dataset}/bars?symbol=...&limit=...`
  - recent bars
- `POST /api/research/ingestion/upbit/daily`
  - market, count, optional dataset
  - return path + row count

### 7.4 Reports

- `GET /api/reports/daily/latest`
  - latest generated report payload
- `GET /api/ops/reconciliation/latest`
  - latest reconciliation detail
- `GET /api/ops/kill-switch/active`
  - active event list

## 8. API response shape 권장안

응답은 지나친 범용 envelope 없이 아래 정도로 단순하게 유지하는 편이 좋습니다.

예시:

```json
{
  "mode": "paper",
  "strategy": "daily_momentum",
  "venue": "krx",
  "execution_adapter": "PaperAdapter"
}
```

에러 응답:

```json
{
  "error": "dataset not found"
}
```

## 9. 상태 갱신 전략

실시간 websocket은 아직 과합니다. 현재는 polling으로 충분합니다.

권장 refresh:

- overview summary: 10초
- orders list: 5초
- research dataset list: manual refresh + 30초
- reports: manual refresh

이유:

- 현재 시스템은 HFT가 아닙니다.
- 하루 1회 수준 전략과 운영 모니터링에 websocket은 과합니다.

## 10. 프론트 UX 원칙

- `live` 모드일 때는 붉은 경고 배지와 함께 “실제 broker 미연결”을 명시합니다.
- `kill switch active` 상태는 모든 화면 상단에 고정 배너로 표시합니다.
- destructive action은 이번 단계에서 넣지 않습니다.
- ingestion 실행은 완료 결과와 저장 경로를 바로 보여줍니다.
- reconciliation mismatch는 color + summary + mismatch count를 함께 노출합니다.

## 11. 보안 / 운영 원칙

- 브라우저에 broker credential을 절대 두지 않습니다.
- 브라우저가 외부 broker API를 직접 호출하지 않습니다.
- 브라우저가 SQLite/DuckDB 파일 경로를 직접 다루지 않습니다.
- API layer에서만 config를 읽고 runtime을 생성합니다.
- live 관련 endpoint는 현재 만들지 않습니다.

## 12. 구현 우선순위

### 단계 A: 읽기 전용 운영 대시보드

- `GET /api/system/runtime`
- `GET /api/ops/summary`
- `GET /api/ops/kill-switch/active`
- `GET /api/ops/reconciliation/latest`
- Overview 화면

### 단계 B: 주문 조회

- `GET /api/ops/orders`
- `GET /api/ops/orders/{order_id}`
- Orders 화면

### 단계 C: 리서치 조회 및 수집 실행

- `GET /api/research/datasets`
- `GET /api/research/datasets/{dataset}/bars`
- `POST /api/research/ingestion/upbit/daily`
- Research 화면

### 단계 D: 리포트 화면

- `GET /api/reports/daily/latest`
- Reports 화면

## 13. 파일 구조 제안

프론트까지 구현한다면 권장 구조는 아래입니다.

```text
quant/
├─ src/quant_os/
│  ├─ api/
│  │  ├─ main.py
│  │  ├─ schemas.py
│  │  ├─ deps.py
│  │  └─ routes/
│  │     ├─ system.py
│  │     ├─ ops.py
│  │     ├─ research.py
│  │     └─ reports.py
├─ frontend/
│  ├─ index.html
│  ├─ package.json
│  └─ src/
│     ├─ app/
│     ├─ pages/
│     ├─ components/
│     ├─ hooks/
│     ├─ lib/
│     └─ styles/
└─ docs/
   └─ frontend_ops_dashboard_design.md
```

## 14. 구현 시 주의점

- `build_app_runtime()`를 request마다 과하게 만들지 않도록 dependency caching을 고려해야 합니다.
- `OperationalStore`와 `ResearchStore`는 read-heavy 용도로 thin wrapper를 하나 더 두는 편이 API layer에서 깔끔합니다.
- daily report는 현재 generator만 있고 저장소는 없습니다. 따라서 API에서는 “latest snapshot + latest recon + active kill switch”로 즉석 생성하거나, 별도 persistence를 추가해야 합니다.
- orders list endpoint를 만들려면 `OperationalStore`에 recent order projection list 메서드가 추가로 필요합니다.
- dataset list endpoint를 만들려면 `ResearchStore`에 dataset enumeration helper가 필요합니다.

## 15. 최종 권장

지금 프론트를 붙인다면 가장 안전한 시작점은 다음입니다.

1. FastAPI 기반 read-mostly backend 추가
2. React/Vite 기반 ops dashboard 추가
3. Overview + Research 화면부터 구현
4. Orders 화면 추가
5. live control UI는 보류

한 줄 요약:

현재 코드베이스에는 `운영 조회/수집 실행용 프론트`를 붙일 준비는 되어 있지만, `실거래 프론트`를 붙일 준비는 아직 되어 있지 않습니다.
