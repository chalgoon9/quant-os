from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.helpers import (
    build_seeded_runtime,
    seed_active_kill_switch,
    seed_ops_snapshot,
    seed_order,
    seed_reconciliation_mismatch,
)


def test_order_and_report_routes_return_persisted_ops_views(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, runtime = build_seeded_runtime(tmp_path)
    seed_ops_snapshot(runtime)
    seed_reconciliation_mismatch(runtime)
    seed_active_kill_switch(runtime)
    order_id = seed_order(runtime)
    client = TestClient(create_app(config=config_path))

    orders_response = client.get("/api/ops/orders")
    order_detail_response = client.get(f"/api/ops/orders/{order_id}")
    report_response = client.get("/api/reports/daily/latest")

    assert orders_response.status_code == 200
    assert orders_response.json()["items"][0]["order_id"] == order_id

    assert order_detail_response.status_code == 200
    assert order_detail_response.json()["projection"]["status"] == "partially_filled"
    assert len(order_detail_response.json()["events"]) == 1
    assert len(order_detail_response.json()["fills"]) == 1

    assert report_response.status_code == 200
    assert report_response.json()["reconciliation_status"] == "mismatch"
    assert "Daily Report" in report_response.json()["body_markdown"]


def test_order_detail_returns_explicit_error_for_missing_order(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, runtime = build_seeded_runtime(tmp_path)
    seed_ops_snapshot(runtime)
    client = TestClient(create_app(config=config_path))

    response = client.get("/api/ops/orders/order_missing")

    assert response.status_code == 404
    assert response.json()["code"] == "order_not_found"
