from __future__ import annotations

from typing import Any


def explain_ranking(paper: dict[str, Any]) -> list[str]:
    reasons = []

    if paper.get("summary") and paper["summary"] != "No abstract available from the selected source.":
        reasons.append("abstract available")

    if paper.get("citation_count"):
        reasons.append(f"{paper['citation_count']} citations")

    if paper.get("year"):
        reasons.append(f"published in {paper['year']}")

    return reasons or ["basic metadata match"]
