"""Application entry point with scheduler support."""


import uvicorn

from src.core.config import settings
from src.core.logging import logger


def main() -> None:
    """Start the application with API server and optional scheduler."""
    logger.info(
        "Starting Crew Media Ops (env=%s, port=%d)",
        settings.APP_ENV,
        settings.API_PORT,
    )

    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
