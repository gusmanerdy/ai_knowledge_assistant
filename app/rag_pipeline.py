from __future__ import annotations

from typing import Any

from app.loader import search_openalex, search_semantic_scholar


def _paper_score(paper: dict[str, Any]) -> tuple[int, int, int]:
    has_abstract = 1 if paper.get("abstract") else 0
    citation_count = paper.get("citation_count") or 0
    year = paper.get("year") or 0
    return has_abstract, citation_count, year


def rank_papers(papers: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return sorted(papers, key=_paper_score, reverse=True)[:limit]


def summarize_paper_metadata(paper: dict[str, Any]) -> dict[str, Any]:
    abstract = paper.get("abstract") or ""
    short_abstract = abstract[:700].strip()
    if len(abstract) > 700:
        short_abstract += "..."

    return {
        "title": paper.get("title"),
        "authors": paper.get("authors", []),
        "year": paper.get("year"),
        "source": paper.get("source"),
        "url": paper.get("url"),
        "doi": paper.get("doi"),
        "citation_count": paper.get("citation_count"),
        "summary": short_abstract or "No abstract available from the selected source.",
    }


async def find_research_papers(
    query: str,
    limit: int = 10,
    year_from: int | None = None,
    sources: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected_sources = sources or ["semantic_scholar", "openalex"]
    per_source_limit = max(limit, 5)
    papers: list[dict[str, Any]] = []

    if "semantic_scholar" in selected_sources:
        papers.extend(await search_semantic_scholar(query, per_source_limit, year_from))

    if "openalex" in selected_sources:
        papers.extend(await search_openalex(query, per_source_limit, year_from))

    ranked_papers = rank_papers(papers, limit)
    return [summarize_paper_metadata(paper) for paper in ranked_papers]
