"""Tests for RAGAS-style evaluation framework — all external calls are mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from fraudai.evaluation.ragas_eval import (
    BenchmarkQuestion,
    EvaluationResult,
    RAGEvaluator,
)
from fraudai.rag.retriever import RetrievalResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_retrieval_result(
    text: str = "Articulo sobre blanqueo",
    score: float = 0.9,
    boe_id: str = "BOE-A-2010-6737",
    norma_titulo: str = "Ley 10/2010",
    articulo: str = "Art. 3",
    collection: str = "boe_legislation",
) -> RetrievalResult:
    """Build a RetrievalResult for tests."""
    return RetrievalResult(
        text=text,
        score=score,
        metadata={
            "boe_id": boe_id,
            "norma_titulo": norma_titulo,
            "articulo": articulo,
            "fecha_publicacion": "2010-04-29",
            "estado_consolidacion": "vigente",
        },
        boe_id=boe_id,
        norma_titulo=norma_titulo,
        articulo=articulo,
        collection=collection,
    )


def _make_benchmark_question(
    question: str = "Pregunta de test?",
    ground_truth: str = "Respuesta de test.",
    expected_contexts: list[str] | None = None,
    category: str = "aml",
    difficulty: str = "easy",
) -> BenchmarkQuestion:
    """Build a BenchmarkQuestion for tests."""
    return BenchmarkQuestion(
        question=question,
        ground_truth=ground_truth,
        expected_contexts=expected_contexts or ["Ley 10/2010", "Art. 3"],
        category=category,
        difficulty=difficulty,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_retriever() -> AsyncMock:
    """Return a mocked LegalRetriever that returns matching results."""
    retriever = AsyncMock()

    # Default: return results that match "Ley 10/2010" and "Art. 3".
    retriever.retrieve.return_value = [
        _make_retrieval_result(
            text="El articulo 3 de la Ley 10/2010 establece la identificacion...",
            norma_titulo="Ley 10/2010",
            articulo="Art. 3",
        ),
        _make_retrieval_result(
            text="Sujetos obligados segun la Ley 10/2010...",
            norma_titulo="Ley 10/2010",
            articulo="Art. 2",
        ),
        _make_retrieval_result(
            text="Contenido no relevante sobre otra norma",
            norma_titulo="Real Decreto 304/2014",
            articulo="Art. 27",
        ),
    ]

    # Mock the store for corpus version.
    mock_store = AsyncMock()
    mock_store.get_corpus_version.return_value = "2026-W14"
    retriever._store = mock_store

    return retriever


@pytest.fixture
def evaluator(mock_retriever: AsyncMock) -> RAGEvaluator:
    """Return a RAGEvaluator wired to a mocked retriever."""
    return RAGEvaluator(retriever=mock_retriever)


# ---------------------------------------------------------------------------
# Tests: evaluate_single
# ---------------------------------------------------------------------------


async def test_evaluate_single_returns_all_metrics(
    evaluator: RAGEvaluator,
) -> None:
    """evaluate_single() should return all four RAGAS metrics."""
    bq = _make_benchmark_question()

    scores = await evaluator.evaluate_single(bq)

    assert "context_precision" in scores
    assert "context_recall" in scores
    assert "faithfulness" in scores
    assert "answer_relevancy" in scores


async def test_evaluate_single_placeholders_are_zero(
    evaluator: RAGEvaluator,
) -> None:
    """Faithfulness and answer_relevancy should be 0.0 (placeholders)."""
    bq = _make_benchmark_question()

    scores = await evaluator.evaluate_single(bq)

    assert scores["faithfulness"] == 0.0
    assert scores["answer_relevancy"] == 0.0


async def test_evaluate_single_calls_retriever(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """evaluate_single() should call retriever.retrieve with the question."""
    bq = _make_benchmark_question(question="Que dice la Ley 10/2010?")

    await evaluator.evaluate_single(bq)

    mock_retriever.retrieve.assert_called_once_with("Que dice la Ley 10/2010?")


# ---------------------------------------------------------------------------
# Tests: context precision
# ---------------------------------------------------------------------------


async def test_context_precision_calculation(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Context precision: fraction of retrieved docs matching expected contexts."""
    # 3 results: 2 match "Ley 10/2010", 1 does not match expected ["Ley 10/2010", "Art. 3"].
    # Result 0: text has "Ley 10/2010" -> match
    # Result 1: norma_titulo has "Ley 10/2010" -> match
    # Result 2: neither text nor meta contains "Ley 10/2010" or "Art. 3"

    mock_retriever.retrieve.return_value = [
        _make_retrieval_result(
            text="Ley 10/2010 articulo sobre identificacion",
            norma_titulo="Ley 10/2010",
            articulo="Art. 3",
        ),
        _make_retrieval_result(
            text="Articulo de diligencia debida",
            norma_titulo="Ley 10/2010",
            articulo="Art. 11",
        ),
        _make_retrieval_result(
            text="Normativa europea sobre pagos",
            norma_titulo="Directiva 2015/2366",
            articulo="Art. 98",
        ),
    ]

    bq = _make_benchmark_question(expected_contexts=["Ley 10/2010", "Art. 3"])
    scores = await evaluator.evaluate_single(bq)

    # Result 0: matches both "Ley 10/2010" and "Art. 3" -> relevant
    # Result 1: matches "Ley 10/2010" -> relevant
    # Result 2: matches neither -> not relevant
    # Precision = 2/3
    assert scores["context_precision"] == pytest.approx(2.0 / 3.0)


async def test_context_precision_all_relevant(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Context precision should be 1.0 when all retrieved docs are relevant."""
    mock_retriever.retrieve.return_value = [
        _make_retrieval_result(norma_titulo="Ley 10/2010", articulo="Art. 3"),
        _make_retrieval_result(norma_titulo="Ley 10/2010", articulo="Art. 11"),
    ]

    bq = _make_benchmark_question(expected_contexts=["Ley 10/2010"])
    scores = await evaluator.evaluate_single(bq)

    assert scores["context_precision"] == 1.0


async def test_context_precision_empty_retrieval(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Context precision should be 0.0 when no results are retrieved."""
    mock_retriever.retrieve.return_value = []

    bq = _make_benchmark_question()
    scores = await evaluator.evaluate_single(bq)

    assert scores["context_precision"] == 0.0


# ---------------------------------------------------------------------------
# Tests: context recall
# ---------------------------------------------------------------------------


async def test_context_recall_calculation(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Context recall: fraction of expected contexts found in retrieval."""
    mock_retriever.retrieve.return_value = [
        _make_retrieval_result(norma_titulo="Ley 10/2010", articulo="Art. 3"),
    ]

    bq = _make_benchmark_question(expected_contexts=["Ley 10/2010", "Art. 3", "Art. 18"])
    scores = await evaluator.evaluate_single(bq)

    # "Ley 10/2010" found, "Art. 3" found, "Art. 18" NOT found
    # Recall = 2/3
    assert scores["context_recall"] == pytest.approx(2.0 / 3.0)


async def test_context_recall_all_found(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Context recall should be 1.0 when all expected contexts are found."""
    mock_retriever.retrieve.return_value = [
        _make_retrieval_result(
            text="Ley 10/2010 art 3 sobre identificacion",
            norma_titulo="Ley 10/2010",
            articulo="Art. 3",
        ),
    ]

    bq = _make_benchmark_question(expected_contexts=["Ley 10/2010", "Art. 3"])
    scores = await evaluator.evaluate_single(bq)

    assert scores["context_recall"] == 1.0


async def test_context_recall_empty_expected(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Context recall should be 1.0 when expected_contexts is empty (vacuously true)."""
    bq = _make_benchmark_question(expected_contexts=[])
    scores = await evaluator.evaluate_single(bq)

    assert scores["context_recall"] == 1.0


async def test_context_recall_case_insensitive(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Context recall matching should be case-insensitive."""
    mock_retriever.retrieve.return_value = [
        _make_retrieval_result(
            text="LEY 10/2010 sobre blanqueo",
            norma_titulo="LEY 10/2010",
            articulo="ART. 3",
        ),
    ]

    bq = _make_benchmark_question(expected_contexts=["ley 10/2010", "art. 3"])
    scores = await evaluator.evaluate_single(bq)

    assert scores["context_recall"] == 1.0


# ---------------------------------------------------------------------------
# Tests: evaluate (full benchmark)
# ---------------------------------------------------------------------------


async def test_evaluate_returns_evaluation_result(
    evaluator: RAGEvaluator,
) -> None:
    """evaluate() should return an EvaluationResult with all fields populated."""
    benchmark = [
        _make_benchmark_question(category="aml", difficulty="easy"),
        _make_benchmark_question(category="aml", difficulty="medium"),
        _make_benchmark_question(category="penal", difficulty="easy"),
    ]

    result = await evaluator.evaluate(benchmark)

    assert isinstance(result, EvaluationResult)
    assert result.n_questions == 3
    assert result.corpus_version == "2026-W14"
    assert result.timestamp  # Non-empty ISO timestamp.
    assert len(result.per_question) == 3
    assert "context_precision" in result.metrics
    assert "context_recall" in result.metrics


async def test_evaluate_per_question_has_metadata(
    evaluator: RAGEvaluator,
) -> None:
    """per_question entries should include question text, category, and difficulty."""
    benchmark = [
        _make_benchmark_question(question="Test AML?", category="aml", difficulty="hard"),
    ]

    result = await evaluator.evaluate(benchmark)

    entry = result.per_question[0]
    assert entry["question"] == "Test AML?"
    assert entry["category"] == "aml"
    assert entry["difficulty"] == "hard"


# ---------------------------------------------------------------------------
# Tests: category_breakdown
# ---------------------------------------------------------------------------


async def test_category_breakdown_correct(
    evaluator: RAGEvaluator,
) -> None:
    """category_breakdown should group metrics by category."""
    benchmark = [
        _make_benchmark_question(category="aml"),
        _make_benchmark_question(category="aml"),
        _make_benchmark_question(category="penal"),
    ]

    result = await evaluator.evaluate(benchmark)

    assert "aml" in result.category_breakdown
    assert "penal" in result.category_breakdown
    assert "context_precision" in result.category_breakdown["aml"]
    assert "context_recall" in result.category_breakdown["penal"]


async def test_category_breakdown_independent_averages(
    evaluator: RAGEvaluator,
    mock_retriever: AsyncMock,
) -> None:
    """Each category should have independently computed metric averages."""
    # AML questions get perfect retrieval.
    aml_results = [
        _make_retrieval_result(norma_titulo="Ley 10/2010", articulo="Art. 3"),
    ]
    # Penal questions get no matching retrieval.
    penal_results = [
        _make_retrieval_result(
            text="Unrelated content",
            norma_titulo="Otra norma",
            articulo="Art. 99",
        ),
    ]

    call_count = 0

    async def side_effect(query: str, **kwargs: Any) -> list[RetrievalResult]:
        nonlocal call_count
        call_count += 1
        # First two calls are AML, third is Penal.
        if call_count <= 2:
            return aml_results
        return penal_results

    mock_retriever.retrieve.side_effect = side_effect

    benchmark = [
        _make_benchmark_question(category="aml", expected_contexts=["Ley 10/2010"]),
        _make_benchmark_question(category="aml", expected_contexts=["Ley 10/2010"]),
        _make_benchmark_question(category="penal", expected_contexts=["Codigo Penal"]),
    ]

    result = await evaluator.evaluate(benchmark)

    # AML should have perfect precision and recall.
    assert result.category_breakdown["aml"]["context_precision"] == 1.0
    assert result.category_breakdown["aml"]["context_recall"] == 1.0

    # Penal should have zero precision and recall (no match).
    assert result.category_breakdown["penal"]["context_precision"] == 0.0
    assert result.category_breakdown["penal"]["context_recall"] == 0.0


# ---------------------------------------------------------------------------
# Tests: metric selection
# ---------------------------------------------------------------------------


async def test_evaluate_single_selected_metrics(
    evaluator: RAGEvaluator,
) -> None:
    """evaluate_single() with explicit metrics should only return those."""
    bq = _make_benchmark_question()
    requested = frozenset(["context_precision"])

    scores = await evaluator.evaluate_single(bq, metrics=requested)

    assert "context_precision" in scores
    assert "context_recall" not in scores
    assert "faithfulness" not in scores


async def test_evaluate_invalid_metric_raises(
    evaluator: RAGEvaluator,
) -> None:
    """evaluate() with an unknown metric name should raise ValueError."""
    benchmark = [_make_benchmark_question()]

    with pytest.raises(ValueError, match="Unknown metrics"):
        await evaluator.evaluate(benchmark, metrics=["nonexistent_metric"])


# ---------------------------------------------------------------------------
# Tests: corpus version fallback
# ---------------------------------------------------------------------------


async def test_corpus_version_fallback_on_error(
    mock_retriever: AsyncMock,
) -> None:
    """If corpus version lookup fails, result should show 'unknown'."""
    mock_retriever._store.get_corpus_version.side_effect = RuntimeError("connection lost")
    evaluator = RAGEvaluator(retriever=mock_retriever)

    benchmark = [_make_benchmark_question()]
    result = await evaluator.evaluate(benchmark)

    assert result.corpus_version == "unknown"


async def test_corpus_version_none_returns_unknown(
    mock_retriever: AsyncMock,
) -> None:
    """If corpus version is None, result should show 'unknown'."""
    mock_retriever._store.get_corpus_version.return_value = None
    evaluator = RAGEvaluator(retriever=mock_retriever)

    benchmark = [_make_benchmark_question()]
    result = await evaluator.evaluate(benchmark)

    assert result.corpus_version == "unknown"


# ---------------------------------------------------------------------------
# Tests: empty benchmark
# ---------------------------------------------------------------------------


async def test_evaluate_empty_benchmark(
    evaluator: RAGEvaluator,
) -> None:
    """evaluate() with empty benchmark should return zero metrics."""
    result = await evaluator.evaluate([])

    assert result.n_questions == 0
    assert result.metrics["context_precision"] == 0.0
    assert result.per_question == []
    assert result.category_breakdown == {}
