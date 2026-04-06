"""RAGAS-style evaluation framework for the FraudAI RAG pipeline.

Implements proxy metrics that do NOT require an external LLM judge:
    - Context Precision:  fraction of retrieved contexts that match expected ones.
    - Context Recall:     fraction of expected contexts found in retrieved ones.
    - Faithfulness:       placeholder (0.0) -- requires LLM-as-judge.
    - Answer Relevancy:   placeholder (0.0) -- requires LLM-as-judge.

These proxy metrics are cheap to compute and sufficient for CI gating.
Full RAGAS evaluation (with LLM judge) can be layered on top later
without changing the public interface.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from fraudai.rag.retriever import (  # noqa: TC001 — runtime usage in __init__ and bodies
    LegalRetriever,
    RetrievalResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

_ALL_METRICS = frozenset(
    ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
)


class BenchmarkQuestion(BaseModel):
    """A single benchmark question with ground truth for evaluation."""

    question: str
    """Natural-language question (Spanish)."""

    ground_truth: str
    """Expected correct answer including specific article references."""

    expected_contexts: list[str]
    """Substrings that should appear in retrieved context (e.g. law names, article numbers)."""

    category: str
    """Domain category: 'aml', 'psd2', 'penal', 'rgpd', 'ai_act', etc."""

    difficulty: str = "medium"
    """Difficulty level: 'easy', 'medium', 'hard'."""


class EvaluationResult(BaseModel):
    """Aggregated results of a RAGAS-style evaluation run."""

    metrics: dict[str, float]
    """Aggregate metric values, e.g. {"context_precision": 0.82, ...}."""

    per_question: list[dict[str, Any]]
    """Per-question metric breakdown."""

    category_breakdown: dict[str, dict[str, float]]
    """Metrics grouped by category, e.g. {"aml": {"context_precision": 0.9, ...}}."""

    timestamp: str
    """ISO-8601 timestamp of the evaluation run."""

    corpus_version: str
    """Qdrant corpus version at evaluation time."""

    n_questions: int = Field(default=0)
    """Total number of questions evaluated."""


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class RAGEvaluator:
    """Evaluates RAG retrieval quality using RAGAS-style proxy metrics.

    For MVP, ``faithfulness`` and ``answer_relevancy`` return 0.0 because
    they require an LLM judge.  ``context_precision`` and ``context_recall``
    are computed locally by matching retrieved context text against the
    ``expected_contexts`` substrings declared in each ``BenchmarkQuestion``.
    """

    def __init__(self, retriever: LegalRetriever) -> None:
        self._retriever = retriever

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        benchmark: list[BenchmarkQuestion],
        metrics: list[str] | None = None,
    ) -> EvaluationResult:
        """Run RAGAS evaluation on a benchmark dataset.

        Args:
            benchmark: List of benchmark questions with ground truth.
            metrics:   Subset of metrics to compute.  Defaults to all four.

        Returns:
            ``EvaluationResult`` with aggregate, per-question, and per-category metrics.
        """
        requested = self._resolve_metrics(metrics)
        per_question: list[dict[str, Any]] = []
        category_accum: dict[str, list[dict[str, float]]] = defaultdict(list)

        for bq in benchmark:
            q_metrics = await self.evaluate_single(bq, requested)
            per_question.append(
                {
                    "question": bq.question,
                    "category": bq.category,
                    "difficulty": bq.difficulty,
                    **q_metrics,
                }
            )
            category_accum[bq.category].append(q_metrics)

        # Aggregate metrics (mean across all questions).
        aggregate = self._aggregate(per_question, requested)

        # Category breakdown (mean per category).
        category_breakdown: dict[str, dict[str, float]] = {}
        for cat, entries in category_accum.items():
            category_breakdown[cat] = self._mean_metrics(entries, requested)

        # Corpus version.
        corpus_version = await self._get_corpus_version()

        return EvaluationResult(
            metrics=aggregate,
            per_question=per_question,
            category_breakdown=category_breakdown,
            timestamp=datetime.now(tz=UTC).isoformat(),
            corpus_version=corpus_version,
            n_questions=len(benchmark),
        )

    async def evaluate_single(
        self,
        question: BenchmarkQuestion,
        metrics: frozenset[str] | None = None,
    ) -> dict[str, float]:
        """Evaluate a single benchmark question.

        Args:
            question: The benchmark question to evaluate.
            metrics:  Subset of metrics.  Defaults to all four.

        Returns:
            Dict mapping metric name to score (0.0 -- 1.0).
        """
        requested = metrics or _ALL_METRICS

        # Retrieve contexts via the retriever.
        results: list[RetrievalResult] = await self._retriever.retrieve(question.question)
        retrieved_texts = [r.text for r in results]
        retrieved_meta = [f"{r.norma_titulo} {r.articulo} {r.boe_id}" for r in results]

        scores: dict[str, float] = {}

        if "context_precision" in requested:
            scores["context_precision"] = self._context_precision(
                retrieved_texts, retrieved_meta, question.expected_contexts
            )

        if "context_recall" in requested:
            scores["context_recall"] = self._context_recall(
                retrieved_texts, retrieved_meta, question.expected_contexts
            )

        if "faithfulness" in requested:
            # Placeholder: requires LLM-as-judge to verify answer is grounded in context.
            scores["faithfulness"] = 0.0

        if "answer_relevancy" in requested:
            # Placeholder: requires LLM-as-judge to verify answer addresses the question.
            scores["answer_relevancy"] = 0.0

        return scores

    # ------------------------------------------------------------------
    # Metric implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _context_precision(
        retrieved_texts: list[str],
        retrieved_meta: list[str],
        expected_contexts: list[str],
    ) -> float:
        """Fraction of retrieved documents that contain at least one expected context substring.

        Context Precision = |relevant retrieved| / |retrieved|

        A retrieved document is considered relevant if ANY of the
        ``expected_contexts`` substrings appears (case-insensitive) in
        either its text or its metadata string.
        """
        if not retrieved_texts:
            return 0.0

        relevant_count = 0
        for text, meta in zip(retrieved_texts, retrieved_meta, strict=True):
            combined = f"{text} {meta}".lower()
            if any(ctx.lower() in combined for ctx in expected_contexts):
                relevant_count += 1

        return relevant_count / len(retrieved_texts)

    @staticmethod
    def _context_recall(
        retrieved_texts: list[str],
        retrieved_meta: list[str],
        expected_contexts: list[str],
    ) -> float:
        """Fraction of expected context substrings found in retrieved documents.

        Context Recall = |expected found| / |expected|

        An expected context is considered found if its substring appears
        (case-insensitive) in ANY retrieved document's text or metadata.
        """
        if not expected_contexts:
            return 1.0  # Vacuously true: nothing was expected.

        all_retrieved = " ".join(
            f"{t} {m}" for t, m in zip(retrieved_texts, retrieved_meta, strict=True)
        ).lower()

        found = sum(1 for ctx in expected_contexts if ctx.lower() in all_retrieved)
        return found / len(expected_contexts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_metrics(metrics: list[str] | None) -> frozenset[str]:
        """Validate and resolve the requested metric names."""
        if metrics is None:
            return _ALL_METRICS
        requested = frozenset(metrics)
        unknown = requested - _ALL_METRICS
        if unknown:
            msg = f"Unknown metrics: {unknown}. Valid: {_ALL_METRICS}"
            raise ValueError(msg)
        return requested

    @staticmethod
    def _aggregate(
        per_question: list[dict[str, Any]],
        requested: frozenset[str],
    ) -> dict[str, float]:
        """Compute mean of each metric across all questions."""
        if not per_question:
            return {m: 0.0 for m in sorted(requested)}

        totals: dict[str, float] = defaultdict(float)
        for entry in per_question:
            for metric in requested:
                totals[metric] += entry.get(metric, 0.0)

        n = len(per_question)
        return {m: round(totals[m] / n, 4) for m in sorted(requested)}

    @staticmethod
    def _mean_metrics(
        entries: list[dict[str, float]],
        requested: frozenset[str],
    ) -> dict[str, float]:
        """Compute mean metrics for a list of per-question score dicts."""
        if not entries:
            return {m: 0.0 for m in sorted(requested)}

        totals: dict[str, float] = defaultdict(float)
        for entry in entries:
            for metric in requested:
                totals[metric] += entry.get(metric, 0.0)

        n = len(entries)
        return {m: round(totals[m] / n, 4) for m in sorted(requested)}

    async def _get_corpus_version(self) -> str:
        """Retrieve corpus version from the underlying store, with fallback."""
        try:
            store = self._retriever._store
            version = await store.get_corpus_version()
            return version or "unknown"
        except Exception:
            logger.warning("Could not retrieve corpus version, defaulting to 'unknown'")
            return "unknown"
