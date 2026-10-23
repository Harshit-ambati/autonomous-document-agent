"""Run with: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000."""

import asyncio
import logging
import ssl
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.agent import Agent
from app.config import Settings
from app.guardrails import check_request
from app.llm import AgentError, GeminiModel, LanguageModel
from app.models import AgentRequest, AgentResponse

logger = logging.getLogger("document_agent")
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(settings: Settings | None = None, model: LanguageModel | None = None) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        config.output_dir.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(verify=ssl.create_default_context()) as client:
            application.state.model = model or GeminiModel(client, config)
            application.state.busy = asyncio.Lock()
            yield

    application = FastAPI(
        title="Autonomous Document Agent",
        version="1.0.0",
        description="Plan, execute, check, and generate a business Word document. Inspect the plan and tool trace in the response.",
        lifespan=lifespan,
    )
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/", include_in_schema=False)
    async def home():
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/health")
    async def health():
        return {"status": "ok", "model_configured": bool(config.api_key or model), "model": config.model}

    @application.post(
        "/agent",
        response_model=AgentResponse,
        responses={
            422: {"description": "Invalid input or failed quality check"},
            502: {"description": "Invalid model response"},
            503: {"description": "Model not configured, busy, or unavailable"},
            504: {"description": "Run deadline exceeded"},
        },
    )
    async def agent(body: AgentRequest):
        try:
            check_request(body.request)
        except AgentError as error:
            return JSONResponse(
                status_code=error.status_code,
                content={"error": {"code": error.code, "message": error.message}},
            )
        if application.state.busy.locked():
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "agent_busy",
                        "message": "Another document is being generated. Please retry shortly.",
                    }
                },
                headers={"Retry-After": "5"},
            )
        run_id = str(uuid4())
        engine = Agent(application.state.model, config.output_dir, config.model, config.api_key)
        async with application.state.busy:
            try:
                async with asyncio.timeout(config.agent_timeout):
                    return await engine.run(body.request, run_id)
            except TimeoutError:
                error = AgentError("run_timeout", "Agent exceeded its run deadline. Please try a smaller request.", 504)
            except AgentError as exc:
                error = exc
            except Exception as exc:
                # Log exception class only: upstream payloads may contain sensitive text.
                logger.error("Run %s failed (%s)", run_id, type(exc).__name__)
                error = AgentError("internal_error", "Document generation failed. See server logs for the run ID.", 500)
        return JSONResponse(
            status_code=error.status_code,
            content={
                "run_id": run_id,
                "error": {"code": error.code, "message": error.message, "details": error.details},
                "trace": [event.model_dump() for event in engine.trace],
            },
        )

    @application.get("/documents/{run_id}")
    async def document(run_id: UUID):
        path = config.output_dir / f"{run_id}.docx"
        if not path.is_file():
            return JSONResponse(status_code=404, content={"error": "Document not found"})
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"document-{run_id}.docx",
        )

    @application.get("/runs/{run_id}")
    async def run_trace(run_id: UUID):
        path = config.output_dir / f"{run_id}.json"
        if not path.is_file():
            return JSONResponse(status_code=404, content={"error": "Run not found"})
        return FileResponse(path, media_type="application/json")

    return application


app = create_app()
