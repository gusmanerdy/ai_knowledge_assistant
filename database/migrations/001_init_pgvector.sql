CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doi TEXT,
    title TEXT NOT NULL,
    abstract TEXT,
    publication_year INTEGER CHECK (publication_year IS NULL OR publication_year BETWEEN 1000 AND 3000),
    publication_date DATE,
    venue TEXT,
    url TEXT,
    citation_count INTEGER NOT NULL DEFAULT 0 CHECK (citation_count >= 0),
    is_open_access BOOLEAN,
    fields_of_study TEXT[] NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    search_vector TSVECTOR NOT NULL DEFAULT ''::tsvector,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT papers_doi_not_blank CHECK (doi IS NULL OR length(trim(doi)) > 0)
);

CREATE UNIQUE INDEX papers_doi_unique_idx
    ON papers (lower(doi))
    WHERE doi IS NOT NULL;

CREATE INDEX papers_publication_year_idx ON papers (publication_year DESC);
CREATE INDEX papers_citation_count_idx ON papers (citation_count DESC);
CREATE INDEX papers_search_vector_idx ON papers USING GIN (search_vector);
CREATE INDEX papers_fields_of_study_idx ON papers USING GIN (fields_of_study);

CREATE TABLE paper_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('semantic_scholar', 'openalex', 'arxiv', 'crossref')),
    source_paper_id TEXT NOT NULL,
    source_url TEXT,
    source_score DOUBLE PRECISION,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_paper_id)
);

CREATE INDEX paper_sources_paper_id_idx ON paper_sources (paper_id);
CREATE INDEX paper_sources_source_idx ON paper_sources (source);
CREATE INDEX paper_sources_raw_payload_idx ON paper_sources USING GIN (raw_payload);

CREATE TABLE authors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    orcid TEXT,
    openalex_id TEXT,
    semantic_scholar_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (normalized_name)
);

CREATE INDEX authors_display_name_idx ON authors (display_name);
CREATE INDEX authors_orcid_idx ON authors (orcid) WHERE orcid IS NOT NULL;

CREATE TABLE paper_authors (
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    author_id UUID NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    author_order INTEGER NOT NULL CHECK (author_order >= 1),
    affiliation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (paper_id, author_id),
    UNIQUE (paper_id, author_order)
);

CREATE INDEX paper_authors_author_id_idx ON paper_authors (author_id);

CREATE TABLE paper_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    embedding_kind TEXT NOT NULL CHECK (embedding_kind IN ('title', 'abstract', 'title_abstract', 'summary')),
    embedding_model TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL DEFAULT 1536 CHECK (embedding_dimensions = 1536),
    content_hash TEXT NOT NULL,
    content_text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (paper_id, embedding_kind, embedding_model, content_hash)
);

CREATE INDEX paper_embeddings_paper_id_idx ON paper_embeddings (paper_id);
CREATE INDEX paper_embeddings_kind_model_idx ON paper_embeddings (embedding_kind, embedding_model);

CREATE INDEX paper_embeddings_embedding_hnsw_idx
    ON paper_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE TABLE searches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    query_embedding vector(1536),
    year_from INTEGER CHECK (year_from IS NULL OR year_from BETWEEN 1000 AND 3000),
    year_to INTEGER CHECK (year_to IS NULL OR year_to BETWEEN 1000 AND 3000),
    sources TEXT[] NOT NULL DEFAULT '{}',
    limit_requested INTEGER NOT NULL DEFAULT 10 CHECK (limit_requested BETWEEN 1 AND 100),
    ranking_strategy TEXT NOT NULL DEFAULT 'hybrid_v1',
    filters JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX searches_query_idx ON searches USING GIN (to_tsvector('english', query));
CREATE INDEX searches_created_at_idx ON searches (created_at DESC);

CREATE TABLE search_results (
    search_id UUID NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL CHECK (rank >= 1),
    score DOUBLE PRECISION NOT NULL DEFAULT 0,
    keyword_rank DOUBLE PRECISION,
    vector_distance DOUBLE PRECISION,
    ranking_reasons TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (search_id, paper_id),
    UNIQUE (search_id, rank)
);

CREATE INDEX search_results_paper_id_idx ON search_results (paper_id);
CREATE INDEX search_results_search_rank_idx ON search_results (search_id, rank);

CREATE TABLE paper_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    summary_kind TEXT NOT NULL CHECK (summary_kind IN ('short', 'structured', 'limitations', 'relevance')),
    summary_text TEXT NOT NULL,
    model TEXT,
    prompt_version TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (paper_id, summary_kind, model, prompt_version)
);

CREATE INDEX paper_summaries_paper_id_idx ON paper_summaries (paper_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_papers_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector =
        setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.abstract, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(NEW.doi, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.venue, '')), 'C') ||
        setweight(to_tsvector('english', array_to_string(NEW.fields_of_study, ' ')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER papers_set_updated_at
BEFORE UPDATE ON papers
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER papers_set_search_vector
BEFORE INSERT OR UPDATE OF title, abstract, doi, venue, fields_of_study ON papers
FOR EACH ROW
EXECUTE FUNCTION set_papers_search_vector();

CREATE TRIGGER authors_set_updated_at
BEFORE UPDATE ON authors
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
