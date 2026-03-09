# Usage Guide

기준일: 2026-03-10

이 문서는 현재 저장소 상태에서 바로 실행 가능한 명령과 사용 흐름을 정리합니다.

## 1. 준비

필수 조건:

- Python `>=3.12,<3.15`
- `uv`

프로젝트 루트에서 의존성 설치:

```bash
uv sync --extra dev
```

## 2. 기본 검증

전체 테스트 실행:

```bash
uv run --extra dev pytest -q
```

예상 결과:

- 모든 테스트 통과
- 현재 기준 통과 수는 환경에 따라 다를 수 있지만, 실패가 없어야 합니다.

DB migration 적용:

```bash
uv run python -m alembic upgrade head
```

예상 결과:

- Alembic이 `strategy_runs`, `orders`, `order_events`, `fills`, `positions_snapshot`, `cash_ledger`, `pnl_snapshot`, `reconciliation_log`, `kill_switch_events`를 사용할 수 있는 상태가 됩니다.

## 3. 설정 점검

기본 설정 파일:

- [base.yaml](/home/lia/repos/my-projects/quant/conf/base.yaml)

현재 기본값:

- 모드: `paper`
- 기준통화: `KRW`
- venue: `krx`
- 전략: `daily_momentum`

설정과 runtime wiring 점검:

```bash
uv run quant-os doctor --config conf/base.yaml
```

예상 출력 예시:

```text
system=quant-os-mvp
mode=paper
strategy=daily_momentum
research_dataset=krx_etf_daily
intent_lot_size=1
runtime=research:quant_os.duckdb,risk:intent,ledger:LedgerProjector,execution:PaperAdapter,recon:PortfolioReconciler,kill:KillSwitch,report:DailyReportGenerator
tables=cash_ledger,fills,kill_switch_events,order_events,orders,pnl_snapshot,positions_snapshot,reconciliation_log,strategy_runs
```

## 4. Upbit 시세 수집

현재 회원가입 없이 바로 붙어 있는 공식 API는 `Upbit Quotation API`입니다.

일봉 30개 수집:

```bash
uv run quant-os ingest-upbit-daily --config conf/base.yaml --market KRW-BTC --count 30
```

dataset 이름을 직접 지정:

```bash
uv run quant-os ingest-upbit-daily --config conf/base.yaml --market KRW-BTC --count 30 --dataset upbit_krw_btc_daily
```

예상 출력 예시:

```text
source=upbit_quotation
market=KRW-BTC
dataset=upbit_krw_btc_daily
path=/abs/path/to/bars.parquet
```

기본 dataset 이름 규칙:

- `KRW-BTC` -> `upbit_krw_btc_daily`
- `KRW-ETH` -> `upbit_krw_eth_daily`

저장 위치:

- `data/normalized/<dataset>/bars.parquet`

## 5. 수집 데이터 확인

Python one-liner 예시:

```bash
uv run python - <<'PY'
from pathlib import Path
from quant_os.research_store.store import ResearchStore

store = ResearchStore(
    root=Path("data/normalized"),
    duckdb_path=Path("research/quant_os.duckdb"),
)
bars = store.load_bars("upbit_krw_btc_daily", symbol="KRW-BTC")
print(len(bars))
print(bars[0].timestamp.isoformat(), bars[-1].timestamp.isoformat(), bars[-1].close)
PY
```

할 수 있는 것:

- dataset 전체 row 수 확인
- 특정 심볼 일봉 로드
- latest bar 확인

관련 코드:

- [store.py](/home/lia/repos/my-projects/quant/src/quant_os/research_store/store.py)

## 6. 현재 모드 의미

- `paper`
  - 내부 paper execution 사용
- `shadow`
  - paper 경로를 재사용하되 shadow report와 venue-rule precheck를 포함
- `live`
  - 현재는 실제 broker 연결이 없는 fail-closed stub

중요:

- 현재 `live`는 실거래가 아닙니다.
- 실제 broker `LiveAdapter`와 external sync/reconciliation이 아직 없으므로 live 제출 용도로 사용하면 안 됩니다.

## 7. API 백엔드 실행

대시보드용 FastAPI 실행:

```bash
uv run quant-os serve-api --config conf/base.yaml --host 0.0.0.0 --port 8000
```

기본 base URL:

- 대시보드: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/api`

대표 endpoint:

- `GET /api/system/runtime`
- `GET /api/ops/summary`
- `GET /api/ops/orders`
- `GET /api/research/datasets`
- `POST /api/research/ingestion/upbit/daily`
- `GET /api/reports/daily/latest`

## 8. 프론트 실행

기본 운영 방식은 별도 preview 서버가 아니라 FastAPI 단일 포트 서빙입니다.

브라우저 접속:

- `http://127.0.0.1:8000`
- LAN 접속 예시: `http://192.168.0.31:8000`

프론트 production build 갱신이 필요하면:

```bash
cd frontend
npm run build
```

개발용으로만 Vite dev server를 따로 띄우고 싶으면:

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 4173
```

## 9. 현재 가능한 흐름

현재 저장소에서 바로 가능한 운영 흐름은 아래 수준입니다.

1. 설정 로드
2. migration 적용
3. 테스트 실행
4. read-only 시세 수집
5. research/backtest 입력 데이터 저장
6. paper/shadow skeleton 경로 검증

## 10. 현재 불가능하거나 미완성인 것

- 실제 broker 주문 제출
- broker 잔고/체결/open order 동기화
- live reconciliation 실연결
- tiny live 운영

## 11. 문서 위치

- 개요: [README.md](/home/lia/repos/my-projects/quant/README.md)
- API 조사/채택 기록: [api_reference.md](/home/lia/repos/my-projects/quant/docs/api_reference.md)
- 현재 문서: [usage_guide.md](/home/lia/repos/my-projects/quant/docs/usage_guide.md)
