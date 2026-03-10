"""phase6a backtest catalog metadata

Revision ID: 20260310_0002
Revises: 20260309_0001
Create Date: 2026-03-10 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260310_0002"
down_revision = "20260309_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("strategy_runs") as batch:
        batch.add_column(sa.Column("strategy_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("strategy_kind", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("strategy_version", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("dataset", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("profile_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("artifact_path", sa.String(length=512), nullable=True))
        batch.add_column(sa.Column("config_fingerprint", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("tags_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("strategy_runs") as batch:
        batch.drop_column("notes")
        batch.drop_column("tags_json")
        batch.drop_column("config_fingerprint")
        batch.drop_column("artifact_path")
        batch.drop_column("profile_id")
        batch.drop_column("dataset")
        batch.drop_column("strategy_version")
        batch.drop_column("strategy_kind")
        batch.drop_column("strategy_id")
