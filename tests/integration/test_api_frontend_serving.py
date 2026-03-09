from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.helpers import build_seeded_runtime, seed_ops_snapshot


def test_frontend_dist_is_served_from_root_and_spa_routes(tmp_path) -> None:
    from quant_os.api.main import create_app

    config_path, runtime = build_seeded_runtime(tmp_path)
    seed_ops_snapshot(runtime)

    dist_dir = tmp_path / "frontend_dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>quant frontend</div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('ok');", encoding="utf-8")

    client = TestClient(create_app(config=config_path, frontend_dist=dist_dir))

    root = client.get("/")
    root_head = client.head("/")
    route = client.get("/orders")
    asset = client.get("/assets/app.js")
    api = client.get("/api/ops/summary")

    assert root.status_code == 200
    assert "quant frontend" in root.text
    assert root_head.status_code == 200

    assert route.status_code == 200
    assert "quant frontend" in route.text

    assert asset.status_code == 200
    assert "console.log('ok')" in asset.text

    assert api.status_code == 200
    assert api.json()["nav"] == "100145.0000"
