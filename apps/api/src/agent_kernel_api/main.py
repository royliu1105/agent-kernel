"""Agent Kernel API entrypoint."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Agent Kernel API", version="0.1.0")

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "agent-kernel-api"}

    return app


app = create_app()


def main() -> None:
    uvicorn.run("agent_kernel_api.main:app", host="0.0.0.0", port=8000, reload=False)
