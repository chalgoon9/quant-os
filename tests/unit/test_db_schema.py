from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_sqlalchemy_metadata_contains_required_tables() -> None:
    from quant_os.db.base import Base
    from quant_os.db.schema import REQUIRED_TABLES

    assert REQUIRED_TABLES.issubset(set(Base.metadata.tables))


def test_alembic_upgrade_creates_phase1_tables(tmp_path: Path) -> None:
    from quant_os.db.schema import REQUIRED_TABLES

    db_path = tmp_path / "phase1.db"
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    script_location = Path(__file__).resolve().parents[2] / "alembic"

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)

    assert REQUIRED_TABLES.issubset(set(inspector.get_table_names()))


def test_strategy_runs_table_exposes_backtest_catalog_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "phase6a.db"
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    script_location = Path(__file__).resolve().parents[2] / "alembic"

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(script_location))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("strategy_runs")}

    assert {
        "strategy_id",
        "strategy_kind",
        "strategy_version",
        "dataset",
        "profile_id",
        "artifact_path",
        "config_fingerprint",
        "tags_json",
        "notes",
    }.issubset(columns)
