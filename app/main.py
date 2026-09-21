from __future__ import annotations

from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.embedding import explain_ranking
from app.model_client import ModelError
from app.rag_pipeline import find_research_papers
from app.research import answer_research_question


app = FastAPI(
    title="AI Knowledge Assistant",
    description="A topic-bounded academic research assistant.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Research topic or question.")
    limit: int = Field(10, ge=1, le=25)
    year_from: int | None = Field(None, ge=1900, le=2100)
    sources: list[Literal["semantic_scholar", "openalex"]] | None = None


class ResearchQueryRequest(PaperSearchRequest):
    query: str = Field(..., min_length=3, max_length=2000)
    limit: int = Field(8, ge=1, le=12)
    provider: Literal["openrouter", "local"] = "openrouter"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.post("/papers/search")
async def search_papers(request: PaperSearchRequest) -> dict[str, object]:
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
async def research_query(request: ResearchQueryRequest) -> dict[str, object]:
    try:
        return await answer_research_question(
            question=request.query,
            limit=request.limit,
            year_from=request.year_from,
            sources=list(request.sources) if request.sources else None,
            provider=request.provider,
        )
    except ModelError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Sumber paper tidak dapat dihubungi saat ini.") from exc
