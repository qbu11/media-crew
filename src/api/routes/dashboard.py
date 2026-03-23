"""Dashboard HTML."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Dashboard"])

# Get the static directory path
STATIC_DIR = Path(__file__).parent.parent / "static"
templates = Jinja2Templates(directory=str(STATIC_DIR))


@router.get("/", response_class=HTMLResponse)
async def dashboard(_request: Request) -> str:
    """Serve the dashboard page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crew Media Ops - Dashboard</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Dashboard not found</h1>
        <p>Please ensure static/index.html exists.</p>
    </body>
    </html>
    """
