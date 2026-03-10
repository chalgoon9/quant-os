from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path

from quant_os.backtest.simple import EquityPoint, SimulatedTrade
from quant_os.domain.enums import OrderSide


@dataclass(frozen=True)
class StoredBacktestResult:
    run_id: str
    strategy_id: str
    strategy_name: str
    strategy_kind: str
    strategy_version: str
    dataset: str
    profile_id: str
    generated_at: datetime
    as_of: datetime
    initial_cash: Decimal
    final_nav: Decimal
    total_return: Decimal
    max_drawdown: Decimal
    trade_count: int
    loaded_symbols: tuple[str, ...]
    missing_symbols: tuple[str, ...]
    equity_curve: tuple[EquityPoint, ...]
    trades: tuple[SimulatedTrade, ...]
    tags: tuple[str, ...] = ()
    notes: str | None = None


class BacktestArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root) / "backtests"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, result: StoredBacktestResult) -> Path:
        strategy_root = self.root / result.strategy_id
        strategy_root.mkdir(parents=True, exist_ok=True)
        file_path = strategy_root / f"{result.generated_at.strftime('%Y%m%dT%H%M%SZ')}_{result.run_id}.json"
        latest_path = self.root / "latest.json"
        payload = _result_to_payload(result)
        _write_json(file_path, payload)
        _write_json(latest_path, payload)
        return file_path

    def latest(self) -> StoredBacktestResult:
        latest_path = self.root / "latest.json"
        if not latest_path.exists():
            raise FileNotFoundError(f"latest backtest result not found: {latest_path}")
        return _payload_to_result(json.loads(latest_path.read_text(encoding="utf-8")))

    def load(self, run_id: str) -> StoredBacktestResult:
        matches = sorted(self.root.glob(f"**/*_{run_id}.json"))
        if not matches:
            raise FileNotFoundError(f"backtest run not found: {run_id}")
        return self.load_path(matches[-1])

    def load_path(self, path: str | Path) -> StoredBacktestResult:
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"backtest artifact not found: {target}")
        return _payload_to_result(json.loads(target.read_text(encoding="utf-8")))


def _result_to_payload(result: StoredBacktestResult) -> dict[str, object]:
    return {
        "run_id": result.run_id,
        "strategy_id": result.strategy_id,
        "strategy_name": result.strategy_name,
        "strategy_kind": result.strategy_kind,
        "strategy_version": result.strategy_version,
        "dataset": result.dataset,
        "profile_id": result.profile_id,
        "generated_at": result.generated_at.isoformat(),
        "as_of": result.as_of.isoformat(),
        "initial_cash": str(result.initial_cash),
        "final_nav": str(result.final_nav),
        "total_return": str(result.total_return),
        "max_drawdown": str(result.max_drawdown),
        "trade_count": result.trade_count,
        "loaded_symbols": list(result.loaded_symbols),
        "missing_symbols": list(result.missing_symbols),
        "tags": list(result.tags),
        "notes": result.notes,
        "equity_curve": [
            {
                "timestamp": point.timestamp.isoformat(),
                "nav": str(point.nav),
                "cash": str(point.cash),
            }
            for point in result.equity_curve
        ],
        "trades": [
            {
                "timestamp": trade.timestamp.isoformat(),
                "symbol": trade.symbol,
                "side": trade.side.value,
                "quantity": str(trade.quantity),
                "price": str(trade.price),
                "notional": str(trade.notional),
            }
            for trade in result.trades
        ],
    }


def _payload_to_result(payload: dict[str, object]) -> StoredBacktestResult:
    return StoredBacktestResult(
        run_id=str(payload["run_id"]),
        strategy_id=str(payload.get("strategy_id") or payload["strategy_name"]),
        strategy_name=str(payload["strategy_name"]),
        strategy_kind=str(payload.get("strategy_kind") or "daily_momentum"),
        strategy_version=str(payload.get("strategy_version") or "runtime"),
        dataset=str(payload["dataset"]),
        profile_id=str(payload.get("profile_id") or "runtime-config"),
        generated_at=datetime.fromisoformat(str(payload["generated_at"])),
        as_of=datetime.fromisoformat(str(payload["as_of"])),
        initial_cash=Decimal(str(payload["initial_cash"])),
        final_nav=Decimal(str(payload["final_nav"])),
        total_return=Decimal(str(payload["total_return"])),
        max_drawdown=Decimal(str(payload["max_drawdown"])),
        trade_count=int(payload["trade_count"]),
        loaded_symbols=tuple(str(symbol) for symbol in payload.get("loaded_symbols", [])),
        missing_symbols=tuple(str(symbol) for symbol in payload.get("missing_symbols", [])),
        tags=tuple(str(tag) for tag in payload.get("tags", [])),
        notes=str(payload["notes"]) if payload.get("notes") is not None else None,
        equity_curve=tuple(
            EquityPoint(
                timestamp=datetime.fromisoformat(str(item["timestamp"])),
                nav=Decimal(str(item["nav"])),
                cash=Decimal(str(item["cash"])),
            )
            for item in payload.get("equity_curve", [])
        ),
        trades=tuple(
            SimulatedTrade(
                timestamp=datetime.fromisoformat(str(item["timestamp"])),
                symbol=str(item["symbol"]),
                side=OrderSide(str(item["side"])),
                quantity=Decimal(str(item["quantity"])),
                price=Decimal(str(item["price"])),
                notional=Decimal(str(item["notional"])),
            )
            for item in payload.get("trades", [])
        ),
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
