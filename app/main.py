from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.embedding import explain_ranking
from app.rag_pipeline import find_research_papers


app = FastAPI(
    title="AI Knowledge Assistant",
    description="A topic-bounded academic research assistant.",
    version="0.1.0",
)


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Research topic or question.")
    limit: int = Field(10, ge=1, le=25)
    year_from: int | None = Field(None, ge=1900, le=2100)
    sources: list[Literal["semantic_scholar", "openalex"]] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
