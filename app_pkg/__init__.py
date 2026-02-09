import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import HTTPException, status
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .auth import auth_router, get_current_user
from .ws import ws_router, manager
from .services import create_data, watch_file

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown events"""
    # Startup: start background tasks
    print("Starting background tasks...")
    bg_tasks = []
    bg_tasks.append(asyncio.create_task(create_data(manager)))
    bg_tasks.append(asyncio.create_task(watch_file(manager)))
    app.state._bg_tasks = bg_tasks

    yield

    # Shutdown: cancel background tasks
    print("Shutting down background tasks...")
    for task in app.state._bg_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # session secret should come from env in real app
    app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-this")

    # Mount static files
    static_dir = BASE_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # exception handler for 401
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return RedirectResponse(url="/login")
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    # include routers
    app.include_router(auth_router)
    app.include_router(ws_router)

    return app
