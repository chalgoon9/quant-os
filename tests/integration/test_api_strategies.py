from __future__ import annotations

from fastapi.testclient import TestClient


def test_strategies_route_lists_catalog_specs(tmp_path) -> None:
    from quant_os.api.main import create_app
    from tests.integration.helpers import build_seeded_runtime

    config_path, _runtime = build_seeded_runtime(tmp_path)
    client = TestClient(create_app(config=config_path))

    response = client.get("/api/strategies")

    assert response.status_code == 200
    payload = response.json()
    ids = {item["strategy_id"] for item in payload["items"]}
    assert "kr_etf_momo_20_60_v1" in ids
    assert "kr_etf_momo_30_90_v1" in ids
