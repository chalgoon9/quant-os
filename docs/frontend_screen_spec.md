# Frontend Screen Spec

기준일: 2026-03-10

이 문서는 실제 프론트 구현 직전 기준의 화면 명세입니다.

범위:

- 운영 조회 중심
- 수집 실행 포함
- destructive live control 제외

## 1. 공통 원칙

- 모든 화면은 모바일보다 데스크톱 우선으로 설계합니다.
- 상단 전역 상태 bar는 모든 페이지에 고정합니다.
- `kill switch active` 상태는 모든 페이지에서 최상단 경고 배너로 노출합니다.
- 숫자는 사람이 읽기 쉽게 formatting 하되, detail drawer에서는 원값 문자열도 표시할 수 있습니다.
- 로딩/빈 상태/에러 상태를 명시적으로 둡니다.
- live 관련 액션 버튼은 현재 넣지 않습니다.

## 2. 앱 구조

전역 레이아웃:

- 좌측 navigation
- 상단 status bar
- 본문 content area
- 우측 detail drawer optional

권장 메뉴:

1. `Overview`
2. `Orders`
3. `Research`
4. `Reports`
5. `Controls`

## 3. 전역 Status Bar

목적:

- 운영 모드를 한눈에 보여줌

표시 항목:

- `mode`
- `strategy`
- `venue`
- `execution adapter`
- `research dataset`

상태 표현:

- `paper`: neutral badge
- `shadow`: amber badge
- `live`: red badge

예외 상태:

- runtime fetch 실패 시 bar 전체를 error banner로 대체

## 4. Global Kill Switch Banner

표시 조건:

- active kill switch event 1개 이상

표시 내용:

- `KILL SWITCH ACTIVE`
- active reason list
- latest trigger time

사용자 액션:

- `Reports` 페이지로 이동 링크
- `Controls` 페이지로 이동 링크

## 5. Overview Page

목표:

- 운영 상태를 가장 빨리 확인하는 화면

구성 블록:

### 5.1 Runtime Summary

표시:

- mode
- venue
- strategy
- execution adapter

### 5.2 KPI Cards

카드:

- NAV
- Cash
- Realized PnL
- Unrealized PnL
- Total PnL

상태:

- 값 없음: `No snapshot yet`
- 로딩: skeleton cards
- 에러: compact error card

### 5.3 Reconciliation Card

표시:

- latest status
- mismatch count
- summary

색상:

- matched: green
- mismatch: amber/red
- unknown: neutral

액션:

- `View details` -> Reports page section 또는 detail drawer

### 5.4 Kill Switch Card

표시:

- clear / active
- active reasons

액션:

- `Open controls`

### 5.5 Position Summary Table

컬럼:

- symbol
- quantity
- average cost
- market price
- market value

상태:

- 포지션 없음: `No open positions`

## 6. Orders Page

목표:

- append-only execution 흐름을 읽기 쉽게 확인

구성:

### 6.1 Orders Table

컬럼:

- order_id
- symbol
- side
- status
- quantity
- filled_quantity
- updated_at

기능:

- status badge
- 정렬: updated_at desc 기본
- row click -> detail drawer open

상태:

- 로딩: table skeleton
- 빈 상태: `No orders yet`
- 에러: retry button

### 6.2 Order Detail Drawer

섹션:

- projection summary
- order event timeline
- fills table

projection summary:

- order_id
- intent_id
- broker_order_id
- status
- quantity
- filled_quantity
- created_at
- updated_at

event timeline:

- occurred_at
- status
- event_type
- reason

fills table:

- fill_id
- occurred_at
- quantity
- price
- fee
- tax

## 7. Research Page

목표:

- dataset 상태 확인과 Upbit 수집 실행

구성:

### 7.1 Dataset List Panel

컬럼:

- dataset
- row_count
- latest_timestamp

기능:

- dataset 선택
- refresh button

상태:

- 빈 상태: `No datasets yet`

### 7.2 Bars Preview Panel

표시:

- selected dataset
- symbol filter
- latest N rows
- optional small line/candlestick chart

컬럼:

- timestamp
- open
- high
- low
- close
- volume

상태:

- dataset 미선택: `Select a dataset`
- 데이터 없음: `No bars found`

### 7.3 Upbit Ingestion Form

입력:

- market
- count
- optional dataset

버튼:

- `Fetch Daily Bars`

성공 결과:

- source
- market
- dataset
- 저장 path

에러:

- API source failure
- validation error

## 8. Reports Page

목표:

- 운영 결과를 문장과 로그 수준으로 읽는 화면

구성:

### 8.1 Daily Report Viewer

표시:

- as_of
- nav/cash/pnl summary
- markdown body

상태:

- 보고서 생성 불가 시 explanatory empty state

### 8.2 Reconciliation Detail

표시:

- status
- summary
- mismatch_count
- issue list

issue list 컬럼:

- code
- message
- details

### 8.3 Kill Switch History Preview

표시:

- active events 우선
- trigger time
- reason
- details

현재 백엔드 기준:

- history full list는 아직 없으므로 active 중심으로 시작

## 9. Controls Page

목표:

- 위험 상태와 운영 제한을 명확히 보여주는 화면

구성:

### 9.1 Mode Notice

표시:

- paper / shadow / live
- live stub warning

### 9.2 Kill Switch Panel

표시:

- active 여부
- active reasons
- trigger values
- threshold values

### 9.3 External Sync Placeholder

표시:

- `Not yet connected`

이유:

- external broker sync가 아직 미구현이므로 placeholder를 명시적으로 둡니다.

## 10. Loading / Empty / Error Spec

### 10.1 Loading

- card: shimmer skeleton
- table: 5-row skeleton
- chart: grey block placeholder

### 10.2 Empty

- overview positions: `No open positions`
- orders: `No orders yet`
- datasets: `No datasets yet`
- bars preview: `Select a dataset`
- report: `No report available yet`

### 10.3 Error

모든 에러 박스 공통 요소:

- 간단한 제목
- 한 줄 설명
- `Retry` 버튼

분리 기준:

- backend unavailable
- dataset not found
- upstream source failure
- invalid request

## 11. 프론트 라우팅 제안

- `/` -> Overview
- `/orders`
- `/research`
- `/reports`
- `/controls`

## 12. 우선 구현 순서

1. Global layout + runtime status bar
2. Overview
3. Research
4. Reports
5. Orders
6. Controls

## 13. 이번 단계에서 절대 넣지 말 것

- live submit button
- broker credential input
- browser direct API key storage
- “kill switch reset” button
- order cancel button

## 14. 승인 기준

프론트 최초 구현이 승인되려면 다음이 만족되어야 합니다.

- runtime summary가 정상 표시될 것
- latest ops summary가 정상 표시될 것
- Upbit ingestion form이 동작할 것
- dataset/bars preview가 동작할 것
- orders detail drawer가 동작할 것
- kill switch active 상태가 전역 배너로 보일 것
