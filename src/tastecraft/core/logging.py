"""Structured logging setup for TasteCraft."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    verbose: bool = False,
) -> None:
    """Configure logging for the application."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    if verbose:
        log_level = logging.DEBUG

    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=log_level,
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
        force=True,
    )

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
