from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# demo user store (replace with DB & hashed passwords)
USERS = {"Litsa": "lomlleo", "Leo": "imthebest"}

auth_router = APIRouter()


def get_current_user(request: Request) -> str:
    """Dependency to get current user from session"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in"
        )
    return user_id


@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@auth_router.post("/login")
async def login(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")

    if username in USERS and USERS[username] == password:
        request.session["user_id"] = username
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid credentials"}
    )


@auth_router.get("/logout")
async def logout(request: Request):
    # Disconnect all WebSockets for this user
    user_id = request.session.get("user_id")
    if user_id:
        # Import here to avoid circular imports
        from .ws import manager

        await manager.disconnect_user(user_id)

    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
