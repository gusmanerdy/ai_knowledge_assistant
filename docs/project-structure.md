# Project Structure

This repository separates application concerns by runtime and ownership.

## Backend

`backend/app` contains the FastAPI application.

- `clients`: adapters for external model providers.
- `core`: authentication, runtime settings, and absolute project paths.
- `services`: scholarly source access, ranking, search orchestration, and answer generation.
- `main.py`: HTTP routes and FastAPI application setup.
- `backend/tests`: backend unit and API tests.

Run from the repository root:

```bash
uvicorn backend.app.main:app --reload
python -m unittest backend.tests.test_research -q
```

## Frontend

`frontend/pages` contains HTML documents. Browser assets live under `frontend/static` and are mounted by FastAPI at `/static`.

- `static/css`: Tailwind source and generated CSS.
- `static/js`: page and session scripts.
- `static/images`: favicon assets.

Run frontend commands from `frontend`:

```bash
npm install
npm run css:dev
npm run css:build
```

## Database

`database/migrations` contains ordered schema changes. `database/queries` contains reference SQL that is not applied automatically.

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres
```

## Infrastructure And Storage

`infrastructure` contains service definitions and Ollama model files. `storage` contains local runtime data and source documents. Runtime model settings are ignored by Git so admin changes do not become source-code changes.
