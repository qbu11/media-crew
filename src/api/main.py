"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import (
    accounts,
    analytics,
    clients,
    content,
    dashboard,
    health,
    images,
    research,
    search,
    tasks,
)
from src.core.config import settings
from src.services.scheduler import HotspotScheduler

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

    scheduler = HotspotScheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Scheduler initialized")

    yield

    logger.info("Crew Media Ops shutting down")
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        logger.info("Scheduler stopped")


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
app.include_router(content.router)
app.include_router(tasks.router)
app.include_router(analytics.router)
app.include_router(dashboard.router)
app.include_router(research.router)
app.include_router(search.router)
app.include_router(clients.router)
app.include_router(accounts.router)
app.include_router(images.router)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
