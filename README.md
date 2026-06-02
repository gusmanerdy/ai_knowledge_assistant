# AI Knowledge Assistant

AI Knowledge Assistant is an early-stage Retrieval-Augmented Generation (RAG) project for asking questions over personal documents and notes.

The goal is to build a local knowledge assistant that can ingest files, retrieve the most relevant context, and generate grounded answers based on the indexed material.

## Project Vision

This project is intended to become a lightweight assistant for working with private knowledge sources such as:

- PDF documents
- Research notes
- Course material
- Internal documentation
- Personal reference files

Instead of answering only from a language model's general knowledge, the assistant should retrieve relevant passages from uploaded documents and use them as context for its response.

## Current Stack

The current dependency set suggests the project is being built around:

- **FastAPI** for the backend API
- **LangChain** for RAG orchestration
- **FAISS** for local vector search
- **Sentence Transformers** for embeddings
- **PyPDF** for PDF parsing
- **Uvicorn** for running the API server

## Planned Features

### Document Ingestion

- Load PDF files
- Extract readable text
- Split documents into searchable chunks
- Store document metadata such as filename, page number, and chunk position

### Vector Search

- Generate embeddings for document chunks
- Store embeddings in a local FAISS index
- Retrieve the most relevant chunks for a user question

### Question Answering

- Accept user questions through an API endpoint
- Retrieve supporting document context
- Generate answers grounded in retrieved content
- Return sources or citations with each answer

### API

Planned API endpoints:

```text
POST /ingest      Add documents to the knowledge base
POST /ask         Ask a question over indexed documents
GET /documents    List indexed documents
GET /health       Check service status
```

### Future UI

A simple user interface may be added after the backend is stable. Possible options include:

- Streamlit
- Gradio
- A small web frontend

## Suggested Development Roadmap

1. Build a basic PDF ingestion script.
2. Create and persist a FAISS vector index.
3. Add a retriever that returns relevant document chunks.
4. Add FastAPI endpoints for ingestion and question answering.
5. Return source metadata with generated answers.
6. Add tests for ingestion, retrieval, and API behavior.
7. Add a simple UI for uploading files and asking questions.

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
uvicorn app:app --reload
```

## Notes

This repository is currently in an early planning and implementation stage. The README describes the intended direction so future development can stay focused and incremental.
