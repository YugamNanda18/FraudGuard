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
            r"(?i)\b(?:fraude|fraud|transacci|transaction|anomal|riesgo|risk|"
            r"scoring|sospech|suspicious|alerta|alert|detection|detectar)\b"
        ),
    ),
    (
        "louis",
        re.compile(
            r"(?i)\b(?:compliance|cumplimiento|aml|kyc|psd2|rgpd|gdpr|"
            r"regulaci|regulation|blanqueo|laundering|sar|str|sepblac|"
            r"normativa|legal|ley|law|art[i\u00ed]culo|article)\b"
        ),
    ),
    (
        "jessica",
        re.compile(
            r"(?i)\b(?:red\s+de\s+fraude|fraud\s+network|grafo|graph|"
            r"network|investigaci|investigation|identidad|identity|"
            r"fatf|gafi|tipolog|typolog|comunidad|community)\b"
        ),
    ),
    (
        "mike",
        re.compile(
            r"(?i)\b(?:red\s+team|adversar|evasion|evasi\u00f3n|prompt\s+injection|"
            r"ataque|attack|seguridad\s+ia|ai\s+security|pentest|"
            r"vulnerabilid|vulnerability|robustez|robustness)\b"
        ),
    ),
    (
        "rachel",
        re.compile(
            r"(?i)\b(?:etl|pipeline|feature|ingenier.a\s+de\s+datos|"
            r"data\s+engineer|calidad\s+de\s+datos|data\s+quality|"
            r"esquema|schema|parquet|csv|polars|pandas)\b"
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
    """Intent classifier using local Ollama model for routing."""

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "llama3.1:8b-instruct-q4_K_M",
    ) -> None:
        self._ollama_host = ollama_host.rstrip("/")
        self._model = model
        self._timeout = 5.0

    async def classify(self, message: str) -> IntentClassification:
        """Classify user intent and detect language.

        Calls Ollama with JSON mode for structured output. Falls back to
        keyword-based classification on timeout or invalid response.

        Returns:
            IntentClassification with agent, language, and confidence.
            Agent is None when confidence < 0.7 (triggers clarification).
        """
        try:
            result = await self._call_ollama(message)
            return result
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning("Ollama unreachable (%s), falling back to keywords", type(exc).__name__)
            return classify_by_keywords(message)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(
                "Ollama returned invalid response (%s: %s), falling back to keywords",
                type(exc).__name__,
                exc,
            )
            return classify_by_keywords(message)

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
