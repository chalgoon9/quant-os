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
- `data/raw/upbit_quotation/<dataset>/<timestamp>.json`
- `data/artifacts/validation/upbit_quotation/<dataset>/<timestamp>.json`
- validation 실패 시 `data/artifacts/quarantine/upbit_quotation/<dataset>/<timestamp>.json`

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

## 6. 백테스트 실행

설정에 정의된 전략을 데이터셋에 대해 실행:

```bash
uv run quant-os run-backtest --config conf/base.yaml --dataset krx_etf_daily
```

예상 출력 예시:

```text
run_id=backtest_xxxxx
strategy=daily_momentum
dataset=krx_etf_daily
path=/abs/path/to/latest.json
loaded_symbols=069500,114800
missing_symbols=122630,229200,233740
final_nav=10123456.0000
total_return=0.0123
max_drawdown=-0.0345
trade_count=12
```

저장 위치:

- `data/artifacts/backtests/latest.json`
- `strategy_runs` 테이블에 run metadata와 config fingerprint 기록

중요:

- 현재 백테스트는 신호 시점과 체결 시점을 분리합니다.
- 같은 종가로 신호를 만들고 같은 종가로 체결하는 단순 모델은 사용하지 않습니다.

## 7. 현재 모드 의미

- `paper`
  - 내부 paper execution 사용
- `shadow`
  - paper 경로를 재사용하되 shadow report와 venue-rule precheck를 포함
- `live`
  - `venue=upbit` 이고 필요한 환경변수가 있으면 `UpbitLiveAdapter`
  - 그렇지 않으면 fail-closed fallback stub

중요:

- 기본 설정은 `paper` 이며, `live`는 명시적으로 켜야 합니다.
- Upbit 자격 증명이 없으면 `live`는 자동으로 fail-closed stub로 남습니다.
- tiny live 전에는 소량 smoke test와 reconciliation 확인이 먼저 필요합니다.

## 8. API 백엔드 실행

대시보드와 API를 함께 서빙하는 FastAPI 실행:

```bash
uv run quant-os serve-api --config conf/base.yaml --host 127.0.0.1 --port 8000
```

기본 base URL:

- 대시보드: `http://127.0.0.1:8000`
- API: `http://127.0.0.1:8000/api`

대표 endpoint:

- `GET /api/system/runtime`
- `GET /api/ops/summary`
- `GET /api/backtests/latest`
- `GET /api/ops/orders`
- `GET /api/research/datasets`
- `POST /api/research/ingestion/upbit/daily`
- `GET /api/reports/daily/latest`

## 9. 프론트 실행

기본 운영 방식은 별도 preview 서버가 아니라 FastAPI 단일 포트 서빙입니다.

브라우저 접속:

- `http://127.0.0.1:8000`

프론트 production build 갱신이 필요하면:

```bash
cd frontend
npm run build
```

로컬 프론트 개발이 필요할 때만 Vite dev server를 따로 띄울 수 있습니다.
이 경우 API는 기본적으로 같은 머신의 `:8000`을 바라봅니다.

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 4173
```

다른 기기에서 접속하려면:

- `serve-api`를 `--host 0.0.0.0`으로 실행
- 사용하는 네트워크 정책에 맞는 프록시나 터널을 별도로 구성

## 9-1. 재부팅 후 자동 실행

이 머신에서 대시보드 서버를 재부팅 후에도 자동으로 올리려면 user-level systemd service를 설치합니다.

```bash
chmod +x scripts/install_user_service.sh
./scripts/install_user_service.sh
```

설치 결과:

- 템플릿: [quant-os.service.in](/home/lia/repos/my-projects/quant/deploy/systemd/quant-os.service.in)
- 실제 서비스 파일: `~/.config/systemd/user/quant-os.service`
- 서비스 이름: `quant-os.service`

상태 확인:

```bash
systemctl --user status quant-os.service
```

## 10. 현재 가능한 흐름

현재 저장소에서 바로 가능한 운영 흐름은 아래 수준입니다.

1. 설정 로드
2. migration 적용
3. 테스트 실행
4. read-only 시세 수집
5. 백테스트 실행과 결과 저장
6. API/프론트에서 최신 백테스트 결과 조회
7. paper/shadow skeleton 경로 검증

## 11. 현재 불가능하거나 미완성인 것

- venue별 live adapter 추가 확장
- weekly report / alert summary
- scheduler / replay / runbook 보강

## 12. 문서 위치

- 개요: [README.md](/home/lia/repos/my-projects/quant/README.md)
- API 조사/채택 기록: [api_reference.md](/home/lia/repos/my-projects/quant/docs/api_reference.md)
- 현재 문서: [usage_guide.md](/home/lia/repos/my-projects/quant/docs/usage_guide.md)
