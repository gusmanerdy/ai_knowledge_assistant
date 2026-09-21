# Database Design

This project uses PostgreSQL as the source of truth and pgvector for semantic search over academic paper metadata.

## Start Here

The first database milestone should be a paper discovery cache:

1. Store normalized paper metadata from Semantic Scholar and OpenAlex.
2. Deduplicate papers by DOI first, then by source-specific paper IDs.
3. Store raw source payloads for debugging and future re-normalization.
4. Add full-text search over title, abstract, DOI, venue, and fields of study.
5. Add pgvector embeddings for title and abstract semantic search.
6. Store user searches and ranked results so research sessions can be reproduced.

This keeps the first version useful before adding heavier features like generated summaries, research briefs, PDF ingestion, or OCR.

## Core Entities

### papers

Canonical academic works.

Important fields:

- `doi`: primary deduplication key when available.
- `title`, `abstract`, `publication_year`, `venue`, `url`: normalized display/search metadata.
- `citation_count`, `is_open_access`: ranking signals.
- `search_vector`: PostgreSQL full-text index for keyword search.

### paper_sources

Links a canonical paper to source-specific records.

Examples:

- Semantic Scholar `paperId`
- OpenAlex work ID
- arXiv ID
- Crossref DOI metadata record

This table allows the app to merge the same paper from multiple APIs without losing provenance.

### authors and paper_authors

Stores normalized author names and ordered paper authorship.

Author identity from scholarly APIs is imperfect, so the first version keeps this intentionally simple.

### paper_embeddings

Stores vector embeddings for searchable text.

Recommended first embedding records:

- `title_abstract`: title plus abstract
- `title`: title only, useful when abstracts are missing

The schema defaults to `vector(1536)`. If the project later uses an embedding model with a different dimension, create a new embedding table or migration for that dimension instead of mixing dimensions in the same vector column.

### searches and search_results

Stores user search requests, filters, and result ordering.

This makes ranking explainable and allows later features like saved research sessions, "why this paper", and research brief generation from a stable result set.

### paper_summaries

Stores generated summaries separately from paper metadata.

This avoids overwriting source data and allows multiple summary styles or model versions later.

## Search Strategy

Use hybrid retrieval:

1. PostgreSQL full-text search for precise keyword, title, author, DOI, and venue matches.
2. pgvector search for semantic similarity over title and abstract.
3. Application-level ranking that combines source score, citation count, recency, abstract availability, keyword rank, and vector distance.

Initial ranking can stay simple:

```text
score = keyword_rank + semantic_rank + citation_boost + recency_boost + abstract_boost
```

Keep individual ranking signals in API responses so users can understand why a paper was selected.

## Suggested Query Flow

1. User calls `/papers/search`.
2. App checks recent cached `searches`.
3. If needed, app queries Semantic Scholar and OpenAlex.
4. App upserts papers, authors, source mappings, and raw payloads.
5. App creates missing embeddings for papers with title or abstract.
6. App runs hybrid search against PostgreSQL.
7. App stores `search_results`.
8. API returns normalized papers with ranking reasons.

## Phase Boundaries

### Phase 1

- PostgreSQL + pgvector
- Paper/source/author/search tables
- Full-text search
- Embeddings for title and abstract
- Hybrid paper retrieval

### Phase 2

- Generated paper summaries
- Research briefs
- Saved research sessions
- More sources: arXiv, Crossref
- Better deduplication

### Phase 3

- PDF ingestion
- Chunk-level embeddings from full text
- OCR for scanned or image-based documents
- Optional Meilisearch as a secondary search index
