"""Socket.IO server instance for real-time events."""

import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, socketio_path="/ws")


@sio.event
async def connect(sid: str, environ: dict) -> None:
    """Handle client connection."""
    pass


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    pass
