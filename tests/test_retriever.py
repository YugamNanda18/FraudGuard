"""Tests for LegalRetriever and Reranker — all external calls are mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fraudai.rag.reranker import Reranker
from fraudai.rag.retriever import LegalRetriever, RetrievalResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_result(
    idx: int = 0,
    text: str = "Article text",
    score: float = 0.9,
    boe_id: str = "BOE-A-2010-6737",
    norma_titulo: str = "Ley 10/2010, de 28 de abril",
    articulo: str = "Art. 18",
) -> dict[str, Any]:
    """Build a raw result dict as returned by QdrantStore.hybrid_search."""
    return {
        "id": f"point-{idx}",
        "score": score,
        "payload": {
            "text": text,
            "boe_id": boe_id,
            "norma_titulo": norma_titulo,
            "articulo": articulo,
            "fecha_publicacion": "2010-04-29",
            "fecha_consolidacion": "2025-12-01",
            "estado_consolidacion": "vigente",
        },
    }


def _make_retrieval_result(
    idx: int = 0,
    text: str = "Article text",
    score: float = 0.9,
    boe_id: str = "BOE-A-2010-6737",
    norma_titulo: str = "Ley 10/2010, de 28 de abril",
    articulo: str = "Art. 18",
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
            "fecha_consolidacion": "2025-12-01",
            "estado_consolidacion": "vigente",
        },
        boe_id=boe_id,
        norma_titulo=norma_titulo,
        articulo=articulo,
        collection=collection,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_store() -> AsyncMock:
    """Return a mocked QdrantStore."""
    store = AsyncMock()
    store.BOE_COLLECTION = "boe_legislation"
    store.hybrid_search.return_value = [
        _make_raw_result(idx=0, score=0.9, text="Result 0"),
        _make_raw_result(idx=1, score=0.8, text="Result 1"),
        _make_raw_result(idx=2, score=0.7, text="Result 2"),
    ]
    return store


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Return a mocked EmbeddingGenerator."""
    embedder = MagicMock()
    embedder.encode.return_value = [
        {
            "dense": [0.1] * 1024,
            "sparse": {"indices": [1, 5, 10], "values": [0.8, 0.5, 0.3]},
        },
    ]
    return embedder


@pytest.fixture
def retriever(mock_store: AsyncMock, mock_embedder: MagicMock) -> LegalRetriever:
    """Return a LegalRetriever wired to mocked dependencies."""
    return LegalRetriever(
        store=mock_store,
        embedder=mock_embedder,
        reranker=None,
        default_k=10,
        rerank_k=20,
    )


@pytest.fixture
def mock_reranker() -> MagicMock:
    """Return a mocked Reranker."""
    reranker = MagicMock(spec=Reranker)
    # rerank returns a reordered subset.
    reranker.rerank.side_effect = lambda query, docs, top_k: list(reversed(docs[:top_k]))
    return reranker


@pytest.fixture
def retriever_with_reranker(
    mock_store: AsyncMock,
    mock_embedder: MagicMock,
    mock_reranker: MagicMock,
) -> LegalRetriever:
    """Return a LegalRetriever with reranker enabled."""
    return LegalRetriever(
        store=mock_store,
        embedder=mock_embedder,
        reranker=mock_reranker,
        default_k=10,
        rerank_k=20,
    )


# ---------------------------------------------------------------------------
# Tests: retrieve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_returns_results(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
    mock_embedder: MagicMock,
) -> None:
    """retrieve() should encode query, call hybrid_search, and return results."""
    results = await retriever.retrieve("blanqueo de capitales")

    assert len(results) == 3
    mock_embedder.encode.assert_called_once_with(["blanqueo de capitales"])
    mock_store.hybrid_search.assert_called_once()

    # Verify the search was called with correct vectors.
    call_kwargs = mock_store.hybrid_search.call_args.kwargs
    assert call_kwargs["collection"] == "boe_legislation"
    assert len(call_kwargs["dense_vector"]) == 1024
    assert call_kwargs["sparse_vector"] is not None


@pytest.mark.asyncio
async def test_retrieve_respects_k(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """retrieve() should limit results to the specified k."""
    results = await retriever.retrieve("test query", k=2)

    assert len(results) == 2


@pytest.mark.asyncio
async def test_retrieve_passes_collection(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """retrieve() should forward collection parameter to store."""
    await retriever.retrieve("query", collection="eu_regulation")

    call_kwargs = mock_store.hybrid_search.call_args.kwargs
    assert call_kwargs["collection"] == "eu_regulation"


@pytest.mark.asyncio
async def test_retrieve_passes_filters(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """retrieve() should forward metadata filters to store."""
    filters = {"estado_consolidacion": "vigente"}
    await retriever.retrieve("query", filters=filters)

    call_kwargs = mock_store.hybrid_search.call_args.kwargs
    assert call_kwargs["filters"] == filters


@pytest.mark.asyncio
async def test_retrieve_empty_results(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """retrieve() should handle empty search results gracefully."""
    mock_store.hybrid_search.return_value = []

    results = await retriever.retrieve("nonexistent topic")

    assert results == []


# ---------------------------------------------------------------------------
# Tests: retrieve with reranker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_with_reranker_fetches_more(
    retriever_with_reranker: LegalRetriever,
    mock_store: AsyncMock,
    mock_reranker: MagicMock,
) -> None:
    """When reranker is enabled, hybrid_search should fetch rerank_k results."""
    await retriever_with_reranker.retrieve("query", k=2)

    call_kwargs = mock_store.hybrid_search.call_args.kwargs
    # Should use rerank_k (20) as the search limit, not final k (2).
    assert call_kwargs["limit"] == 20

    # Reranker should be called with all raw results and top_k=2.
    mock_reranker.rerank.assert_called_once()
    rerank_call = mock_reranker.rerank.call_args
    # top_k is passed as the third positional argument
    assert rerank_call.args[2] == 2


@pytest.mark.asyncio
async def test_retrieve_reranker_reorders_results(
    retriever_with_reranker: LegalRetriever,
    mock_reranker: MagicMock,
) -> None:
    """Reranker should change the order of results."""
    results = await retriever_with_reranker.retrieve("query", k=3)

    # Our mock reranker reverses the order.
    assert results[0].text == "Result 2"
    assert results[2].text == "Result 0"


# ---------------------------------------------------------------------------
# Tests: retrieve_for_agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_for_agent_louis_uses_k20(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """Louis should retrieve k=20 results (exhaustive legal citations)."""
    # Provide enough raw results to fill k=20.
    mock_store.hybrid_search.return_value = [
        _make_raw_result(idx=i, score=0.9 - i * 0.01) for i in range(20)
    ]

    results = await retriever.retrieve_for_agent("AML compliance", "louis")

    assert len(results) == 20
    call_kwargs = mock_store.hybrid_search.call_args.kwargs
    # Without reranker, limit should equal final k=20.
    assert call_kwargs["limit"] == 20


@pytest.mark.asyncio
async def test_retrieve_for_agent_harvey_uses_k10(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """Harvey should retrieve k=10 results."""
    mock_store.hybrid_search.return_value = [
        _make_raw_result(idx=i, score=0.9 - i * 0.01) for i in range(10)
    ]

    results = await retriever.retrieve_for_agent("fraud detection", "harvey")

    assert len(results) == 10
    call_kwargs = mock_store.hybrid_search.call_args.kwargs
    assert call_kwargs["limit"] == 10


@pytest.mark.asyncio
async def test_retrieve_for_agent_unknown_uses_defaults(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """Unknown agent names should fall back to default_k."""
    await retriever.retrieve_for_agent("test query", "unknown_agent")

    call_kwargs = mock_store.hybrid_search.call_args.kwargs
    assert call_kwargs["limit"] == 10  # default_k


@pytest.mark.asyncio
async def test_retrieve_for_agent_case_insensitive(
    retriever: LegalRetriever,
    mock_store: AsyncMock,
) -> None:
    """Agent name matching should be case-insensitive."""
    mock_store.hybrid_search.return_value = [
        _make_raw_result(idx=i, score=0.9 - i * 0.01) for i in range(20)
    ]

    results = await retriever.retrieve_for_agent("query", "LOUIS")

    assert len(results) == 20


# ---------------------------------------------------------------------------
# Tests: format_context
# ---------------------------------------------------------------------------


def test_format_context_generic(retriever: LegalRetriever) -> None:
    """format_context() should produce a readable context block."""
    results = [
        _make_retrieval_result(idx=0, text="First article text"),
        _make_retrieval_result(idx=1, text="Second article text"),
    ]

    context = retriever.format_context(results, corpus_version="2026-W14")

    assert "First article text" in context
    assert "Second article text" in context
    assert "BOE-A-2010-6737" in context
    assert "Ley 10/2010" in context
    assert "Art. 18" in context
    assert "2026-W14" in context
    assert "Retrieved 2 relevant passages" in context


def test_format_context_louis_template(retriever: LegalRetriever) -> None:
    """format_context() with agent_name='louis' should use the Louis template."""
    results = [_make_retrieval_result(idx=0)]

    context = retriever.format_context(results, corpus_version="2026-W14", agent_name="louis")

    assert "LEGAL REFERENCES" in context
    assert "INSTRUCTIONS FOR CITATION" in context
    assert "Retrieved" not in context  # Louis template does not include this line


def test_format_context_empty_results(retriever: LegalRetriever) -> None:
    """format_context() with empty results should return empty string."""
    context = retriever.format_context([], corpus_version="2026-W14")

    assert context == ""


def test_format_context_includes_metadata(retriever: LegalRetriever) -> None:
    """format_context() should include dates and status from metadata."""
    results = [_make_retrieval_result(idx=0)]

    context = retriever.format_context(results, corpus_version="2026-W14")

    assert "2010-04-29" in context  # fecha_publicacion
    assert "2025-12-01" in context  # fecha_consolidacion
    assert "vigente" in context  # estado_consolidacion


# ---------------------------------------------------------------------------
# Tests: format_citations
# ---------------------------------------------------------------------------


def test_format_citations_structure(retriever: LegalRetriever) -> None:
    """format_citations() should return structured citation dicts."""
    results = [
        _make_retrieval_result(idx=0, score=0.9123456),
        _make_retrieval_result(idx=1, score=0.8765432),
    ]

    citations = retriever.format_citations(results)

    assert len(citations) == 2
    assert citations[0]["boe_id"] == "BOE-A-2010-6737"
    assert citations[0]["norma_titulo"] == "Ley 10/2010, de 28 de abril"
    assert citations[0]["articulo"] == "Art. 18"
    assert citations[0]["score"] == 0.9123  # rounded to 4 decimals
    assert citations[0]["fecha_publicacion"] == "2010-04-29"
    assert citations[0]["estado_consolidacion"] == "vigente"
    assert citations[0]["collection"] == "boe_legislation"


def test_format_citations_empty(retriever: LegalRetriever) -> None:
    """format_citations() with empty results should return empty list."""
    citations = retriever.format_citations([])

    assert citations == []


# ---------------------------------------------------------------------------
# Tests: Reranker unit tests
# ---------------------------------------------------------------------------


def test_reranker_rerank_returns_top_k() -> None:
    """Reranker.rerank() should return top_k results sorted by score."""
    reranker = Reranker(model_name="BAAI/bge-reranker-v2-m3")

    documents = [
        _make_retrieval_result(idx=0, text="doc A", score=0.5),
        _make_retrieval_result(idx=1, text="doc B", score=0.8),
        _make_retrieval_result(idx=2, text="doc C", score=0.3),
    ]

    # Mock the cross encoder so we don't load the actual model.
    mock_encoder = MagicMock()
    mock_encoder.predict.return_value = [0.2, 0.9, 0.6]  # B is best, C is second
    reranker._cross_encoder = mock_encoder

    results = reranker.rerank("test query", documents, top_k=2)

    assert len(results) == 2
    # B should be first (score 0.9), C second (score 0.6).
    assert results[0].text == "doc B"
    assert results[0].score == pytest.approx(0.9)
    assert results[1].text == "doc C"
    assert results[1].score == pytest.approx(0.6)


def test_reranker_rerank_empty_documents() -> None:
    """Reranker.rerank() with empty documents should return empty list."""
    reranker = Reranker(model_name="BAAI/bge-reranker-v2-m3")

    results = reranker.rerank("test query", [], top_k=10)

    assert results == []


def test_reranker_lazy_loading() -> None:
    """Reranker should not load the model on init (lazy loading)."""
    with patch("fraudai.rag.reranker.logger"):
        reranker = Reranker(model_name="BAAI/bge-reranker-v2-m3", device="cpu")

    # Model should NOT be loaded yet.
    assert reranker._cross_encoder is None


def test_reranker_loads_model_on_first_call() -> None:
    """Reranker should load CrossEncoder on first rerank call."""
    reranker = Reranker(model_name="BAAI/bge-reranker-v2-m3", device="cpu")

    mock_encoder = MagicMock()
    mock_encoder.predict.return_value = [0.5]

    with patch(
        "sentence_transformers.CrossEncoder",
        return_value=mock_encoder,
        create=True,
    ) as mock_cls:
        documents = [_make_retrieval_result(idx=0)]
        reranker.rerank("query", documents, top_k=1)

        mock_cls.assert_called_once_with("BAAI/bge-reranker-v2-m3", device="cpu")


# ---------------------------------------------------------------------------
# Tests: _parse_results
# ---------------------------------------------------------------------------


def test_parse_results_extracts_fields() -> None:
    """_parse_results should map raw dict fields to RetrievalResult."""
    raw = [_make_raw_result(idx=0, text="Test text", score=0.85)]

    results = LegalRetriever._parse_results(raw, "boe_legislation")

    assert len(results) == 1
    assert results[0].text == "Test text"
    assert results[0].score == pytest.approx(0.85)
    assert results[0].boe_id == "BOE-A-2010-6737"
    assert results[0].norma_titulo == "Ley 10/2010, de 28 de abril"
    assert results[0].articulo == "Art. 18"
    assert results[0].collection == "boe_legislation"


def test_parse_results_handles_missing_fields() -> None:
    """_parse_results should handle results with missing payload fields."""
    raw = [{"id": "point-0", "score": 0.5, "payload": {"text": "partial"}}]

    results = LegalRetriever._parse_results(raw, "boe_legislation")

    assert len(results) == 1
    assert results[0].text == "partial"
    assert results[0].boe_id == ""
    assert results[0].norma_titulo == ""
    assert results[0].articulo == ""
