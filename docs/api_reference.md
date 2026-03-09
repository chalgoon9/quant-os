# API Reference

기준일: 2026-03-10

이 문서는 현재까지 조사한 공식 API 후보와, 실제로 이 저장소에 연결한 API를 기록합니다.

## 결정 요약

- 현재 실제 연결한 API: `Upbit Quotation API`
- 이유:
  - 공식 문서 기준 `Quotation`은 `Public API`라서 인증 없이 조회 가능합니다.
  - `페어`, `캔들(OHLCV)`, `체결`, `현재가`, `호가`를 지원합니다.
  - 회원가입이나 API Key 없이 바로 붙일 수 있는 공식 read-only 소스로는 가장 실용적입니다.
  - 현재 프로젝트의 `research_store -> strategy/backtest` 흐름에 바로 넣기 쉽습니다.
- 현재 의도적으로 연결하지 않은 것:
  - `KRX OPEN API`: 회원가입, 로그인, 인증키 신청, 활용 신청, 관리자 승인 필요
  - `SEC EDGAR APIs`: 무가입 가능하지만 시세가 아니라 공시/재무 데이터 중심
  - `Binance Spot Public Market Data`: 공식 public market data 이지만 현재 기본 운영 가정인 한국 사용자/국문 문맥/원화 기준에서는 Upbit가 더 단순
  - `Alpha Vantage`, `CoinGecko`: API key 필요

## 조사 결과

### 1. Upbit Quotation API

- 상태: 채택 및 연결 완료
- 인증: 불필요
- 용도: read-only 시세 조회
- 현재 연결한 엔드포인트:
  - `GET https://api.upbit.com/v1/market/all`
  - `GET https://api.upbit.com/v1/candles/days`
- 현재 코드 위치:
  - 클라이언트: [upbit.py](/home/lia/repos/my-projects/quant/src/quant_os/data_ingestion/upbit.py)
  - CLI: [main.py](/home/lia/repos/my-projects/quant/src/quant_os/cli/main.py)
  - 테스트: [test_upbit_ingestion.py](/home/lia/repos/my-projects/quant/tests/unit/test_upbit_ingestion.py)
- 현재 지원 기능:
  - 마켓 목록 조회
  - 일봉 조회
  - `ResearchStore` Parquet 적재
- 제한:
  - 주문/잔고/체결 관리 API는 연결하지 않았습니다.
  - 이는 `Quotation`만 연결한 것이고, `Exchange`는 회원가입 및 API Key가 필요합니다.

공식 문서:
- 개요: https://docs.upbit.com/reference
- 페어 목록 조회: https://docs.upbit.com/kr/reference/list-trading-pairs
- 일(Day) 캔들 조회: https://docs.upbit.com/kr/reference/list-candles-days
- 인증: https://docs.upbit.com/kr/reference/auth
- REST API 가이드: https://docs.upbit.com/kr/reference/rest-api-guide

### 2. KRX OPEN API

- 상태: 조사만 완료, 미연결
- 인증: 필요
- 미연결 이유:
  - 회원가입 후 로그인 필요
  - 인증키 신청 필요
  - 활용 신청 및 관리자 승인 필요
  - 현재 요구사항인 "회원가입 없이 바로 붙이기"를 만족하지 못합니다.

공식 문서:
- 서비스 이용방법: https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp
- 이용약관/인증키 조건: https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp

### 3. SEC EDGAR APIs

- 상태: 조사만 완료, 미연결
- 인증: 불필요
- 장점:
  - `data.sec.gov` 기반 JSON API를 인증 없이 사용할 수 있습니다.
  - 제출 서류, 공시 이력, XBRL 재무 데이터 접근에 적합합니다.
- 미연결 이유:
  - 현재 필요한 것은 `시장 시세 데이터`인데, SEC는 `공시/재무 데이터` 중심입니다.

공식 문서:
- Developer Resources: https://www.sec.gov/about/developer-resources
- EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

### 4. Binance Spot Public Market Data

- 상태: 조사만 완료, 미연결
- 인증: `NONE` 보안 타입은 인증 불필요
- 장점:
  - public market data 엔드포인트가 명확합니다.
  - 시세, 호가, 캔들 조회가 가능합니다.
- 미연결 이유:
  - 현재 한국 사용자 기준으로는 Upbit가 더 단순하고, 국문 문서 접근성도 높습니다.
  - "먼저 하나 붙인다"는 목적에서는 Upbit가 더 적합했습니다.

공식 문서:
- Request Security: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/request-security
- Market Data Endpoints: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints

### 5. Alpha Vantage

- 상태: 조사만 완료, 미연결
- 인증: API key 필요
- 미연결 이유:
  - `apikey`가 필수라서 "회원가입 없이 바로 사용" 조건에 맞지 않습니다.

공식 문서:
- https://www.alphavantage.co/documentation/

### 6. CoinGecko

- 상태: 조사만 완료, 미연결
- 인증: Demo API key 필요
- 미연결 이유:
  - Public/Demo라도 API key가 필요합니다.

공식 문서:
- https://docs.coingecko.com/v3.0.1/reference/authentication

## 현재 붙인 API 사용법

일봉을 `ResearchStore`로 적재:

```bash
uv run quant-os ingest-upbit-daily --config conf/base.yaml --market KRW-BTC --count 30
```

기본 dataset 이름 규칙:

- `KRW-BTC` -> `upbit_krw_btc_daily`
- `KRW-ETH` -> `upbit_krw_eth_daily`

CLI 출력 예시:

```text
source=upbit_quotation
market=KRW-BTC
dataset=upbit_krw_btc_daily
path=/abs/path/to/bars.parquet
```

## 현재 구현 범위

- `UpbitQuotationClient.list_markets(fiat=...)`
- `UpbitQuotationClient.fetch_daily_bars(market, count, to=None)`
- `ingest_upbit_daily_bars(...)`
- `quant-os ingest-upbit-daily`

현재 구현은 research/backtest용 read-only 수집 경로만 다룹니다.  
주문, 잔고, 실거래 adapter는 포함하지 않습니다.
