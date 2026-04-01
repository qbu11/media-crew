"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.ws import socket_app

from src.api.routes import (
    accounts,
    agents,
    analytics,
    clients,
    content,
    crew_execution,
    dashboard,
    health,
    images,
    onboarding,
    research,
    review,
    schedule,
    search,
    tasks,
)
from src.core.config import settings
from src.services.scheduler import HotspotScheduler
from src.api.dependencies import engine
import src.models  # noqa: F401 — ensure all models are registered with Base

logger = logging.getLogger(__name__)

static_dir = Path(__file__).parent.parent / "api" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    logging.basicConfig(level=logging.INFO)
    logger.info(
        "Crew Media Ops starting on http://%s:%s",
        settings.API_HOST,
        settings.API_PORT,
    )

    # Initialize database tables (non-blocking)
    try:
        from src.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")
    except Exception as e:
        logger.warning("Database initialization failed (non-blocking): %s", e)

    # Try to start scheduler, but don't block if it fails
    try:
        scheduler = HotspotScheduler()
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Scheduler initialized")
    except Exception as e:
        logger.warning("Scheduler initialization failed (non-blocking): %s", e)
        app.state.scheduler = None

    yield

    logger.info("Crew Media Ops shutting down")
    if hasattr(app.state, "scheduler") and app.state.scheduler:
        try:
            app.state.scheduler.shutdown()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.warning("Scheduler shutdown failed: %s", e)


app = FastAPI(
    title="Crew Media Ops API",
    description="Multi-agent system for social media operations",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Tailscale access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(agents.router)  # already has /api/v1 prefix
app.include_router(content.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(dashboard.router)
app.include_router(research.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(images.router, prefix="/api/v1")
app.include_router(crew_execution.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")
app.include_router(schedule.router, prefix="/api")

# Mount static files (only if directory exists)
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    logger.info("Static files mounted at /static")
else:
    logger.warning("Static directory not found: %s", static_dir)

# Mount Socket.IO at /ws
app.mount("/ws", socket_app)
