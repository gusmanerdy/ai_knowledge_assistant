# AI Knowledge Assistant

AI Knowledge Assistant is an early-stage research assistant for discovering, summarizing, and comparing academic papers about a focused topic.

The current product direction is to help users search trusted scholarly sources, review relevant papers, and generate grounded research briefs with clear citations.

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

## Suggested API Design

Planned FastAPI endpoints:

```text
GET  /health             Check service status
POST /papers/search      Search for papers by topic
POST /papers/summarize   Summarize selected papers
POST /research/brief     Generate a topic research brief
POST /ask                Answer a question using retrieved paper context
```

## Suggested Development Roadmap

1. Build a basic paper search endpoint using one academic API.
2. Normalize paper metadata into a consistent internal schema.
3. Add query constraints such as year range, result count, and source.
4. Add simple rule-based ranking.
5. Add short paper summaries.
6. Add research brief generation with source citations.
7. Add support for multiple academic APIs.
8. Add semantic reranking or embeddings if basic ranking is not enough.
9. Add OCR support later for uploaded screenshots, scanned papers, or image-based documents.

## Current Stack

The current dependency set includes:

- FastAPI
- Uvicorn
- LangChain
- FAISS
- Sentence Transformers
- PyPDF

Some dependencies were originally selected for local document RAG. As the project pivots toward academic paper discovery, the dependency list may be simplified or adjusted.

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
pip install -r requirements.txt
```

## Running the Project

The application entry point is still being developed.

Once the FastAPI app is added, the expected command will be:

```bash
uvicorn app.main:app --reload
```

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
