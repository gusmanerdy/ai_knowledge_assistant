# AI Knowledge Assistant

AI Knowledge Assistant is an early-stage research assistant for discovering, summarizing, and comparing academic papers about a focused topic.

The current product direction is to help users search trusted scholarly sources, review relevant papers, and generate grounded research briefs with clear citations.

## Project Structure

```text
backend/
  app/
    clients/       External model clients for OpenRouter and Ollama
    core/          Authentication, settings, and project paths
    services/      Paper discovery, ranking, and answer generation
    main.py        FastAPI application entry point
  tests/           Backend automated tests
  requirements.txt

frontend/
  pages/           HTML pages served by FastAPI
  static/
    css/           Tailwind source and compiled CSS
    images/        Favicons and browser assets
    js/            Page-specific browser scripts
  package.json     Frontend build dependencies and commands

database/
  migrations/      Ordered PostgreSQL migrations
  queries/         Reference and diagnostic SQL queries

infrastructure/
  docker-compose.yml
  ollama/          Ollama model definitions

storage/
  documents/       Local source documents
  model_settings.json  Runtime model settings, ignored by Git

docs/
  notes/           Planning and historical technical notes
```

## Project Vision

The goal is to build a topic-bounded academic research assistant.

Instead of scanning local laptop folders, the assistant will search academic sources on the web and help users understand the most relevant papers for a given topic.

Example user prompts:

```text
Find recent papers about RAG evaluation.
Compare papers about OCR in document understanding.
Summarize research trends in small language models.
What are the main limitations of current AI research assistants?
```

The assistant should return useful paper metadata, short summaries, and source links so users can continue reading from the original sources.

## Core Principles

- Keep research topics focused and constrained.
- Search trusted academic sources before general web sources.
- Show sources clearly for every result and generated answer.
- Separate paper discovery from answer generation.
- Avoid scanning local files or private folders in the first version.
- Keep OCR as a future optional feature.

## Planned Sources

The first version should prioritize scholarly APIs instead of generic search scraping.

Potential sources:

- Semantic Scholar for paper search, abstracts, citations, authors, and references
- OpenAlex for broad scholarly metadata and research discovery
- arXiv for preprints, especially AI, ML, math, and computer science topics
- Crossref for DOI and publisher metadata

## Main Features

### Paper Search

- Accept a research topic or question
- Search academic APIs for relevant papers
- Return paper titles, authors, year, abstract, DOI or source URL, and citation metadata when available
- Allow constraints such as year range, result count, source, and sort order

### Paper Ranking

- Rank papers by relevance
- Optionally consider recency, citation count, source quality, and availability of abstracts
- Keep ranking explainable so users can understand why a paper was selected

### Paper Summaries

Summaries should be short and practical.

For each paper, the assistant should identify:

- Research problem
- Method or approach
- Key findings
- Limitations, when available
- Why the paper is relevant to the user query

### Research Briefs

The assistant should eventually generate a brief overview for a topic.

A research brief may include:

- Topic overview
- Top relevant papers
- Common themes
- Conflicting findings or open questions
- Research gaps
- Suggested next papers to read

### Question Answering

The assistant may answer user questions using only the papers retrieved for the current topic.

Answers should:

- Cite the papers used
- Avoid unsupported claims
- Mention when the retrieved sources are insufficient
- Prefer cautious summaries over overconfident conclusions

## API

Available FastAPI endpoints:

```text
GET  /health             Check service status
GET  /login              Sign in to the application
POST /auth/login         Create an 8-hour signed session
POST /auth/logout        End the active session
GET  /admin              Manage the active model response configuration
GET  /admin/model-settings
PUT  /admin/model-settings
POST /papers/search      Search for papers by topic
POST /research/query     Answer a question with cited paper abstracts via OpenRouter or Ollama
```

## Suggested Development Roadmap

1. Build a basic paper search endpoint using one academic API.
2. Normalize paper metadata into a consistent internal schema.
3. Add PostgreSQL as the application database.
4. Add pgvector for semantic paper search and embedding storage.
5. Add PostgreSQL full-text search for keyword, title, author, and abstract search.
6. Add query constraints such as year range, result count, and source.
7. Add simple rule-based ranking.
8. Add short paper summaries.
9. Add research brief generation with source citations.
10. Add support for multiple academic APIs.
11. Add semantic reranking or embeddings if basic ranking is not enough.
12. Add OCR support later for uploaded screenshots, scanned papers, or image-based documents.

## Current Stack

The current dependency set includes:

- FastAPI
- Uvicorn
- HTTPX
- Pydantic

Some dependencies were originally selected for local document RAG. As the project pivots toward academic paper discovery, the dependency list may be simplified or adjusted.

## Planned Database And Search Stack

Phase 1 should use PostgreSQL as the source of truth, with pgvector for semantic search and PostgreSQL full-text search for keyword search.

PostgreSQL should store paper metadata, authors, sources, saved searches, summaries, and embeddings. pgvector should handle vector similarity queries over paper embeddings. PostgreSQL full-text search should handle lightweight keyword search across titles, abstracts, authors, topics, and source metadata.

Meilisearch can be considered later as Phase 2 if the app needs a more polished search experience with typo tolerance, search-as-you-type, or dedicated keyword ranking. It should be treated as a secondary index synced from PostgreSQL, not as the source of truth.

The initial database design lives in `docs/database-design.md`. PostgreSQL migrations are in `database/migrations`, with a sample hybrid keyword/vector query in `database/queries/hybrid_paper_search.sql`.

For local development, start PostgreSQL with:

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres
```

This uses the `pgvector/pgvector:pg16` image and automatically applies migrations mounted from `database/migrations` on first database initialization.

## Installation

Clone the repository:

```bash
git clone https://github.com/gusmanerdy/ai_knowledge_assistant.git
cd ai_knowledge_assistant
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Install frontend build dependencies:

```bash
cd frontend
npm install
npm run css:build
cd ..
```

## Running the Project

Create an OpenRouter API key, then open `.env` in the project root and paste it after the equals sign:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=google/gemini-3.8-flash
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5-3b-instruct-q6k
```

The `.env` file is ignored by Git. The default answer model is `google/gemini-3.8-flash`. To use another OpenRouter model that supports structured JSON output, change `OPENROUTER_MODEL` in the same file.

Start the application:

```bash
uvicorn backend.app.main:app --reload
```

During frontend development, run the Tailwind watcher in a second terminal:

```bash
cd frontend
npm run css:dev
```

Open `http://127.0.0.1:8000/`. The research form accepts a question in Indonesian or English, searches Semantic Scholar and OpenAlex with the original question and English research terms, and returns an answer in the question's language with links to the cited papers.

Open `http://127.0.0.1:8000/admin` to manage the active provider, response intent, response instruction, token limit, paragraph count, temperature, and evidence policy. The saved configuration is applied to subsequent research requests without restarting the server.

The application uses signed, HTTP-only session cookies and role-based access control:

- `admin` can use research, manage model settings, and open API documentation.
- `researcher` can use the research workflow but cannot access admin settings.
- `viewer` receives a read-only account page.

Configure `AUTH_SECRET` and the three account credentials in `.env`. When those variables are absent, local development defaults are `admin` / `admin123`, `researcher` / `research123`, and `viewer` / `viewer123`. Replace these defaults before exposing the application outside local development.

For local inference with the existing GGUF file, import it into Ollama:

```bash
ollama create qwen2.5-3b-instruct-q6k -f infrastructure/ollama/qwen2.5-3b-instruct.Modelfile
```

Run the backend tests from the project root:

```bash
python -m unittest backend.tests.test_research -q
```

The current answer uses titles and abstracts returned by the academic APIs. It does not read full papers or search stored pgvector embeddings yet. The PostgreSQL migrations can be applied separately; they are not required for this OpenRouter flow.

## Future OCR Feature

OCR is planned as a later optional feature.

Possible OCR use cases:

- Extract text from uploaded screenshots
- Read scanned paper pages
- Process image-based PDFs
- Add OCR text into the same summarization or question-answering flow

OCR should not be part of the first version because it adds extra complexity, model choices, and resource usage.

## Notes

This repository is in an early planning and implementation stage. The current README describes the updated direction: a focused academic research assistant built around paper discovery, summarization, comparison, and citation-grounded answers.
