import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))

from tagger.tmdb.media import (
    TMDBAuthError,
    TMDBConnectionError,
    TMDBError,
    TMDBResponseError,
    TMDBTimeoutError,
    GET_MOVIE_EMBED,
    GET_SHOW_EMBED,
    get_episodes,
    get_seasons,
    search_multi,
)

PASSWORD_ENV = "WATCH_WEB_PASSWORD"
SECRET_ENV = "WATCH_WEB_SESSION_SECRET"

password = os.getenv(PASSWORD_ENV)
if not password:
    raise RuntimeError(f"Missing {PASSWORD_ENV} env var for login gating.")

session_secret = os.getenv(SECRET_ENV)
if not session_secret:
    raise RuntimeError(f"Missing {SECRET_ENV} env var for session cookies.")

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="watch_session",
    same_site="lax",
    https_only=False,
)

TEMPLATES_DIR = ROOT / "web" / "templates"
STATIC_DIR = ROOT / "web" / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _authed(request: Request) -> bool:
    return request.session.get("authed") is True


def _require_auth(request: Request) -> RedirectResponse | None:
    if _authed(request):
        return None
    return RedirectResponse("/login", status_code=303)


def _require_auth_json(request: Request) -> JSONResponse | None:
    if _authed(request):
        return None
    return JSONResponse({"error": "unauthorized"}, status_code=401)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if _authed(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": None}
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, password: str = Form("")):
    if password != os.getenv(PASSWORD_ENV):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Wrong password."}
        )
    request.session["authed"] = True
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    guard = _require_auth(request)
    if guard:
        return guard
    return templates.TemplateResponse("index.html", {"request": request})


def _handle_tmdb_errors(exc: Exception) -> JSONResponse:
    if isinstance(exc, TMDBAuthError):
        return JSONResponse({"error": "tmdb_auth", "detail": str(exc)}, status_code=401)
    if isinstance(exc, (TMDBConnectionError, TMDBTimeoutError)):
        return JSONResponse({"error": "tmdb_connection", "detail": str(exc)}, status_code=503)
    if isinstance(exc, TMDBResponseError):
        return JSONResponse({"error": "tmdb_response", "detail": str(exc)}, status_code=502)
    if isinstance(exc, TMDBError):
        return JSONResponse({"error": "tmdb_error", "detail": str(exc)}, status_code=500)
    return JSONResponse({"error": "unknown", "detail": str(exc)}, status_code=500)


@app.get("/api/search")
def api_search(request: Request, query: str, page: int = 1):
    guard = _require_auth_json(request)
    if guard:
        return guard
    try:
        payload = search_multi(query, page=page)
        return payload
    except Exception as exc:  # noqa: BLE001 - returning error for UI
        return _handle_tmdb_errors(exc)


@app.get("/api/seasons")
def api_seasons(request: Request, show_id: int):
    guard = _require_auth_json(request)
    if guard:
        return guard
    try:
        seasons = get_seasons(show_id)
        return {"seasons": seasons}
    except Exception as exc:  # noqa: BLE001 - returning error for UI
        return _handle_tmdb_errors(exc)


@app.get("/api/episodes")
def api_episodes(request: Request, show_id: int, season_number: int):
    guard = _require_auth_json(request)
    if guard:
        return guard
    try:
        episodes = get_episodes(show_id, season_number)
        return {"episodes": episodes}
    except Exception as exc:  # noqa: BLE001 - returning error for UI
        return _handle_tmdb_errors(exc)


@app.get("/api/embed")
def api_embed(request: Request, media_type: str, tmdb_id: int, season: int | None = None, episode: int | None = None) -> dict[str, Any]:
    guard = _require_auth_json(request)
    if guard:
        return guard
    if media_type == "movie":
        return {"url": GET_MOVIE_EMBED(tmdb_id)}
    if media_type == "tv":
        if season is None or episode is None:
            return JSONResponse({"error": "missing_params"}, status_code=400)
        return {"url": GET_SHOW_EMBED(tmdb_id, season, episode)}
    return JSONResponse({"error": "unsupported_media_type"}, status_code=400)
