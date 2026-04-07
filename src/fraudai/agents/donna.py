"""Donna Router -- Intent classifier using local Ollama model.

Routes user messages to the appropriate specialist agent using
Llama 3.1 8B via the Ollama REST API. Falls back to keyword-based
classification when Ollama is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, TypedDict

import httpx

from fraudai.core.metrics import AGENT_LATENCY, ROUTING_ACCURACY


class IntentClassification(TypedDict):
    """Return contract for intent classification.

    Defined here (not in graph.py) to avoid circular imports, since
    graph.py imports DonnaRouter from this module.
    """

    agent: str  # "harvey" | "louis" | "jessica" | "mike" | "rachel" | None
    language: str  # "es" | "en"
    confidence: float  # 0.0 - 1.0


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM_PROMPT = """\
You are a routing classifier for a banking fraud detection platform. \
Your ONLY job is to read the user message and return a JSON object \
classifying the intent.

## Agents
- harvey: Transaction fraud analysis, anomaly detection, risk scoring, detection rules.
- louis: AML/KYC/PSD2/RGPD compliance, regulatory questions, SAR/STR reports.
- jessica: Fraud network investigation, graph analysis, identity resolution, FATF typologies.
- mike: AI red teaming, adversarial attacks on ML models, prompt injection testing, AI governance.
- rachel: Data engineering, ETL pipelines, feature engineering, data quality, schema design.

## Rules
1. Classify the PRIMARY intent into exactly one agent.
2. Detect the language of the message: "es" for Spanish, "en" for English.
3. Set confidence between 0.0 and 1.0. Use < 0.7 if ambiguous.
4. Return ONLY valid JSON. No extra text.

## Output format
{"agent": "<harvey|louis|jessica|mike|rachel>", "language": "<es|en>", "confidence": <float>}
"""

# ---------------------------------------------------------------------------
# Keyword fallback patterns
# ---------------------------------------------------------------------------

_KEYWORD_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "harvey",
        re.compile(
            r"(?i)\b(?:fraud\w*|estaf\w*|scam\w*|transacci\w*|transaction\w*|"
            r"anomal\w*|riesgo\w*|risk\w*|scoring|sospech\w*|suspicious|"
            r"alerta\w*|alert\w*|detect\w*|rob[oa]\w*|theft|tarjeta\w*|"
            r"card\w*|skimming|phishing|pago\w*|payment\w*|transferencia\w*|"
            r"transfer\w*|cuenta\w*|account\w*|operaci\w*|dinero\w*|money|"
            r"timo\w*|engaño\w*|ilegal\w*|ilícit\w*)"
        ),
    ),
    (
        "louis",
        re.compile(
            r"(?i)\b(?:compliance|cumplimient\w*|aml|kyc|psd2|rgpd|gdpr|"
            r"regulaci\w*|regulation\w*|blanque\w*|laundering|sar|str|sepblac|"
            r"normativ\w*|legal\w*|ley\w*|law|art[ií]culo\w*|article\w*|"
            r"denunci\w*|penal\w*|sanci[oó]n\w*|sanction\w*|multa\w*|fine|"
            r"reclamaci\w*|complaint\w*|contrat\w*|obligaci\w*|derecho\w*|"
            r"right\w*|tribunal\w*|juzgado\w*|court|abogad\w*|lawyer\w*|"
            r"defens\w*|protecci\w*|consumidor\w*|consumer\w*)"
        ),
    ),
    (
        "jessica",
        re.compile(
            r"(?i)\b(?:red\s+de\s+fraude|fraud\s+network|grafo\w*|graph\w*|"
            r"network\w*|investigaci\w*|investigation\w*|identidad\w*|identity\w*|"
            r"fatf|gafi|tipolog\w*|typolog\w*|comunidad\w*|community\w*|"
            r"mula\w*|relacion\w*|v[ií]ncul\w*|link\w*|conexi\w*|patr[oó]n\w*)"
        ),
    ),
    (
        "mike",
        re.compile(
            r"(?i)\b(?:red\s+team\w*|adversar\w*|evasi[oó]n\w*|evasion\w*|"
            r"prompt\s+injection|ataque\w*|attack\w*|seguridad\s+ia|"
            r"ai\s+security|pentest\w*|vulnerabilid\w*|vulnerability\w*|"
            r"robustez|robustness|modelo\s+ml|hacker?\w*|exploit\w*|inyecci\w*)"
        ),
    ),
    (
        "rachel",
        re.compile(
            r"(?i)\b(?:etl|pipeline\w*|feature\w*|ingenier.a\s+de\s+datos|"
            r"data\s+engineer\w*|calidad\s+de\s+datos|data\s+quality|"
            r"esquema\w*|schema\w*|parquet|csv|polars|pandas|"
            r"base\s+de\s+datos|database\w*|column\w*|tabla\w*|table\w*)"
        ),
    ),
]

_LANGUAGE_PATTERN_ES = re.compile(
    r"(?i)\b(?:hola|necesito|quiero|analizar|transacciones|"
    r"por\s+favor|gracias|ayuda|puedes|el|la|los|las|un|una|"
    r"del|al|es|est[a\u00e1]|son|tiene|c[o\u00f3]mo)\b"
)


# ---------------------------------------------------------------------------
# Keyword fallback
# ---------------------------------------------------------------------------


def classify_by_keywords(message: str) -> IntentClassification:
    """Classify intent using regex keyword matching.

    Used as a fallback when Ollama is unavailable or returns invalid data.
    Returns agent=None (mapped to clarification) when no pattern matches.
    """
    scores: dict[str, int] = {}
    for agent_name, pattern in _KEYWORD_PATTERNS:
        matches = pattern.findall(message)
        if matches:
            scores[agent_name] = len(matches)

    # Detect language
    es_matches = len(_LANGUAGE_PATTERN_ES.findall(message))
    language = "es" if es_matches >= 2 else "en"

    if not scores:
        logger.info("Keyword fallback: no pattern matched, requesting clarification")
        return {"agent": None, "language": language, "confidence": 0.0}  # type: ignore[typeddict-item]

    # Boost Mike for adversarial/security context (often overlaps with Harvey)
    if "mike" in scores and any(
        w in message.lower()
        for w in ("adversar", "red team", "prompt injection", "pentest", "vulnerab", "exploit")
    ):
        scores["mike"] = scores.get("mike", 0) + 3

    best_agent = max(scores, key=scores.get)  # type: ignore[arg-type]
    # Keyword confidence caps at 0.75 -- it is a heuristic, not LLM-grade
    confidence = min(0.75, 0.5 + 0.05 * scores[best_agent])

    logger.info(
        "Keyword fallback: routed to %s (confidence=%.2f, matches=%d)",
        best_agent,
        confidence,
        scores[best_agent],
    )
    return {"agent": best_agent, "language": language, "confidence": confidence}


# ---------------------------------------------------------------------------
# DonnaRouter
# ---------------------------------------------------------------------------


class DonnaRouter:
    """Intent classifier using local Ollama model for routing.

    Classification strategy (ordered by priority):
    1. Keyword-based (instant, ~0ms) -- used when keywords match clearly.
    2. Groq API (fast, ~200ms) -- used for ambiguous messages when key is set.
    3. Ollama local (slower, ~2-10s) -- fallback when Groq is unavailable.
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "llama3.1:8b-instruct-q4_K_M",
        groq_api_key: str | None = None,
        groq_model: str | None = None,
    ) -> None:
        self._ollama_host = ollama_host.rstrip("/")
        self._model = model
        self._groq_api_key = groq_api_key or None
        self._groq_model = groq_model or "llama-3.3-70b-versatile"
        self._timeout = 10.0

    async def classify(self, message: str) -> IntentClassification:
        """Classify user intent and detect language.

        Strategy:
        1. Fast keyword classification first (< 1ms)
        2. If keywords match with confidence >= 0.5, use that result
        3. If ambiguous, try Ollama for LLM-based classification
        4. Ollama timeout/error falls back to keyword result

        Returns:
            IntentClassification with agent, language, and confidence.
            Agent is None when confidence < 0.7 (triggers clarification).
        """
        import time as _time

        start = _time.monotonic()
        result: IntentClassification | None = None

        # Step 1: Always try keywords first (instant)
        keyword_result = classify_by_keywords(message)

        # Step 2: If keywords matched, use them directly
        if keyword_result.get("agent") is not None:
            result = keyword_result
            return result

        # Step 3: Keywords didn't match — try Groq API for fast LLM classification
        if self._groq_api_key:
            try:
                result = await self._call_groq(message)
                return result
            except Exception as exc:
                logger.warning(
                    "Groq classification failed (%s: %s), trying Ollama",
                    type(exc).__name__,
                    exc,
                )

        # Step 4: Ollama fallback for ambiguous messages
        try:
            result = await self._call_ollama(message)
            return result
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            logger.warning("Ollama error (%s: %s), using keyword result", type(exc).__name__, exc)
            result = keyword_result
            return result
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Ollama returned invalid response (%s: %s), falling back to keywords",
                type(exc).__name__,
                exc,
            )
            result = classify_by_keywords(message)
            return result
        finally:
            duration = _time.monotonic() - start
            AGENT_LATENCY.labels(agent_name="donna").observe(duration)
            if result is not None:
                self._record_routing(result)

    @staticmethod
    def _record_routing(result: IntentClassification) -> None:
        """Record a routing decision in Prometheus metrics."""
        confidence = result.get("confidence", 0.0)
        if confidence >= 0.85:
            bucket = "high"
        elif confidence >= 0.7:
            bucket = "medium"
        else:
            bucket = "low"
        target = result.get("agent") or "clarify"
        ROUTING_ACCURACY.labels(target_agent=target, confidence_bucket=bucket).inc()

    async def _call_ollama(self, message: str) -> IntentClassification:
        """Send classification request to Ollama and parse response."""
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 100,
            },
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._ollama_host}/api/chat",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content = data["message"]["content"]
        parsed = json.loads(content)

        return self._validate_classification(parsed)

    async def _call_groq(self, message: str) -> IntentClassification:
        """Send classification request to Groq API and parse response.

        Uses the OpenAI-compatible chat completions endpoint with JSON mode.
        Timeout is tight (5s) since Groq is designed for low-latency inference.
        """
        payload: dict[str, Any] = {
            "model": self._groq_model,
            "messages": [
                {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 100,
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._groq_api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        logger.info("Groq classification succeeded (model=%s)", self._groq_model)
        return self._validate_classification(parsed)

    def _validate_classification(self, raw: dict[str, Any]) -> IntentClassification:
        """Validate and normalize the LLM classification output.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are outside valid ranges.
        """
        valid_agents = {"harvey", "louis", "jessica", "mike", "rachel"}
        valid_languages = {"es", "en"}

        agent = str(raw["agent"]).lower().strip()
        if agent not in valid_agents:
            raise ValueError(f"Invalid agent: {agent!r}")

        language = str(raw.get("language", "es")).lower().strip()
        if language not in valid_languages:
            language = "es"

        try:
            confidence = float(raw.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        # Low confidence triggers clarification
        if confidence < 0.7:
            logger.info(
                "Low confidence %.2f for agent=%s, requesting clarification",
                confidence,
                agent,
            )
            return {"agent": None, "language": language, "confidence": confidence}  # type: ignore[typeddict-item]

        logger.info(
            "Classified intent: agent=%s, language=%s, confidence=%.2f",
            agent,
            language,
            confidence,
        )
        return {"agent": agent, "language": language, "confidence": confidence}
