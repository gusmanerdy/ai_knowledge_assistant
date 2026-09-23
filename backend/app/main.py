from __future__ import annotations

from typing import Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.app.clients.model_client import ModelError
from backend.app.core.auth import (
    SESSION_COOKIE,
    SESSION_DURATION_SECONDS,
    SessionUser,
    authenticate,
    create_session_token,
    current_user_or_none,
    landing_path,
    require_roles,
    require_user,
)
from backend.app.core.model_settings import (
    ModelSettings,
    load_model_settings,
    reset_model_settings,
    save_model_settings,
)
from backend.app.core.paths import FRONTEND_PAGES, FRONTEND_STATIC
from backend.app.services.paper_search import find_research_papers
from backend.app.services.ranking import explain_ranking
from backend.app.services.research import answer_research_question


app = FastAPI(
    title="AI Knowledge Assistant",
    description="A topic-bounded academic research assistant.",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=str(FRONTEND_STATIC)), name="static")


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Research topic or question.")
    limit: int = Field(10, ge=1, le=25)
    year_from: int | None = Field(None, ge=1900, le=2100)
    sources: list[Literal["semantic_scholar", "openalex"]] | None = None


class ResearchQueryRequest(PaperSearchRequest):
    query: str = Field(..., min_length=3, max_length=2000)
    limit: int = Field(8, ge=1, le=12)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=200)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(FRONTEND_STATIC / "images/favicon.ico", media_type="image/x-icon")


@app.get("/login", include_in_schema=False)
def login_page(request: Request) -> Response:
    user = current_user_or_none(request)
    if user:
        return RedirectResponse(landing_path(user.role), status_code=303)
    return FileResponse(FRONTEND_PAGES / "login.html")


@app.post("/auth/login", include_in_schema=False)
def login(request: LoginRequest, response: Response) -> dict[str, str]:
    user = authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Username atau password tidak benar.")
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user),
        max_age=SESSION_DURATION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "redirect_to": landing_path(user.role),
    }


@app.post("/auth/logout", include_in_schema=False)
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")
    return {"ok": True}


@app.get("/auth/me", include_in_schema=False)
def auth_me(user: SessionUser = Depends(require_user)) -> dict[str, str]:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
    }


@app.get("/", include_in_schema=False)
def home(request: Request) -> Response:
    user = current_user_or_none(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse(landing_path(user.role), status_code=303)


@app.get("/research", include_in_schema=False)
def research_page(request: Request) -> Response:
    user = current_user_or_none(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role not in ("admin", "researcher"):
        return RedirectResponse(landing_path(user.role), status_code=303)
    return FileResponse(FRONTEND_PAGES / "research.html")


@app.get("/admin", include_in_schema=False)
def admin(request: Request) -> Response:
    user = current_user_or_none(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role != "admin":
        return RedirectResponse(landing_path(user.role), status_code=303)
    return FileResponse(FRONTEND_PAGES / "admin.html")


@app.get("/viewer", include_in_schema=False)
def viewer_page(request: Request) -> Response:
    user = current_user_or_none(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return FileResponse(FRONTEND_PAGES / "viewer.html")


@app.get("/docs", include_in_schema=False)
def api_docs(_user: SessionUser = Depends(require_roles("admin"))) -> Response:
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="AI Knowledge Assistant API",
        swagger_favicon_url="/static/images/favicon.png?v=2",
    )


@app.get("/openapi.json", include_in_schema=False)
def openapi_schema(_user: SessionUser = Depends(require_roles("admin"))) -> JSONResponse:
    return JSONResponse(app.openapi())


@app.get("/admin/model-settings")
def get_model_settings(_user: SessionUser = Depends(require_roles("admin"))) -> ModelSettings:
    return load_model_settings()


@app.get("/model-profile")
def get_model_profile(
    _user: SessionUser = Depends(require_roles("admin", "researcher")),
) -> dict[str, str | int]:
    settings = load_model_settings()
    return {
        "provider": settings.provider,
        "intent": settings.intent,
        "max_tokens": settings.max_tokens,
    }


@app.put("/admin/model-settings")
def update_model_settings(
    settings: ModelSettings,
    _user: SessionUser = Depends(require_roles("admin")),
) -> ModelSettings:
    return save_model_settings(settings)


@app.post("/admin/model-settings/reset")
def restore_model_settings(_user: SessionUser = Depends(require_roles("admin"))) -> ModelSettings:
    return reset_model_settings()


@app.post("/papers/search")
async def search_papers(
    request: PaperSearchRequest,
    _user: SessionUser = Depends(require_roles("admin", "researcher")),
) -> dict[str, object]:
    papers = await find_research_papers(
        query=request.query,
        limit=request.limit,
        year_from=request.year_from,
        sources=list(request.sources) if request.sources else None,
    )

    return {
        "query": request.query,
        "count": len(papers),
        "papers": [
            {
                **paper,
                "ranking_reasons": explain_ranking(paper),
            }
            for paper in papers
        ],
    }


@app.post("/research/query")
async def research_query(
    request: ResearchQueryRequest,
    _user: SessionUser = Depends(require_roles("admin", "researcher")),
) -> dict[str, object]:
    try:
        settings = load_model_settings()
        return await answer_research_question(
            question=request.query,
            limit=request.limit,
            year_from=request.year_from,
            sources=list(request.sources) if request.sources else None,
            settings=settings,
        )
    except ModelError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Sumber paper tidak dapat dihubungi saat ini.") from exc
