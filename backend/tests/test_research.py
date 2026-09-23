from __future__ import annotations

import json
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from backend.app.clients.model_client import ModelError
from backend.app.clients.ollama import OllamaClient
from backend.app.clients.openrouter import OpenRouterClient
from backend.app.core.auth import ACCOUNTS, SESSION_COOKIE, SessionUser, create_session_token
from backend.app.core.model_settings import ModelSettings
from backend.app.main import app
from backend.app.services.paper_search import rank_papers
from backend.app.services.research import answer_research_question


PAPER = {
    "title": "Evaluating Retrieval-Augmented Generation",
    "authors": ["A. Researcher"],
    "year": 2025,
    "source": "openalex",
    "url": "https://example.org/paper",
    "doi": "10.1234/example",
    "citation_count": 3,
    "abstract": "Evaluates answer faithfulness and retrieval quality.",
    "summary": "Evaluates answer faithfulness and retrieval quality.",
}


class ResearchTests(unittest.IsolatedAsyncioTestCase):
    def authorize(self, client: httpx.AsyncClient, role: str) -> None:
        account = next(account for account in ACCOUNTS.values() if account.role == role)
        token = create_session_token(
            SessionUser(account.username, account.display_name, account.role)
        )
        client.cookies.set(SESSION_COOKIE, token)

    async def test_indonesian_question_uses_english_search_and_valid_citation(self) -> None:
        model = Mock(model="google/gemini-3.8-flash")
        model.complete_json = AsyncMock(side_effect=[
            {"answer_language": "id", "english_query": "RAG answer quality evaluation"},
            {"paragraphs": [{"text": "Evaluasi mencakup faithfulness.", "citations": [1]}]},
        ])
        with patch("backend.app.services.research.OpenRouterClient", return_value=model), patch(
            "backend.app.services.research.find_research_papers", new_callable=AsyncMock, return_value=[PAPER]
        ) as search:
            result = await answer_research_question(
                "Bagaimana mengevaluasi RAG?", 8, 2020, ["openalex"]
            )

        search.assert_awaited_once_with(
            query="Bagaimana mengevaluasi RAG?",
            limit=8,
            year_from=2020,
            sources=["openalex"],
            additional_queries=["RAG answer quality evaluation"],
        )
        self.assertEqual(result["answer_language"], "id")
        self.assertEqual(result["paragraphs"][0]["citations"], [1])
        answer_messages = model.complete_json.await_args_list[1].kwargs["messages"]
        self.assertIn('"citation": 1', answer_messages[1]["content"])
        self.assertEqual(result["model_settings"]["max_tokens"], 1800)
        self.assertEqual(result["diagnostics"]["cited_papers"], 1)
        self.assertEqual(model.complete_json.await_args_list[1].kwargs["temperature"], 0.2)

    async def test_rejects_citation_outside_retrieved_papers(self) -> None:
        model = Mock(model="google/gemini-3.8-flash")
        model.complete_json = AsyncMock(side_effect=[
            {"answer_language": "en", "english_query": "RAG evaluation"},
            {"paragraphs": [{"text": "Claim.", "citations": [2]}]},
        ])
        with patch("backend.app.services.research.OpenRouterClient", return_value=model), patch(
            "backend.app.services.research.find_research_papers", new_callable=AsyncMock, return_value=[PAPER]
        ):
            with self.assertRaises(ModelError):
                await answer_research_question("How do we evaluate RAG?", 8, None, None)

    async def test_missing_key_returns_clear_error_without_search(self) -> None:
        transport = httpx.ASGITransport(app=app)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}), patch(
            "backend.app.main.load_model_settings", return_value=ModelSettings(provider="openrouter")
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                self.authorize(client, "researcher")
                response = await client.post(
                    "/research/query",
                    json={"query": "Bagaimana mengevaluasi RAG?"},
                )
        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENROUTER_API_KEY", response.json()["detail"])

    async def test_endpoint_uses_admin_model_settings(self) -> None:
        transport = httpx.ASGITransport(app=app)
        settings = ModelSettings(
            provider="local",
            intent="Membuat ringkasan kritis",
            response_instruction="Jawab singkat dan sebutkan keterbatasan bukti.",
            max_tokens=640,
            paragraph_count=2,
            temperature=0.1,
            evidence_policy="strict",
        )
        answer = AsyncMock(return_value={
            "question": "Bagaimana mengevaluasi RAG?",
            "answer_language": "id",
            "search_queries": ["Bagaimana mengevaluasi RAG?"],
            "provider": "local",
            "model": "qwen2.5-3b-instruct-q6k",
            "paragraphs": [],
            "papers": [],
        })
        with patch("backend.app.main.load_model_settings", return_value=settings), patch(
            "backend.app.main.answer_research_question", answer
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                self.authorize(client, "researcher")
                response = await client.post(
                    "/research/query",
                    json={"query": "Bagaimana mengevaluasi RAG?"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(answer.await_args.kwargs["settings"], settings)

    async def test_admin_endpoint_saves_valid_model_settings(self) -> None:
        transport = httpx.ASGITransport(app=app)
        saved = ModelSettings(
            provider="openrouter",
            intent="Membandingkan temuan paper",
            response_instruction="Bandingkan temuan dan jelaskan perbedaan metodologinya.",
            max_tokens=1200,
            paragraph_count=2,
            temperature=0.3,
            evidence_policy="balanced",
        )
        save = Mock(return_value=saved)
        with patch("backend.app.main.save_model_settings", save):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                self.authorize(client, "admin")
                response = await client.put("/admin/model-settings", json=saved.model_dump())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "Membandingkan temuan paper")
        self.assertEqual(save.call_args.args[0], saved)

    async def test_rbac_blocks_viewer_from_research_and_researcher_from_admin(self) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            self.authorize(client, "viewer")
            viewer_response = await client.post(
                "/research/query", json={"query": "Bagaimana mengevaluasi RAG?"}
            )
            self.authorize(client, "researcher")
            researcher_response = await client.get("/admin/model-settings")

        self.assertEqual(viewer_response.status_code, 403)
        self.assertEqual(researcher_response.status_code, 403)

    async def test_each_role_is_redirected_to_its_landing_page(self) -> None:
        transport = httpx.ASGITransport(app=app)
        expected_paths = {
            "admin": "/admin",
            "researcher": "/research",
            "viewer": "/viewer",
        }
        for role, expected_path in expected_paths.items():
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test", follow_redirects=False
            ) as client:
                self.authorize(client, role)
                response = await client.get("/")
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response.headers["location"], expected_path)

    async def test_unauthenticated_api_request_is_rejected(self) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/research/query", json={"query": "Bagaimana mengevaluasi RAG?"}
            )

        self.assertEqual(response.status_code, 401)

    async def test_frontend_pages_and_static_assets_are_served_from_new_paths(self) -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.get("/login")
            stylesheet = await client.get("/static/css/tailwind.css")
            script = await client.get("/static/js/login.js")
            favicon = await client.get("/static/images/favicon.ico")

        self.assertEqual(login.status_code, 200)
        self.assertIn("AI Knowledge Assistant", login.text)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("text/css", stylesheet.headers["content-type"])
        self.assertEqual(script.status_code, 200)
        self.assertIn("javascript", script.headers["content-type"])
        self.assertEqual(favicon.status_code, 200)
        self.assertEqual(favicon.headers["content-type"], "image/x-icon")

    async def test_openrouter_request_uses_structured_output(self) -> None:
        captured = {}

        def handle(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            return httpx.Response(200, json={
                "choices": [{"message": {"content": '{"answer_language":"id"}'}}]
            })

        real_client = httpx.AsyncClient

        def fake_client(*args, **kwargs):
            return real_client(*args, transport=httpx.MockTransport(handle), **kwargs)

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}), patch(
            "backend.app.clients.openrouter.httpx.AsyncClient", side_effect=fake_client
        ):
            result = await OpenRouterClient().complete_json(
                [{"role": "user", "content": "Halo"}],
                "query_plan",
                {"type": "object"},
                300,
            )

        self.assertEqual(result["answer_language"], "id")
        self.assertEqual(captured["model"], "google/gemini-3.8-flash")
        self.assertEqual(captured["response_format"]["type"], "json_schema")
        self.assertTrue(captured["provider"]["require_parameters"])
        self.assertEqual(captured["plugins"], [{"id": "response-healing"}])

    async def test_openrouter_retries_one_malformed_response(self) -> None:
        calls = 0

        def handle(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            content = "not-json" if calls == 1 else '{"answer_language":"id"}'
            return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

        real_client = httpx.AsyncClient

        def fake_client(*args, **kwargs):
            return real_client(*args, transport=httpx.MockTransport(handle), **kwargs)

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}), patch(
            "backend.app.clients.openrouter.httpx.AsyncClient", side_effect=fake_client
        ):
            result = await OpenRouterClient().complete_json(
                [{"role": "user", "content": "Halo"}],
                "query_plan",
                {"type": "object"},
                300,
            )

        self.assertEqual(result["answer_language"], "id")
        self.assertEqual(calls, 2)

    async def test_ollama_request_uses_local_model_and_schema(self) -> None:
        captured = {}

        def handle(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={
                "message": {"content": '{"answer_language":"id"}'},
                "done": True,
            })

        real_client = httpx.AsyncClient

        def fake_client(*args, **kwargs):
            return real_client(*args, transport=httpx.MockTransport(handle), **kwargs)

        with patch.dict(os.environ, {
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
            "OLLAMA_MODEL": "qwen2.5-3b-instruct-q6k",
        }), patch("backend.app.clients.ollama.httpx.AsyncClient", side_effect=fake_client):
            result = await OllamaClient().complete_json(
                [{"role": "user", "content": "Halo"}],
                "query_plan",
                {"type": "object", "properties": {"answer_language": {"type": "string"}}},
                300,
            )

        self.assertEqual(result["answer_language"], "id")
        self.assertEqual(captured["model"], "qwen2.5-3b-instruct-q6k")
        self.assertEqual(captured["format"]["type"], "object")
        self.assertEqual(captured["options"]["temperature"], 0)
        self.assertFalse(captured["stream"])


class RankingTests(unittest.TestCase):
    def test_deduplicates_doi_and_prefers_repeated_relevance(self) -> None:
        first = {"id": "a", "source": "openalex", "doi": "https://doi.org/10.1/test", "title": "Paper A", "abstract": None}
        same = {"id": "b", "source": "semantic_scholar", "doi": "10.1/test", "title": "Paper A", "abstract": "Useful abstract"}
        other = {"id": "c", "source": "openalex", "doi": "10.1/other", "title": "Paper B", "abstract": "Other"}

        ranked = rank_papers([[first, other], [same]], 5)

        self.assertEqual(len(ranked), 2)
        self.assertEqual(ranked[0]["abstract"], "Useful abstract")


if __name__ == "__main__":
    unittest.main()
