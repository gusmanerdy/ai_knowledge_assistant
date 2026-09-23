-- Parameters:
--   $1: plain text query
--   $2: query embedding vector(1536)
--   $3: result limit
--   $4: optional publication year lower bound

WITH keyword_matches AS (
    SELECT
        papers.id AS paper_id,
        ts_rank_cd(papers.search_vector, websearch_to_tsquery('english', $1)) AS keyword_rank
    FROM papers
    WHERE papers.search_vector @@ websearch_to_tsquery('english', $1)
),
vector_matches AS (
    SELECT
        paper_embeddings.paper_id,
        paper_embeddings.embedding <=> $2 AS vector_distance
    FROM paper_embeddings
    WHERE paper_embeddings.embedding_kind = 'title_abstract'
    ORDER BY paper_embeddings.embedding <=> $2
    LIMIT GREATEST($3 * 3, 25)
)
SELECT
    papers.id,
    papers.title,
    papers.abstract,
    papers.publication_year,
    papers.doi,
    papers.url,
    papers.citation_count,
    coalesce(keyword_matches.keyword_rank, 0) AS keyword_rank,
    vector_matches.vector_distance,
    (
        coalesce(keyword_matches.keyword_rank, 0) * 0.55
        + (1 - coalesce(vector_matches.vector_distance, 1)) * 0.35
        + least(log(10, papers.citation_count + 1) / 5, 1) * 0.07
        + CASE
            WHEN papers.publication_year >= extract(year FROM now())::int - 3 THEN 0.03
            ELSE 0
          END
    ) AS hybrid_score
FROM papers
LEFT JOIN keyword_matches ON keyword_matches.paper_id = papers.id
LEFT JOIN vector_matches ON vector_matches.paper_id = papers.id
WHERE
    (keyword_matches.paper_id IS NOT NULL OR vector_matches.paper_id IS NOT NULL)
    AND ($4 IS NULL OR papers.publication_year >= $4)
ORDER BY hybrid_score DESC, papers.citation_count DESC, papers.publication_year DESC NULLS LAST
LIMIT $3;
