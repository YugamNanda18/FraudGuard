"""Tests for the Donna Router intent classifier.

All tests mock httpx so no running Ollama instance is required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fraudai.agents.donna import DonnaRouter, classify_by_keywords


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ollama_response(agent: str, language: str, confidence: float) -> httpx.Response:
    """Build a mock httpx.Response mimicking Ollama /api/chat output."""
    body = {
        "message": {
            "role": "assistant",
            "content": json.dumps(
                {"agent": agent, "language": language, "confidence": confidence}
            ),
        },
        "done": True,
    }
    response = httpx.Response(
        status_code=200,
        json=body,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    return response


def _make_invalid_json_response() -> httpx.Response:
    """Build a mock httpx.Response with non-JSON content."""
    body = {
        "message": {
            "role": "assistant",
            "content": "I cannot parse that request, please try again.",
        },
        "done": True,
    }
    return httpx.Response(
        status_code=200,
        json=body,
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )


# ---------------------------------------------------------------------------
# DonnaRouter.classify -- valid Ollama responses
# ---------------------------------------------------------------------------


class TestClassifyValidResponse:
    """Tests where Ollama returns a well-formed JSON classification."""

    @pytest.mark.parametrize(
        "agent",
        ["harvey", "louis", "jessica", "mike", "rachel"],
    )
    async def test_each_agent_routed(self, agent: str) -> None:
        router = DonnaRouter()
        mock_response = _make_ollama_response(agent, "en", 0.95)

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("test message")

        assert result["agent"] == agent
        assert result["confidence"] == 0.95

    async def test_language_detection_spanish(self) -> None:
        router = DonnaRouter()
        mock_response = _make_ollama_response("harvey", "es", 0.9)

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("Analiza estas transacciones sospechosas")

        assert result["language"] == "es"

    async def test_language_detection_english(self) -> None:
        router = DonnaRouter()
        mock_response = _make_ollama_response("harvey", "en", 0.85)

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("Analyze suspicious transactions")

        assert result["language"] == "en"


# ---------------------------------------------------------------------------
# Low confidence -> agent=None (clarification)
# ---------------------------------------------------------------------------


class TestLowConfidence:
    """When confidence < 0.7, agent should be set to None."""

    async def test_low_confidence_returns_none_agent(self) -> None:
        router = DonnaRouter()
        mock_response = _make_ollama_response("harvey", "es", 0.5)

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("hola")

        assert result["agent"] is None
        assert result["confidence"] == 0.5

    async def test_borderline_confidence_069(self) -> None:
        router = DonnaRouter()
        mock_response = _make_ollama_response("louis", "en", 0.69)

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("something")

        assert result["agent"] is None

    async def test_exactly_070_confidence_routes(self) -> None:
        router = DonnaRouter()
        mock_response = _make_ollama_response("louis", "en", 0.70)

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("something")

        assert result["agent"] == "louis"
        assert result["confidence"] == 0.70


# ---------------------------------------------------------------------------
# Ollama timeout -> keyword fallback
# ---------------------------------------------------------------------------


class TestOllamaTimeout:
    """When Ollama times out, classify should fall back to keywords."""

    async def test_timeout_falls_back_to_keywords(self) -> None:
        router = DonnaRouter()

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("Analiza transacciones de fraude sospechosas")

        # Keyword fallback should pick up fraud-related keywords -> harvey
        assert result["agent"] == "harvey"
        assert result["confidence"] <= 0.75  # keyword cap

    async def test_connect_error_falls_back(self) -> None:
        router = DonnaRouter()

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("Check AML compliance for this customer")

        assert result["agent"] == "louis"


# ---------------------------------------------------------------------------
# Ollama invalid JSON -> keyword fallback
# ---------------------------------------------------------------------------


class TestOllamaInvalidJson:
    """When Ollama returns non-JSON content, keyword fallback kicks in."""

    async def test_invalid_json_falls_back(self) -> None:
        router = DonnaRouter()
        mock_response = _make_invalid_json_response()

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await router.classify("Investigate the network graph and community connections")

        assert result["agent"] == "jessica"

    async def test_invalid_agent_name_falls_back(self) -> None:
        """Ollama returns valid JSON but with an unknown agent name."""
        router = DonnaRouter()
        body = {
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {"agent": "unknown_agent", "language": "en", "confidence": 0.9}
                ),
            },
            "done": True,
        }
        mock_response = httpx.Response(
            status_code=200,
            json=body,
            request=httpx.Request("POST", "http://localhost:11434/api/chat"),
        )

        with patch("fraudai.agents.donna.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            # The ValueError from invalid agent triggers keyword fallback
            result = await router.classify("Run adversarial attack on the model")

        # keyword fallback catches "adversarial" + "attack" -> mike
        assert result["agent"] == "mike"


# ---------------------------------------------------------------------------
# Keyword fallback logic (direct unit tests)
# ---------------------------------------------------------------------------


class TestKeywordFallback:
    """Direct tests for classify_by_keywords()."""

    def test_harvey_keywords(self) -> None:
        result = classify_by_keywords("Detect fraud in these suspicious transactions")
        assert result["agent"] == "harvey"

    def test_louis_keywords(self) -> None:
        result = classify_by_keywords("What are the AML compliance requirements under RGPD?")
        assert result["agent"] == "louis"

    def test_jessica_keywords(self) -> None:
        result = classify_by_keywords("Investigate the network graph and identify communities with typology matching")
        assert result["agent"] == "jessica"

    def test_mike_keywords(self) -> None:
        result = classify_by_keywords("Run a red team adversarial attack on the model")
        assert result["agent"] == "mike"

    def test_rachel_keywords(self) -> None:
        result = classify_by_keywords("Build an ETL pipeline with feature engineering")
        assert result["agent"] == "rachel"

    def test_no_keywords_returns_none(self) -> None:
        result = classify_by_keywords("Hello, how are you today?")
        assert result["agent"] is None
        assert result["confidence"] == 0.0

    def test_spanish_language_detection(self) -> None:
        result = classify_by_keywords(
            "Hola, necesito analizar unas transacciones de fraude por favor"
        )
        assert result["language"] == "es"

    def test_english_language_detection(self) -> None:
        result = classify_by_keywords("Check these fraud transactions for anomalies")
        assert result["language"] == "en"

    def test_confidence_capped_at_075(self) -> None:
        # Many matching keywords should not exceed 0.75
        result = classify_by_keywords(
            "fraud fraud fraud suspicious suspicious anomaly alert detection"
        )
        assert result["confidence"] <= 0.75

    def test_multiple_agents_picks_highest_match(self) -> None:
        # Both harvey (fraud) and louis (compliance) keywords, but more fraud terms
        result = classify_by_keywords(
            "Detect fraud in suspicious transactions with anomaly scoring alerts"
        )
        assert result["agent"] == "harvey"


# ---------------------------------------------------------------------------
# Graph integration: classify_intent_local uses DonnaRouter
# ---------------------------------------------------------------------------


class TestGraphIntegration:
    """Verify classify_intent_local in graph.py delegates to DonnaRouter."""

    async def test_classify_intent_local_delegates(self) -> None:
        from fraudai.agents import graph

        mock_result = {"agent": "jessica", "language": "en", "confidence": 0.92}

        with patch.object(DonnaRouter, "classify", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = mock_result

            # Reset the singleton so _get_donna_router creates a fresh one
            original = graph._donna_router
            graph._donna_router = None
            try:
                result = await graph.classify_intent_local("test")
            finally:
                graph._donna_router = original

        assert result == mock_result
        mock_classify.assert_awaited_once_with("test")
