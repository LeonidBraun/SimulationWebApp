from app_pkg import create_app

# Create the FastAPI app
app = create_app()


# Also need to add the index route here since it's not in a router
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

from app_pkg.auth import get_current_user


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user_id: str = Depends(get_current_user)):
    return templates.TemplateResponse(
        "index.html", {"request": request, "user_id": user_id}
    )
