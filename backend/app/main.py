from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyses, job_descriptions, resumes
from app.core.config import get_settings
from app.db.session import init_db
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{settings.api_prefix}/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            llm_provider=settings.llm_provider,
            storage_backend=settings.storage_backend,
            disclaimer=settings.disclaimer,
        )

    app.include_router(resumes.router, prefix=settings.api_prefix)
    app.include_router(job_descriptions.router, prefix=settings.api_prefix)
    app.include_router(analyses.router, prefix=settings.api_prefix)
    return app


app = create_app()
