from __future__ import annotations

import asyncio
import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

from aiohttp import web

from . import __version__
from .exporters import EXPORTERS
from .fetcher import TermInfoFetcher
from .logger import get_logger, log_exceptions
from .models import MedicalTerm
from .ner import MODEL_NAME, MedicalNERAnalyzer
from .paths import data_dir, export_dir
from .protocols import Analyzer, DescriptionFetcher

WEBUI_DIR = Path(__file__).resolve().parent / "webui"

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8080

MAX_TEXT_LENGTH = 20_000

# Typed keys for application state (aiohttp 3.9+).
SERVICE_KEY: "web.AppKey[AnalysisService]" = web.AppKey("service")
PRELOAD_KEY: "web.AppKey[asyncio.Task]" = web.AppKey("preload_task")


def _term_to_json(term: MedicalTerm) -> dict:
    return {
        "text": term.text,
        "category": term.category,
        "score": round(term.score, 4),
        "start": term.start,
        "end": term.end,
        "description": term.description,
        "source_url": term.source_url,
    }


def _term_from_json(payload: dict) -> MedicalTerm:
    return MedicalTerm(
        text=str(payload.get("text", "")),
        category=str(payload.get("category", "")),
        score=float(payload.get("score", 0.0) or 0.0),
        start=int(payload.get("start", -1) or -1),
        end=int(payload.get("end", -1) or -1),
        description=str(payload.get("description", "") or ""),
        source_url=str(payload.get("source_url", "") or ""),
    )


class AnalysisService:
    """Runs the analysis pipeline for HTTP requests.

    The analyzer is a blocking, single-threaded model, so calls run in a worker
    thread and are serialised with a lock - a Raspberry Pi cannot usefully run
    two inferences at once.
    """

    def __init__(
        self,
        analyzer: Analyzer | None = None,
        fetcher: DescriptionFetcher | None = None,
    ) -> None:
        self.analyzer: Analyzer = analyzer or MedicalNERAnalyzer()
        self.fetcher: DescriptionFetcher = fetcher or TermInfoFetcher()
        self._lock = asyncio.Lock()
        self._log = get_logger()

    @property
    def model_loaded(self) -> bool:
        return bool(getattr(self.analyzer, "is_loaded", False))

    @log_exceptions
    async def analyze(self, text: str) -> list[MedicalTerm]:
        async with self._lock:
            terms = await asyncio.to_thread(self.analyzer.analyze, text)
        if terms:
            terms = await self.fetcher.fetch_all(terms)
        return terms

    @log_exceptions(reraise=False)
    async def preload(self) -> None:
        """Load the model before the first request (optional warm-up)."""
        load = getattr(self.analyzer, "load", None)
        if load is None:
            return
        self._log.info("Preloading model before first request...")
        await asyncio.to_thread(load)


@web.middleware
async def error_middleware(request: web.Request, handler):
    """Turn unhandled exceptions into JSON errors instead of HTML tracebacks.

    The exception itself is already written to the log by @log_exceptions.
    """
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as exc:
        return web.json_response(
            {"error": f"{type(exc).__name__}: {exc}"}, status=500
        )


@log_exceptions
async def handle_index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBUI_DIR / "index.html")


@log_exceptions
async def handle_health(request: web.Request) -> web.Response:
    service = request.app[SERVICE_KEY]
    return web.json_response(
        {"status": "ok", "model_loaded": service.model_loaded}
    )


@log_exceptions
async def handle_info(request: web.Request) -> web.Response:
    service = request.app[SERVICE_KEY]
    return web.json_response(
        {
            "version": __version__,
            "model": MODEL_NAME,
            "model_loaded": service.model_loaded,
            "python": platform.python_version(),
            "system": f"{platform.system()} {platform.release()}",
            "machine": platform.machine(),
            "hostname": platform.node(),
            "data_dir": str(data_dir()),
            "export_dir": str(export_dir()),
        }
    )


@log_exceptions
async def handle_analyze(request: web.Request) -> web.Response:
    payload = await _read_json(request)
    text = str(payload.get("text", "") or "").strip()

    if not text:
        raise web.HTTPBadRequest(
            text='{"error": "Field \'text\' is required."}',
            content_type="application/json",
        )
    if len(text) > MAX_TEXT_LENGTH:
        raise web.HTTPRequestEntityTooLarge(
            max_size=MAX_TEXT_LENGTH,
            actual_size=len(text),
        )

    service = request.app[SERVICE_KEY]
    started = datetime.now()
    terms = await service.analyze(text)
    elapsed = (datetime.now() - started).total_seconds()

    return web.json_response(
        {
            "count": len(terms),
            "elapsed_seconds": round(elapsed, 3),
            "terms": [_term_to_json(t) for t in terms],
        }
    )


@log_exceptions
async def handle_export(request: web.Request) -> web.FileResponse:
    fmt = request.match_info["fmt"].upper()
    exporter = EXPORTERS.get(fmt)
    if exporter is None:
        raise web.HTTPNotFound(
            text='{"error": "Unknown export format."}',
            content_type="application/json",
        )

    payload = await _read_json(request)
    raw_terms = payload.get("terms") or []
    if not isinstance(raw_terms, list) or not raw_terms:
        raise web.HTTPBadRequest(
            text='{"error": "Nothing to export."}',
            content_type="application/json",
        )

    terms = [_term_from_json(item) for item in raw_terms]
    filename = (
        f"medical_terms_{datetime.now():%Y%m%d_%H%M%S}{exporter.extension}"
    )
    target = export_dir() / filename

    try:
        saved = await asyncio.to_thread(exporter.export, terms, target)
    except ImportError as exc:
        # PDF export needs reportlab; report it instead of a 500.
        raise web.HTTPServiceUnavailable(
            text=json.dumps({"error": str(exc)}),
            content_type="application/json",
        )

    return web.FileResponse(
        saved,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Path": str(saved),
        },
    )


async def _read_json(request: web.Request) -> dict:
    try:
        payload = await request.json()
    except Exception:
        raise web.HTTPBadRequest(
            text='{"error": "Invalid JSON body."}',
            content_type="application/json",
        )
    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(
            text='{"error": "JSON object expected."}',
            content_type="application/json",
        )
    return payload


async def _on_startup(app: web.Application) -> None:
    log = get_logger()
    log.info(
        "Web service started (version %s, %s %s).",
        __version__,
        platform.system(),
        platform.machine(),
    )
    if os.environ.get("MEDLEX_PRELOAD", "").lower() in {"1", "true", "yes"}:
        app[PRELOAD_KEY] = asyncio.create_task(app[SERVICE_KEY].preload())


async def _on_cleanup(app: web.Application) -> None:
    task = app.get(PRELOAD_KEY)
    if task is not None and not task.done():
        task.cancel()


def create_app(
    analyzer: Analyzer | None = None,
    fetcher: DescriptionFetcher | None = None,
) -> web.Application:
    """Build the aiohttp application.

    Both collaborators can be injected, which is what the tests use to run the
    HTTP layer without loading the neural network or touching the network.
    """
    app = web.Application(middlewares=[error_middleware])
    app[SERVICE_KEY] = AnalysisService(analyzer=analyzer, fetcher=fetcher)

    app.router.add_get("/", handle_index)
    app.router.add_get("/healthz", handle_health)
    app.router.add_get("/api/info", handle_info)
    app.router.add_post("/api/analyze", handle_analyze)
    app.router.add_post("/api/export/{fmt}", handle_export)
    app.router.add_static("/static/", WEBUI_DIR / "static", name="static")

    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    return app


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Start the web service (blocking)."""
    print(
        f"Medical Lexicon web service on http://{host}:{port}",
        file=sys.stderr,
        flush=True,
    )
    web.run_app(create_app(), host=host, port=port, print=None)
