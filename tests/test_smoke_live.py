"""Live smoke tests against a running FraudAI Agent backend.

Run with: pytest tests/test_smoke_live.py -v --timeout=60

Requires:
- Backend running on http://localhost:8000
- Qdrant running on http://localhost:6333
- GROQ_API_KEY configured in .env

These tests hit the REAL backend (no mocks). They are excluded from
the standard CI suite and run separately via:
  make smoke-test
  ./scripts/smoke-test.sh
"""

from __future__ import annotations

import os

import httpx
import pytest

BASE_URL = os.getenv("FRAUDAI_BASE_URL", "http://localhost:8000/api/v1")
AUTH_HEADER = {"Authorization": "Bearer dev-token"}
TIMEOUT = 30.0


def _is_backend_running() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", headers=AUTH_HEADER, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _is_backend_running(),
    reason="Backend not running — skip live smoke tests",
)


def _chat(message: str, session_id: str | None = None, agent_override: str | None = None) -> dict:
    body: dict = {"message": message, "language": "es"}
    if session_id:
        body["session_id"] = session_id
    if agent_override:
        body["agent_override"] = agent_override
    r = httpx.post(
        f"{BASE_URL}/chat",
        headers={**AUTH_HEADER, "Content-Type": "application/json"},
        json=body,
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, f"Chat failed: {r.status_code} {r.text[:200]}"
    return r.json()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_200(self) -> None:
        r = httpx.get(f"{BASE_URL}/health", headers=AUTH_HEADER, timeout=10)
        assert r.status_code == 200

    def test_health_has_qdrant(self) -> None:
        r = httpx.get(f"{BASE_URL}/health", headers=AUTH_HEADER, timeout=10)
        data = r.json()
        assert data["qdrant"] is True

    def test_health_has_llm(self) -> None:
        r = httpx.get(f"{BASE_URL}/health", headers=AUTH_HEADER, timeout=10)
        data = r.json()
        assert data["claude_api"] is True


# ---------------------------------------------------------------------------
# Donna (Router)
# ---------------------------------------------------------------------------


class TestDonnaRouter:
    def test_hola_routes_to_donna(self) -> None:
        data = _chat("Hola")
        assert data["agent"] == "donna"
        assert "Harvey Specter" in data["message"]

    def test_donna_latency_under_2s(self) -> None:
        data = _chat("Hola")
        assert data["metadata"]["latency_ms"] < 2000


# ---------------------------------------------------------------------------
# Harvey (Transaction Fraud)
# ---------------------------------------------------------------------------


class TestHarvey:
    def test_estafa_routes_to_harvey(self) -> None:
        data = _chat("Me han estafado en una escuela de formacion")
        assert data["agent"] == "harvey"
        assert len(data["message"]) > 50

    def test_transacciones_routes_to_harvey(self) -> None:
        data = _chat("Necesito analizar transacciones sospechosas de fraude bancario")
        assert data["agent"] == "harvey"

    def test_harvey_asks_questions(self) -> None:
        data = _chat("Me han estafado")
        assert data["agent"] == "harvey"
        assert "?" in data["message"], "Harvey should ask clarifying questions"


# ---------------------------------------------------------------------------
# Louis (AML / KYC / Compliance)
# ---------------------------------------------------------------------------


class TestLouis:
    def test_ley_routes_to_louis(self) -> None:
        data = _chat("Que dice la ley 10/2010 sobre blanqueo de capitales?")
        assert data["agent"] == "louis"
        assert len(data["message"]) > 100

    def test_compliance_routes_to_louis(self) -> None:
        data = _chat("Necesito un checklist de cumplimiento AML")
        assert data["agent"] == "louis"

    def test_louis_cites_articles(self) -> None:
        data = _chat("Que dice la normativa sobre blanqueo?")
        assert data["agent"] == "louis"
        msg = data["message"].lower()
        assert any(w in msg for w in ["art.", "artículo", "articulo", "ley"]), \
            "Louis should cite legal articles"


# ---------------------------------------------------------------------------
# Jessica (Fraud Intelligence)
# ---------------------------------------------------------------------------


class TestJessica:
    def test_grafos_routes_to_jessica(self) -> None:
        data = _chat("Necesito investigar una red de fraude con analisis de grafos")
        assert data["agent"] == "jessica"


# ---------------------------------------------------------------------------
# Mike (Red Teaming)
# ---------------------------------------------------------------------------


class TestMike:
    def test_pentest_routes_to_mike(self) -> None:
        data = _chat("Necesito hacer un pentest adversarial a mi modelo de IA")
        assert data["agent"] == "mike"


# ---------------------------------------------------------------------------
# Rachel (Data Engineering)
# ---------------------------------------------------------------------------


class TestRachel:
    def test_pipeline_routes_to_rachel(self) -> None:
        data = _chat("Necesito un pipeline ETL para datos de fraude con pandas y csv")
        assert data["agent"] == "rachel"


# ---------------------------------------------------------------------------
# Agent Override
# ---------------------------------------------------------------------------


class TestAgentOverride:
    def test_override_to_louis(self) -> None:
        data = _chat("Me han robado dinero", agent_override="louis")
        assert data["agent"] == "louis"

    def test_override_to_harvey(self) -> None:
        data = _chat("Que dice la ley?", agent_override="harvey")
        assert data["agent"] == "harvey"


# ---------------------------------------------------------------------------
# Conversational Continuity
# ---------------------------------------------------------------------------


class TestConversationalContinuity:
    def test_followup_stays_with_agent(self) -> None:
        r1 = _chat("Que dice la normativa sobre proteccion de datos?")
        assert r1["agent"] == "louis"
        sid = r1["session_id"]

        r2 = _chat("Y en el ambito financiero?", session_id=sid)
        assert r2["agent"] == "louis", \
            f"Follow-up should stay with louis, got {r2['agent']}"

    def test_topic_change_reroutes(self) -> None:
        r1 = _chat("Que dice la ley sobre blanqueo?")
        sid = r1["session_id"]

        r2 = _chat("Necesito analizar transacciones sospechosas de fraude", session_id=sid)
        assert r2["agent"] == "harvey", \
            f"Topic change should reroute to harvey, got {r2['agent']}"


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------


class TestSessions:
    def test_new_session_created(self) -> None:
        data = _chat("Hola")
        assert "session_id" in data
        assert len(data["session_id"]) > 10

    def test_session_info(self) -> None:
        data = _chat("Hola")
        sid = data["session_id"]
        r = httpx.get(
            f"{BASE_URL}/sessions/{sid}",
            headers=AUTH_HEADER,
            timeout=10,
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Response Quality
# ---------------------------------------------------------------------------


class TestResponseQuality:
    def test_no_empty_responses(self) -> None:
        data = _chat("Me han estafado en una empresa")
        assert len(data["message"]) > 20, "Response should not be empty"

    def test_metadata_present(self) -> None:
        data = _chat("Hola")
        assert "metadata" in data
        assert "routing_agent" in data["metadata"]
        assert "latency_ms" in data["metadata"]

    def test_no_english_disclaimers(self) -> None:
        data = _chat("Me han estafado")
        msg = data["message"].lower()
        assert "i'm not a lawyer" not in msg
        assert "i cannot provide legal" not in msg
        assert "consult a professional" not in msg
