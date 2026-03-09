from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.helpers import build_seeded_runtime, seed_active_kill_switch, seed_ops_snapshot


def test_system_and_ops_summary_routes_return_runtime_and_ops_state(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, runtime = build_seeded_runtime(tmp_path)
    seed_ops_snapshot(runtime)
    seed_active_kill_switch(runtime)
    client = TestClient(create_app(config=config_path))

    runtime_response = client.get("/api/system/runtime")
    doctor_response = client.get("/api/system/doctor")
    summary_response = client.get("/api/ops/summary")
    kill_switch_response = client.get("/api/ops/kill-switch/active")
    reconciliation_response = client.get("/api/ops/reconciliation/latest")

    assert runtime_response.status_code == 200
    assert runtime_response.json()["mode"] == "paper"
    assert runtime_response.json()["execution_adapter"] == "PaperAdapter"

    assert doctor_response.status_code == 200
    assert doctor_response.json()["system_name"] == "quant-os-mvp"

    assert summary_response.status_code == 200
    assert summary_response.json()["nav"] == "100145.0000"
    assert summary_response.json()["active_kill_switch_reasons"] == ["reconciliation_failure"]

    assert kill_switch_response.status_code == 200
    assert kill_switch_response.json()["items"][0]["reason"] == "reconciliation_failure"

    assert reconciliation_response.status_code == 200
    assert reconciliation_response.json()["status"] == "matched"


def test_ops_summary_returns_explicit_error_when_snapshot_missing(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, _runtime = build_seeded_runtime(tmp_path)
    client = TestClient(create_app(config=config_path))

    response = client.get("/api/ops/summary")

    assert response.status_code == 404
    assert response.json()["code"] == "ops_summary_unavailable"
