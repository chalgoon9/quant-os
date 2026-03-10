from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from quant_os.api.deps import resolve_config_path
from quant_os.api.errors import install_error_handlers
from quant_os.api.routes.backtests import router as backtests_router
from quant_os.api.routes.ops import router as ops_router
from quant_os.api.routes.reports import router as reports_router
from quant_os.api.routes.research import router as research_router
from quant_os.api.routes.strategies import router as strategies_router
from quant_os.api.routes.system import router as system_router


def _resolve_frontend_dist(frontend_dist: Path | str | None) -> Path:
    if frontend_dist is not None:
        return Path(frontend_dist).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app(
    *,
    config: Path | str | None = None,
    frontend_dist: Path | str | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Quant OS API",
        version="0.1.0",
    )
    app.state.config_path = str(resolve_config_path(config))
    app.state.frontend_dist = str(_resolve_frontend_dist(frontend_dist))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(system_router, prefix="/api")
    app.include_router(ops_router, prefix="/api")
    app.include_router(research_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(backtests_router, prefix="/api")
    app.include_router(strategies_router, prefix="/api")

    frontend_root = Path(app.state.frontend_dist)
    assets_dir = frontend_root / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"error": "not found", "code": "not_found"})
        candidate = frontend_root / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        index_path = frontend_root / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return JSONResponse(
            status_code=404,
            content={
                "error": "frontend build not found",
                "code": "frontend_not_built",
            },
        )

    return app


app = create_app()
