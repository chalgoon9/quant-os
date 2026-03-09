from __future__ import annotations

from pathlib import Path
import re
from datetime import timezone

import duckdb

from quant_os.domain.models import MarketBar
from quant_os.domain.types import to_decimal


class ResearchStore:
    def __init__(self, root: Path, duckdb_path: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.duckdb_path = Path(duckdb_path)
        self.duckdb_path.parent.mkdir(parents=True, exist_ok=True)

    def write_bars(self, dataset: str, bars: list[MarketBar]) -> Path:
        if not bars:
            raise ValueError("bars must not be empty")
        path = self._dataset_path(dataset)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        with self._connect() as connection:
            connection.execute(
                """
                create or replace temp table bars_tmp (
                    symbol varchar,
                    timestamp timestamp,
                    open double,
                    high double,
                    low double,
                    close double,
                    volume double
                )
                """
            )
            connection.executemany(
                "insert into bars_tmp values (?, ?, ?, ?, ?, ?, ?)",
                [_bar_to_record(bar) for bar in sorted(bars, key=lambda item: item.timestamp)],
            )
            connection.execute(
                f"copy (select * from bars_tmp order by timestamp) to '{path.as_posix()}' (format parquet)"
            )
        return path

    def load_bars(self, dataset: str, symbol: str | None = None) -> list[MarketBar]:
        self._ensure_view(dataset)
        query = f"select symbol, timestamp, open, high, low, close, volume from {dataset}"
        params: list[str] = []
        if symbol is not None:
            query += " where symbol = ?"
            params.append(symbol)
        query += " order by timestamp"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_bar(row) for row in rows]

    def list_datasets(self) -> list[str]:
        datasets: list[str] = []
        for path in sorted(self.root.glob("*/bars.parquet")):
            datasets.append(path.parent.name)
        return datasets

    def latest_timestamp(self, dataset: str) -> object | None:
        self._ensure_view(dataset)
        with self._connect() as connection:
            row = connection.execute(f"select max(timestamp) from {dataset}").fetchone()
        if row is None or row[0] is None:
            return None
        value = row[0]
        return value.replace(tzinfo=timezone.utc) if getattr(value, "tzinfo", None) is None else value

    def sample_bars(self, dataset: str, *, symbol: str | None = None, limit: int = 20) -> list[MarketBar]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        self._ensure_view(dataset)
        query = f"select symbol, timestamp, open, high, low, close, volume from {dataset}"
        params: list[object] = []
        if symbol is not None:
            query += " where symbol = ?"
            params.append(symbol)
        query += " order by timestamp desc limit ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_row_to_bar(row) for row in reversed(rows)]

    def latest_bar(self, dataset: str, symbol: str) -> MarketBar:
        self._ensure_view(dataset)
        with self._connect() as connection:
            row = connection.execute(
                f"""
                select symbol, timestamp, open, high, low, close, volume
                from {dataset}
                where symbol = ?
                order by timestamp desc
                limit 1
                """,
                [symbol],
            ).fetchone()
        if row is None:
            raise ValueError(f"no bar found for symbol={symbol} dataset={dataset}")
        return _row_to_bar(row)

    def count_rows(self, dataset: str) -> int:
        self._ensure_view(dataset)
        with self._connect() as connection:
            row = connection.execute(f"select count(*) from {dataset}").fetchone()
        assert row is not None
        return int(row[0])

    def _ensure_view(self, dataset: str) -> None:
        _validate_identifier(dataset)
        path = self._dataset_path(dataset)
        if not path.exists():
            raise FileNotFoundError(f"dataset does not exist: {path}")
        with self._connect() as connection:
            connection.execute(
                f"create or replace view {dataset} as select * from read_parquet('{_escape_sql_literal(path.as_posix())}')"
            )

    def _dataset_path(self, dataset: str) -> Path:
        return self.root / dataset / "bars.parquet"

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.duckdb_path))


def _bar_to_record(bar: MarketBar) -> tuple[object, ...]:
    return (
        bar.symbol,
        bar.timestamp.astimezone(timezone.utc).replace(tzinfo=None),
        float(bar.open),
        float(bar.high),
        float(bar.low),
        float(bar.close),
        float(bar.volume),
    )


def _row_to_bar(row: tuple[object, ...]) -> MarketBar:
    return MarketBar(
        symbol=str(row[0]),
        timestamp=row[1].replace(tzinfo=timezone.utc) if getattr(row[1], "tzinfo", None) is None else row[1],
        open=to_decimal(row[2]),
        high=to_decimal(row[3]),
        low=to_decimal(row[4]),
        close=to_decimal(row[5]),
        volume=to_decimal(row[6]),
    )


def _validate_identifier(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"invalid dataset identifier: {value}")


def _escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")
