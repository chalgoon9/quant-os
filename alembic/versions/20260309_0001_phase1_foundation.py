"""phase1 foundation

Revision ID: 20260309_0001
Revises:
Create Date: 2026-03-09 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260309_0001"
down_revision = None
branch_labels = None
depends_on = None


AMOUNT_TYPE = sa.Numeric(24, 8)
PRICE_TYPE = sa.Numeric(24, 8)
WEIGHT_TYPE = sa.Numeric(12, 6)


def upgrade() -> None:
    op.create_table(
        "strategy_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("config_payload", sa.JSON()),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_run_id", sa.String(length=64), sa.ForeignKey("strategy_runs.id"), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("time_in_force", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quantity", AMOUNT_TYPE, nullable=False),
        sa.Column("filled_quantity", AMOUNT_TYPE, nullable=False, server_default="0"),
        sa.Column("limit_price", PRICE_TYPE),
        sa.Column("broker_order_id", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True)),
        sa.Column("projection_source_event_id", sa.String(length=64)),
        sa.UniqueConstraint("intent_id"),
        sa.UniqueConstraint("broker_order_id"),
    )
    op.create_index("ix_orders_status_updated_at", "orders", ["status", "updated_at"])

    op.create_table(
        "order_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_run_id", sa.String(length=64), sa.ForeignKey("strategy_runs.id"), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("broker_order_id", sa.String(length=128)),
        sa.Column("reason", sa.Text()),
        sa.Column("raw_payload", sa.JSON()),
        sa.Column("metadata_json", sa.JSON()),
    )
    op.create_index("ix_order_events_order_id_occurred_at", "order_events", ["order_id", "occurred_at"])
    op.create_index("ix_order_events_broker_order_id", "order_events", ["broker_order_id"])

    op.create_table(
        "fills",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("order_id", sa.String(length=64), nullable=False),
        sa.Column("intent_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_run_id", sa.String(length=64), sa.ForeignKey("strategy_runs.id"), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("quantity", AMOUNT_TYPE, nullable=False),
        sa.Column("price", PRICE_TYPE, nullable=False),
        sa.Column("gross_amount", AMOUNT_TYPE, nullable=False),
        sa.Column("fee", AMOUNT_TYPE, nullable=False, server_default="0"),
        sa.Column("tax", AMOUNT_TYPE, nullable=False, server_default="0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("broker_fill_id", sa.String(length=128)),
        sa.Column("raw_payload", sa.JSON()),
        sa.UniqueConstraint("broker_fill_id"),
    )
    op.create_index("ix_fills_order_id_occurred_at", "fills", ["order_id", "occurred_at"])

    op.create_table(
        "positions_snapshot",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("quantity", AMOUNT_TYPE, nullable=False),
        sa.Column("average_cost", PRICE_TYPE, nullable=False),
        sa.Column("market_price", PRICE_TYPE),
        sa.Column("market_value", AMOUNT_TYPE),
        sa.Column("unrealized_pnl", AMOUNT_TYPE),
        sa.Column("source", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_positions_snapshot_symbol_snapshot_at", "positions_snapshot", ["symbol", "snapshot_at"])

    op.create_table(
        "cash_ledger",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount", AMOUNT_TYPE, nullable=False),
        sa.Column("balance_after", AMOUNT_TYPE),
        sa.Column("reference_type", sa.String(length=32)),
        sa.Column("reference_id", sa.String(length=64)),
        sa.Column("notes", sa.Text()),
    )
    op.create_index("ix_cash_ledger_occurred_at", "cash_ledger", ["occurred_at"])

    op.create_table(
        "pnl_snapshot",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realized_pnl", AMOUNT_TYPE, nullable=False, server_default="0"),
        sa.Column("unrealized_pnl", AMOUNT_TYPE, nullable=False, server_default="0"),
        sa.Column("total_pnl", AMOUNT_TYPE, nullable=False, server_default="0"),
        sa.Column("nav", AMOUNT_TYPE, nullable=False),
        sa.Column("gross_exposure", WEIGHT_TYPE, nullable=False),
        sa.Column("net_exposure", WEIGHT_TYPE, nullable=False),
    )
    op.create_index("ix_pnl_snapshot_snapshot_at", "pnl_snapshot", ["snapshot_at"])

    op.create_table(
        "reconciliation_log",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mismatch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requires_manual_intervention", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON()),
    )
    op.create_index("ix_reconciliation_log_occurred_at", "reconciliation_log", ["occurred_at"])

    op.create_table(
        "kill_switch_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("trigger_value", WEIGHT_TYPE),
        sa.Column("threshold_value", WEIGHT_TYPE),
        sa.Column("details", sa.JSON()),
        sa.Column("cleared_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_kill_switch_events_triggered_at", "kill_switch_events", ["triggered_at"])


def downgrade() -> None:
    op.drop_index("ix_kill_switch_events_triggered_at", table_name="kill_switch_events")
    op.drop_table("kill_switch_events")

    op.drop_index("ix_reconciliation_log_occurred_at", table_name="reconciliation_log")
    op.drop_table("reconciliation_log")

    op.drop_index("ix_pnl_snapshot_snapshot_at", table_name="pnl_snapshot")
    op.drop_table("pnl_snapshot")

    op.drop_index("ix_cash_ledger_occurred_at", table_name="cash_ledger")
    op.drop_table("cash_ledger")

    op.drop_index("ix_positions_snapshot_symbol_snapshot_at", table_name="positions_snapshot")
    op.drop_table("positions_snapshot")

    op.drop_index("ix_fills_order_id_occurred_at", table_name="fills")
    op.drop_table("fills")

    op.drop_index("ix_order_events_broker_order_id", table_name="order_events")
    op.drop_index("ix_order_events_order_id_occurred_at", table_name="order_events")
    op.drop_table("order_events")

    op.drop_index("ix_orders_status_updated_at", table_name="orders")
    op.drop_table("orders")

    op.drop_table("strategy_runs")
