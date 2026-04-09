"""
FastAPI application entry point for the ClinicalBench OpenEnv server.

Start with:
    uvicorn server.app:app --host 0.0.0.0 --port 8080
"""

import os
from pathlib import Path

from openenv.core.env_server.http_server import create_app
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import ClinicalAction, ClinicalObservation
from .environment import ClinicalBenchEnvironment, DATA_PATH
from .ai_routes import router as ai_router


def _make_env() -> ClinicalBenchEnvironment:
    """Factory called by HTTPEnvServer for each new session."""
    return ClinicalBenchEnvironment(data_path=DATA_PATH)


app = create_app(
    env=_make_env,
    action_cls=ClinicalAction,
    observation_cls=ClinicalObservation,
    env_name="clinical_bench",
    max_concurrent_envs=4,
)

app.include_router(ai_router)

_FRONTEND_DIST = Path("/app/frontend/dist")
if not _FRONTEND_DIST.exists():
    _FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

if (_FRONTEND_DIST / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="frontend-assets",
    )


@app.get("/")
def _root():
    """Serve the frontend in Docker; return service metadata in local dev without a build."""
    index_path = _FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return {
        "service": "clinical_bench",
        "health": "/health",
        "openapi": "/docs",
        "frontend": "run `npm run build` in frontend/ to generate dist",
    }


def main() -> None:
    """Entry point for `uv run server` / `clinical-bench-server` (openenv validate)."""
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=port,
        workers=1,
        timeout_keep_alive=75,
    )


if __name__ == "__main__":
    main()
