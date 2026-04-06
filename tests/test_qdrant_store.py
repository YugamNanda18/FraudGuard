"""Tests for QdrantStore — all Qdrant calls are mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client import models

from fraudai.rag.qdrant_store import QdrantStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> AsyncMock:
    """Return a mocked AsyncQdrantClient."""
    client = AsyncMock()

    # get_collections returns an empty list by default (no existing collections).
    client.get_collections.return_value = MagicMock(collections=[])

    # create_collection, create_payload_index, upsert — just succeed.
    client.create_collection.return_value = True
    client.create_payload_index.return_value = MagicMock()
    client.upsert.return_value = MagicMock()
    client.delete_collection.return_value = True

    return client


@pytest.fixture
def store(mock_client: AsyncMock) -> QdrantStore:
    """Return a QdrantStore wired to the mocked client."""
    with patch(
        "fraudai.rag.qdrant_store.AsyncQdrantClient",
        return_value=mock_client,
    ):
        s = QdrantStore(host="localhost", port=6333)
    # Replace the internal client reference so every call hits the mock.
    s._client = mock_client
    return s


# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initialize_creates_collections(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """initialize() should create BOE and EU collections."""
    await store.initialize()

    # Two collections created: boe_legislation and eu_regulation.
    assert mock_client.create_collection.call_count == 2

    created_names = [
        call.kwargs["collection_name"] for call in mock_client.create_collection.call_args_list
    ]
    assert QdrantStore.BOE_COLLECTION in created_names
    assert QdrantStore.EU_COLLECTION in created_names


@pytest.mark.asyncio
async def test_initialize_creates_payload_indexes(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """initialize() should create payload indexes on the BOE collection."""
    await store.initialize()

    indexed_fields = [
        call.kwargs["field_name"] for call in mock_client.create_payload_index.call_args_list
    ]
    expected_fields = [
        "boe_id",
        "materia_codigo",
        "fecha_publicacion",
        "estado_consolidacion",
        "version_corpus",
    ]
    assert indexed_fields == expected_fields


@pytest.mark.asyncio
async def test_initialize_skips_existing_collections(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """If collections already exist, initialize() must not recreate them."""
    boe = MagicMock()
    boe.name = QdrantStore.BOE_COLLECTION
    eu = MagicMock()
    eu.name = QdrantStore.EU_COLLECTION
    mock_client.get_collections.return_value = MagicMock(collections=[boe, eu])

    await store.initialize()

    mock_client.create_collection.assert_not_called()


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------


def _make_chunk(
    text: str = "sample text",
    dense: list[float] | None = None,
    sparse: models.SparseVector | None = None,
    metadata: dict[str, Any] | None = None,
    chunk_id: str | None = None,
) -> dict[str, Any]:
    chunk: dict[str, Any] = {
        "text": text,
        "dense_vector": dense or [0.1] * 1024,
        "sparse_vector": sparse,
        "metadata": metadata or {"boe_id": "BOE-A-2010-6737"},
    }
    if chunk_id is not None:
        chunk["id"] = chunk_id
    return chunk


@pytest.mark.asyncio
async def test_upsert_chunks_returns_count(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """upsert_chunks() should return the number of points inserted."""
    chunks = [_make_chunk(text=f"chunk {i}") for i in range(3)]
    count = await store.upsert_chunks(QdrantStore.BOE_COLLECTION, chunks)

    assert count == 3
    mock_client.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_chunks_empty_list(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """upsert_chunks() with empty list should return 0 and skip upsert."""
    count = await store.upsert_chunks(QdrantStore.BOE_COLLECTION, [])

    assert count == 0
    mock_client.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_chunks_batches_large_input(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """upsert_chunks() should split >100 points into multiple batches."""
    chunks = [_make_chunk(text=f"chunk {i}") for i in range(250)]
    count = await store.upsert_chunks(QdrantStore.BOE_COLLECTION, chunks)

    assert count == 250
    # 250 points / 100 batch_size = 3 upsert calls.
    assert mock_client.upsert.call_count == 3


@pytest.mark.asyncio
async def test_upsert_includes_sparse_vector(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """When sparse_vector is provided, it must appear in the point vector."""
    sparse = models.SparseVector(indices=[0, 5, 10], values=[1.0, 0.5, 0.3])
    chunks = [_make_chunk(sparse=sparse)]

    await store.upsert_chunks(QdrantStore.BOE_COLLECTION, chunks)

    upsert_call = mock_client.upsert.call_args
    points = upsert_call.kwargs["points"]
    vector = points[0].vector
    assert "bm25" in vector
    assert vector["bm25"] is sparse


# ---------------------------------------------------------------------------
# Hybrid search
# ---------------------------------------------------------------------------


def _mock_query_response(
    n: int = 2,
) -> models.QueryResponse:
    """Build a fake QueryResponse with n scored points."""
    points = []
    for i in range(n):
        point = MagicMock()
        point.id = f"point-{i}"
        point.score = 0.9 - (i * 0.1)
        point.payload = {"text": f"result {i}", "boe_id": f"BOE-{i}"}
        points.append(point)
    return MagicMock(points=points)


@pytest.mark.asyncio
async def test_hybrid_search_dense_only(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """Search without sparse_vector should use dense-only path."""
    mock_client.query_points.return_value = _mock_query_response(2)

    results = await store.hybrid_search(
        collection=QdrantStore.BOE_COLLECTION,
        dense_vector=[0.1] * 1024,
        limit=5,
    )

    assert len(results) == 2
    assert results[0]["score"] > results[1]["score"]

    call_kwargs = mock_client.query_points.call_args.kwargs
    assert call_kwargs["using"] == "dense"
    assert "prefetch" not in call_kwargs


@pytest.mark.asyncio
async def test_hybrid_search_with_sparse(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """Search with sparse_vector should use prefetch + RRF fusion."""
    mock_client.query_points.return_value = _mock_query_response(3)

    sparse = models.SparseVector(indices=[1, 2, 3], values=[0.8, 0.5, 0.3])
    results = await store.hybrid_search(
        collection=QdrantStore.BOE_COLLECTION,
        dense_vector=[0.1] * 1024,
        sparse_vector=sparse,
        limit=10,
    )

    assert len(results) == 3

    call_kwargs = mock_client.query_points.call_args.kwargs
    assert "prefetch" in call_kwargs
    assert len(call_kwargs["prefetch"]) == 2


@pytest.mark.asyncio
async def test_hybrid_search_with_filters(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """Filters should be converted to Qdrant Filter and passed through."""
    mock_client.query_points.return_value = _mock_query_response(1)

    results = await store.hybrid_search(
        collection=QdrantStore.BOE_COLLECTION,
        dense_vector=[0.1] * 1024,
        filters={"estado_consolidacion": "vigente"},
        limit=5,
    )

    assert len(results) == 1

    call_kwargs = mock_client.query_points.call_args.kwargs
    query_filter = call_kwargs["query_filter"]
    assert isinstance(query_filter, models.Filter)
    assert len(query_filter.must) == 1
    assert query_filter.must[0].key == "estado_consolidacion"


@pytest.mark.asyncio
async def test_hybrid_search_with_nested_filters(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """Nested filter format should also be handled correctly."""
    mock_client.query_points.return_value = _mock_query_response(1)

    results = await store.hybrid_search(
        collection=QdrantStore.BOE_COLLECTION,
        dense_vector=[0.1] * 1024,
        filters={"materia_codigo": {"match": {"value": "2.3.1"}}},
        limit=5,
    )

    assert len(results) == 1

    call_kwargs = mock_client.query_points.call_args.kwargs
    query_filter = call_kwargs["query_filter"]
    assert query_filter.must[0].key == "materia_codigo"


# ---------------------------------------------------------------------------
# Session collection lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_collection(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """create_session_collection() should create 'session_{tenant_id}'."""
    name = await store.create_session_collection("tenant_abc")

    assert name == "session_tenant_abc"
    mock_client.create_collection.assert_called_once()

    call_kwargs = mock_client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == "session_tenant_abc"
    # Session collections should NOT have sparse vectors.
    assert call_kwargs.get("sparse_vectors_config") is None


@pytest.mark.asyncio
async def test_create_session_collection_idempotent(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """If session collection already exists, skip creation."""
    existing = MagicMock()
    existing.name = "session_tenant_abc"
    mock_client.get_collections.return_value = MagicMock(
        collections=[existing],
    )

    name = await store.create_session_collection("tenant_abc")

    assert name == "session_tenant_abc"
    mock_client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_delete_session_collection(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """delete_session_collection() should remove the tenant collection."""
    await store.delete_session_collection("tenant_abc")

    mock_client.delete_collection.assert_called_once_with(
        collection_name="session_tenant_abc",
    )


# ---------------------------------------------------------------------------
# Corpus version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_corpus_version_returns_latest(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """get_corpus_version() should return the latest version string."""
    point = MagicMock()
    point.payload = {"version_corpus": "2026-W14"}
    mock_client.scroll.return_value = ([point], None)

    version = await store.get_corpus_version()
    assert version == "2026-W14"


@pytest.mark.asyncio
async def test_get_corpus_version_empty_collection(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """get_corpus_version() should return None for empty collection."""
    mock_client.scroll.return_value = ([], None)

    version = await store.get_corpus_version()
    assert version is None


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_ok(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """health_check() should return True when Qdrant responds."""
    mock_client.get_collections.return_value = MagicMock(collections=[])

    assert await store.health_check() is True


@pytest.mark.asyncio
async def test_health_check_failure(
    store: QdrantStore,
    mock_client: AsyncMock,
) -> None:
    """health_check() should return False when Qdrant is unreachable."""
    mock_client.get_collections.side_effect = ConnectionError("unreachable")

    assert await store.health_check() is False
