from __future__ import annotations

import asyncio
import re
from typing import Any

from app.loader import search_openalex, search_semantic_scholar


def _paper_key(paper: dict[str, Any]) -> str:
    doi = (paper.get("doi") or "").lower().removeprefix("https://doi.org/")
    if doi:
        return f"doi:{doi}"
    title = re.sub(r"\W+", " ", (paper.get("title") or "").casefold()).strip()
    return f"title:{title}" if title else f"{paper.get('source')}:{paper.get('id')}"


def rank_papers(result_sets: list[list[dict[str, Any]]], limit: int) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    scores: dict[str, float] = {}
    for result_set in result_sets:
        for rank, paper in enumerate(result_set, start=1):
            key = _paper_key(paper)
            scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
            if key not in candidates or (
                not candidates[key].get("abstract") and paper.get("abstract")
            ):
                candidates[key] = paper

    return sorted(
        candidates.values(),
        key=lambda paper: (
            scores[_paper_key(paper)],
            bool(paper.get("abstract")),
            paper.get("citation_count") or 0,
        ),
        reverse=True,
    )[:limit]


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
        "abstract": paper.get("abstract"),
        "summary": short_abstract or "No abstract available from the selected source.",
    }


async def find_research_papers(
    query: str,
    limit: int = 10,
    year_from: int | None = None,
    sources: list[str] | None = None,
    additional_queries: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected_sources = sources or ["semantic_scholar", "openalex"]
    queries = list(dict.fromkeys([query, *(additional_queries or [])]))
    per_source_limit = max(limit, 5)
    requests = []
    for search_query in queries:
        if "semantic_scholar" in selected_sources:
            requests.append(search_semantic_scholar(search_query, per_source_limit, year_from))
        if "openalex" in selected_sources:
            requests.append(search_openalex(search_query, per_source_limit, year_from))

    results = await asyncio.gather(*requests, return_exceptions=True)
    result_sets = [result for result in results if isinstance(result, list)]
    if not result_sets and results:
        raise results[0]

    ranked_papers = rank_papers(result_sets, limit)
    return [summarize_paper_metadata(paper) for paper in ranked_papers]
