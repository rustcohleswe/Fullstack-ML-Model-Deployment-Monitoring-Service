"""FastAPI application: model registry, simulated prediction serving, metrics."""
import logging
import time
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.repository import DuplicateModelError, InMemoryRepository, Repository, RepositoryError, SupabaseRepository
from app.schemas import MetricsOut, ModelCreate, ModelOut, PredictionLogOut, PredictRequest, PredictResponse
from app.service import ModelNotFound, ModelService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("mlmonitor.api")


def build_repository(settings: Settings) -> Repository:
    if settings.has_supabase:
        from supabase import create_client  # imported lazily so tests need no network

        log.info("using Supabase storage")
        return SupabaseRepository(create_client(settings.supabase_url, settings.supabase_key))
    log.warning("SUPABASE_URL/SUPABASE_KEY not set: using volatile in-memory storage (demo only)")
    return InMemoryRepository()


def create_app(settings: Optional[Settings] = None, repo: Optional[Repository] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    service = ModelService(repo or build_repository(settings))
    app = FastAPI(title="ML Model Monitor", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["*"], allow_headers=["*"])

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("unhandled error %s %s", request.method, request.url.path)
            return JSONResponse({"detail": "internal server error"}, status_code=500)
        log.info("%s %s -> %d (%.1f ms)", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - start) * 1000)
        return response

    @app.exception_handler(ModelNotFound)
    async def _not_found(_: Request, exc: ModelNotFound):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(DuplicateModelError)
    async def _duplicate(_: Request, exc: DuplicateModelError):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(RepositoryError)
    async def _storage(_: Request, exc: RepositoryError):
        return JSONResponse({"detail": "storage backend unavailable"}, status_code=503)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/models", response_model=ModelOut, status_code=201)
    def register_model(payload: ModelCreate):
        return service.register(payload)

    @app.get("/models", response_model=List[ModelOut])
    def list_models(name: Optional[str] = Query(None, max_length=100), version: Optional[str] = Query(None, max_length=50)):
        return service.list_models(name, version)

    @app.get("/models/{model_id}", response_model=ModelOut)
    def get_model(model_id: UUID):
        return service.get_model(model_id)

    @app.post("/models/{model_id}/predict", response_model=PredictResponse)
    def predict(model_id: UUID, payload: PredictRequest):
        return service.predict(model_id, payload)

    @app.get("/models/{model_id}/predictions", response_model=List[PredictionLogOut])
    def recent_predictions(model_id: UUID, limit: int = Query(20, ge=1, le=200)):
        return service.list_predictions(model_id, limit)

    @app.get("/models/{model_id}/metrics", response_model=MetricsOut)
    def model_metrics(model_id: UUID):
        return service.metrics_for(model_id)

    @app.get("/metrics", response_model=List[MetricsOut])
    def all_metrics():
        return service.all_metrics()

    return app
