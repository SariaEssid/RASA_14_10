import asyncio
import json

import httpx
import pytest
from unittest.mock import AsyncMock

from actions.answer_from_file.llm_helpers import langchain_helpers as rag_helpers

@pytest.mark.asyncio
async def test_retry_does_not_block_other_requests(monkeypatch):

    retry_attempts = 0
    events = []

    async def mock_rag_handler(request):

        nonlocal retry_attempts

        payload = json.loads(request.content)
        question = payload["question"]

        if question == "retry-question":
            retry_attempts += 1

            if retry_attempts == 1:
                events.append("retry_first_attempt")

                return httpx.Response(
                    503,
                    json={"detail": "Temporarily unavailable"}
                )

            events.append("retry_second_attempt")

        else:
            events.append("parallel_request")

        return httpx.Response(
            200,
            json={
                "context": f"context for {question}",
                "source_file": f"{question}.md"
            }
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_rag_handler)
    )

    monkeypatch.setattr(
        rag_helpers.HttpClientManager,
        "_client",
        client
    )

    monkeypatch.setattr(
        rag_helpers,
        "LANG_CHAIN_URL",
        "http://rag.test"
    )

    monkeypatch.setattr(
        rag_helpers,
        "send_standard_fallback_problem_to_team_leader",
        AsyncMock()
    )

    try:
        retry_task = asyncio.create_task(
            rag_helpers.get_context_from_langchain_rag(
                "retry_action",
                "retry-question",
                ["DSI"],
                [],
                3
            )
        )

        # Allow the first request to receive its 503 response.
        while "retry_first_attempt" not in events:
            await asyncio.sleep(0)

        parallel_task = asyncio.create_task(
            rag_helpers.get_context_from_langchain_rag(
                "parallel_action",
                "parallel-question",
                ["DSI"],
                [],
                3
            )
        )

        parallel_result = await parallel_task
        retry_result = await retry_task

        assert parallel_result == (
            "parallel-question.md",
            "context for parallel-question"
        )

        assert retry_result == (
            "retry-question.md",
            "context for retry-question"
        )

        assert retry_attempts == 2

        # The parallel request must complete before the retry attempt.
        assert events.index("parallel_request") < events.index(
            "retry_second_attempt"
        )

    finally:
        await client.aclose()
        rag_helpers.HttpClientManager._client = None

@pytest.mark.asyncio
async def test_concurrent_rag_requests(monkeypatch):

    active_requests = 0
    max_concurrent_requests = 0
    received_questions = []

    async def mock_rag_handler(request):

        nonlocal active_requests, max_concurrent_requests

        assert request.url.path == "/rag/context"

        payload = json.loads(request.content)
        question = payload["question"]

        received_questions.append(question)

        active_requests += 1
        max_concurrent_requests = max(
            max_concurrent_requests,
            active_requests
        )

        try:
            # Simulate asynchronous RAG processing.
            await asyncio.sleep(0.1)

            return httpx.Response(
                200,
                json={
                    "context": f"context for {question}",
                    "source_file": f"{question}.md"
                }
            )
        finally:
            active_requests -= 1

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(mock_rag_handler)
    )

    monkeypatch.setattr(
        rag_helpers.HttpClientManager,
        "_client",
        client
    )

    monkeypatch.setattr(
        rag_helpers,
        "LANG_CHAIN_URL",
        "http://rag.test"
    )

    monkeypatch.setattr(
        rag_helpers,
        "send_standard_fallback_problem_to_team_leader",
        AsyncMock()
    )

    try:
        number_of_requests = 100

        tasks = [
            rag_helpers.get_context_from_langchain_rag(
                action_label=f"test_action_{i}",
                native_question=f"question_{i}",
                domains=["DSI"],
                grades=[],
                nbr_chunks=3
            )
            for i in range(number_of_requests)
        ]

        results = await asyncio.gather(*tasks)

        # Every request must receive its own response.
        assert len(results) == number_of_requests

        for i, (filename, context) in enumerate(results):
            assert filename == f"question_{i}.md"
            assert context == f"context for question_{i}"

        # All requests must have reached the mock RAG service.
        assert len(received_questions) == number_of_requests
        assert set(received_questions) == {
            f"question_{i}" for i in range(number_of_requests)
        }

        # More than one request must have been active simultaneously.
        assert max_concurrent_requests > 1

        print(f"Total requests: {number_of_requests}")
        print(f"Maximum concurrent requests: {max_concurrent_requests}")

    finally:
        await client.aclose()
        rag_helpers.HttpClientManager._client = None