import asyncio
import logging
import os
import platform
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from neurostreamlab import __version__
from neurostreamlab.datasets.adapter import DATASETS
from neurostreamlab.decoders.registry import REGISTRY
from neurostreamlab.server.runtime import SessionRuntime
from neurostreamlab.server.schemas import ControlRequest, HealthResponse, PerturbationRequest


def create_app(mode: str | None = None) -> FastAPI:
    runtime = SessionRuntime()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=logging.INFO)
        runtime.configure(mode or os.environ.get("NEUROSTREAMLAB_MODE", "synthetic"))
        task = asyncio.create_task(runtime.run())
        yield
        runtime.running = False
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        runtime.close()

    app = FastAPI(title="NeuroStreamLab", version=__version__, lifespan=lifespan)
    app.state.runtime = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health():
        return HealthResponse(status="ok", version=__version__)

    @app.get("/api/system")
    def system() -> dict:
        return {
            "version": __version__,
            "python": platform.python_version(),
            "os": platform.system(),
            "architecture": platform.machine(),
            "privacy": "local-only",
        }

    @app.get("/api/sources")
    def sources() -> list[dict]:
        return [
            {"id": "synthetic", "label": "SYNTHETIC"},
            {
                "id": "replay",
                "label": "RECORDED EEG REPLAY",
                "available": runtime.state()["replay_available"],
            },
            {
                "id": "hardware",
                "label": "LIVE HARDWARE",
                "available": False,
                "reason": "Explicit board configuration and hardware permission required through Python adapter",
            },
        ]

    @app.get("/api/decoders")
    def decoders() -> dict:
        return REGISTRY

    @app.get("/api/datasets")
    def datasets() -> dict:
        return DATASETS

    @app.get("/api/session")
    @app.get("/api/configuration")
    @app.get("/api/experiment")
    def session() -> dict:
        return runtime.state()

    @app.get("/api/model")
    def model() -> dict:
        return {
            "loaded": runtime.model is not None,
            "metadata": runtime.model.metadata if runtime.model else None,
        }

    @app.post("/api/control")
    async def control(request: ControlRequest) -> dict:
        try:
            async with runtime.lock:
                return await asyncio.to_thread(runtime.control, request.action, request.value)
        except (ValueError, FileNotFoundError, RuntimeError) as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/perturbations")
    def perturbations() -> list[dict]:
        return [c.model_dump() for c in runtime.configs]

    @app.post("/api/perturbations")
    async def update_perturbations(request: PerturbationRequest) -> dict:
        try:
            async with runtime.lock:
                runtime.set_perturbations(request.configurations)
            return {"configurations": [c.model_dump() for c in runtime.configs]}
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.websocket("/ws")
    async def websocket(websocket: WebSocket):
        if websocket.headers.get("origin") not in (
            None,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://testserver",
        ):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue(maxsize=4)
        runtime.clients.add(queue)
        try:
            await websocket.send_json(
                {
                    "schema_version": 1,
                    "type": "source_status",
                    "session_id": runtime.session_id,
                    "payload": runtime.state(),
                }
            )
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=2)
                except TimeoutError:
                    message = {
                        "schema_version": 1,
                        "type": "source_status",
                        "session_id": runtime.session_id,
                        "payload": runtime.state(),
                    }
                await websocket.send_json(message)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            runtime.clients.discard(queue)

    return app


app = create_app()
