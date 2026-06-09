"""
Analytics API — main FastAPI application.

Exposes analytics endpoints, health check, and ingestion trigger.
Runs on port 8000.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks

from app.routers import analytics
from app.database import engine
from app.cache import check_redis_health
from app.schemas import HealthResponse, IngestResponse
from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    print("Analytics API starting up...")
    yield
    print("Analytics API shutting down...")
    await engine.dispose()


app = FastAPI(
    title="Analytics API",
    description="Backend analytics service with pre-aggregated materialized views and Redis caching.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(analytics.router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint — verifies PostgreSQL and Redis connectivity."""
    # Check PostgreSQL
    postgres_ok = False
    try:
        from app.database import async_session
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            postgres_ok = True
    except Exception:
        pass

    # Check Redis
    redis_ok = await check_redis_health()

    return {
        "status": "ok" if (postgres_ok and redis_ok) else "degraded",
        "postgres": postgres_ok,
        "redis": redis_ok,
    }


@app.post("/ingest", response_model=IngestResponse)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Trigger data ingestion as a background task."""
    background_tasks.add_task(_run_ingestion)
    return {"status": "ingestion started"}


async def _run_ingestion():
    """Run ingestion in the background."""
    from ingestion.ingest import run_ingestion
    await run_ingestion()
