from __future__ import annotations

from typing import Any

import httpx


SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
OPENALEX_URL = "https://api.openalex.org/works"


def _authors_from_semantic_scholar(paper: dict[str, Any]) -> list[str]:
    return [author.get("name", "") for author in paper.get("authors", []) if author.get("name")]


def _authors_from_openalex(work: dict[str, Any]) -> list[str]:
    authors = []
    for authorship in work.get("authorships", []):
        author_name = authorship.get("author", {}).get("display_name")
        if author_name:
            authors.append(author_name)
    return authors


def _openalex_abstract(work: dict[str, Any]) -> str | None:
    inverted_index = work.get("abstract_inverted_index")
    if not inverted_index:
        return None

    words_by_position: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for position in positions:
            words_by_position[position] = word

    return " ".join(words_by_position[index] for index in sorted(words_by_position))


def _normalize_semantic_scholar(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": paper.get("paperId"),
        "source": "semantic_scholar",
        "title": paper.get("title"),
        "authors": _authors_from_semantic_scholar(paper),
        "year": paper.get("year"),
        "abstract": paper.get("abstract"),
        "url": paper.get("url"),
        "doi": paper.get("externalIds", {}).get("DOI"),
        "citation_count": paper.get("citationCount"),
    }


def _normalize_openalex(work: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": work.get("id"),
        "source": "openalex",
        "title": work.get("title"),
        "authors": _authors_from_openalex(work),
        "year": work.get("publication_year"),
        "abstract": _openalex_abstract(work),
        "url": work.get("primary_location", {}).get("landing_page_url") or work.get("id"),
        "doi": work.get("doi"),
        "citation_count": work.get("cited_by_count"),
    }


async def search_semantic_scholar(query: str, limit: int = 10, year_from: int | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,url,externalIds,citationCount",
    }
    if year_from:
        params["year"] = f"{year_from}-"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(SEMANTIC_SCHOLAR_URL, params=params)
        response.raise_for_status()

    return [_normalize_semantic_scholar(paper) for paper in response.json().get("data", [])]


async def search_openalex(query: str, limit: int = 10, year_from: int | None = None) -> list[dict[str, Any]]:
    filters = []
    if year_from:
        filters.append(f"from_publication_date:{year_from}-01-01")

    params: dict[str, Any] = {
        "search": query,
        "per-page": limit,
        "sort": "relevance_score:desc",
    }
    if filters:
        params["filter"] = ",".join(filters)

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(OPENALEX_URL, params=params)
        response.raise_for_status()

    return [_normalize_openalex(work) for work in response.json().get("results", [])]
