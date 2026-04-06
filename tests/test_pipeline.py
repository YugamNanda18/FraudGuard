"""Tests for the BOE ingestion pipeline with fully mocked dependencies.

All external services (BOE API, Qdrant, embedding model) are mocked so
tests run without network or GPU access.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fraudai.ingestion.boe_client import BOEDocument, BOEDocumentMeta
from fraudai.ingestion.pipeline import BOEIngestionPipeline, PipelineResult

# ---------------------------------------------------------------------------
# Fixtures: fake data
# ---------------------------------------------------------------------------

_FAKE_META = BOEDocumentMeta(
    identificador="BOE-A-2010-6737",
    titulo="Ley 10/2010, de prevencion del blanqueo de capitales.",
    fecha_publicacion="20100429",
    fecha_disposicion="20100428",
    rango="Ley",
    departamento="Jefatura del Estado",
    estado_consolidacion="Finalizado",
)

_FAKE_DOC = BOEDocument(
    meta=_FAKE_META,
    texto="<p>Articulo 1. La presente ley tiene por objeto la prevencion.</p>",
    materias=[{"codigo": "60", "texto": "Activos financieros"}],
    notas=[],
    referencias_anteriores=[],
    referencias_posteriores=[],
)

_FAKE_DOC_NO_TEXT = BOEDocument(
    meta=_FAKE_META,
    texto="",
    materias=[],
    notas=[],
    referencias_anteriores=[],
    referencias_posteriores=[],
)


class _FakeChunkMetadata:
    """Mimics ChunkMetadata from the chunker module."""

    def __init__(self, **kwargs: str) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self) -> dict[str, str]:
        return self.__dict__.copy()


class _FakeLegalChunk:
    """Mimics LegalChunk from the chunker module."""

    def __init__(self, text: str, metadata: _FakeChunkMetadata) -> None:
        self.text = text
        self.metadata = metadata


def _make_fake_chunks(n: int = 3) -> list[_FakeLegalChunk]:
    chunks = []
    for i in range(n):
        meta = _FakeChunkMetadata(
            boe_id="BOE-A-2010-6737",
            norma_titulo="Ley 10/2010 blanqueo",
            articulo=f"art_{i + 1}",
            seccion="I",
            rango="Ley",
            departamento="Jefatura del Estado",
            materia_codigo="60",
            fecha_publicacion="20100429",
            fecha_consolidacion="",
            estado_consolidacion="Finalizado",
        )
        chunks.append(
            _FakeLegalChunk(
                text=f"Chunk text number {i + 1} about anti-money laundering.",
                metadata=meta,
            )
        )
    return chunks


def _make_fake_embeddings(n: int) -> list[dict]:
    return [
        {
            "dense": [0.01 * j for j in range(1024)],
            "sparse": {"indices": [1, 5, 10], "values": [0.8, 0.5, 0.3]},
        }
        for _ in range(n)
    ]


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------


def _build_pipeline(
    *,
    boe_get_doc: BOEDocument = _FAKE_DOC,
    boe_search_results: list[BOEDocumentMeta] | None = None,
    chunks: list[_FakeLegalChunk] | None = None,
    embed_result: list[dict] | None = None,
    upsert_return: int = 3,
    corpus_version: str = "2026-W14",
) -> BOEIngestionPipeline:
    """Build a pipeline with all dependencies mocked."""
    if boe_search_results is None:
        boe_search_results = [_FAKE_META]
    if chunks is None:
        chunks = _make_fake_chunks(3)
    if embed_result is None:
        embed_result = _make_fake_embeddings(len(chunks))

    boe_client = MagicMock()
    boe_client.get_document = AsyncMock(return_value=boe_get_doc)
    boe_client.search_all_pages = AsyncMock(return_value=boe_search_results)

    extractor = MagicMock()
    extractor.extract = MagicMock(return_value="Extracted structured text")

    chunker = MagicMock()
    chunker.chunk_document = MagicMock(return_value=chunks)

    embedder = MagicMock()
    embedder.encode = MagicMock(return_value=embed_result)

    store = MagicMock()
    store.upsert_chunks = AsyncMock(return_value=upsert_return)

    return BOEIngestionPipeline(
        boe_client=boe_client,
        extractor=extractor,
        chunker=chunker,
        embedder=embedder,
        store=store,
        corpus_version=corpus_version,
    )


# ---------------------------------------------------------------------------
# Tests: process_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_document_returns_chunk_count() -> None:
    pipeline = _build_pipeline(upsert_return=3)
    result = await pipeline.process_document("BOE-A-2010-6737")

    assert result == 3
    pipeline._boe.get_document.assert_awaited_once_with("BOE-A-2010-6737")
    pipeline._extractor.extract.assert_called_once()
    pipeline._chunker.chunk_document.assert_called_once()
    pipeline._embedder.encode.assert_called_once()
    pipeline._store.upsert_chunks.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_document_skips_empty_text() -> None:
    pipeline = _build_pipeline(boe_get_doc=_FAKE_DOC_NO_TEXT)
    result = await pipeline.process_document("BOE-A-2010-6737")

    assert result == 0
    pipeline._extractor.extract.assert_not_called()


@pytest.mark.asyncio
async def test_process_document_skips_zero_chunks() -> None:
    pipeline = _build_pipeline(chunks=[], embed_result=[])
    result = await pipeline.process_document("BOE-A-2010-6737")

    assert result == 0
    pipeline._embedder.encode.assert_not_called()
    pipeline._store.upsert_chunks.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_document_passes_metadata_to_qdrant() -> None:
    pipeline = _build_pipeline()
    await pipeline.process_document("BOE-A-2010-6737")

    call_args = pipeline._store.upsert_chunks.call_args
    collection = call_args[0][0]
    chunks_list = call_args[0][1]

    assert collection == "boe_legislation"
    assert len(chunks_list) == 3

    first = chunks_list[0]
    assert "text" in first
    assert "dense_vector" in first
    assert "metadata" in first
    assert first["metadata"]["version_corpus"] == "2026-W14"
    assert "fecha_ingestion" in first["metadata"]


# ---------------------------------------------------------------------------
# Tests: run_full
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_full_processes_all_documents() -> None:
    meta_a = BOEDocumentMeta(
        identificador="BOE-A-0001",
        titulo="Ley A",
        fecha_publicacion="20200101",
        fecha_disposicion="20200101",
    )
    meta_b = BOEDocumentMeta(
        identificador="BOE-A-0002",
        titulo="Ley B",
        fecha_publicacion="20200102",
        fecha_disposicion="20200102",
    )
    pipeline = _build_pipeline(boe_search_results=[meta_a, meta_b])
    result = await pipeline.run_full()

    assert isinstance(result, PipelineResult)
    assert result.documents_processed == 2
    assert result.chunks_upserted == 6  # 3 per doc
    assert result.errors == []
    assert result.corpus_version == "2026-W14"
    assert result.duration_seconds >= 0


@pytest.mark.asyncio
async def test_run_full_with_no_documents() -> None:
    pipeline = _build_pipeline(boe_search_results=[])
    result = await pipeline.run_full()

    assert result.documents_processed == 0
    assert result.chunks_upserted == 0


# ---------------------------------------------------------------------------
# Tests: run_incremental
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_incremental_calls_search_with_date() -> None:
    pipeline = _build_pipeline()
    result = await pipeline.run_incremental(since_date="20260401")

    assert result.documents_processed == 1
    pipeline._boe.search_all_pages.assert_awaited_once()
    call_kwargs = pipeline._boe.search_all_pages.call_args[1]
    assert call_kwargs.get("date_from") == "20260401"


@pytest.mark.asyncio
async def test_run_incremental_defaults_to_today() -> None:
    pipeline = _build_pipeline()
    result = await pipeline.run_incremental()

    assert result.documents_processed == 1
    call_kwargs = pipeline._boe.search_all_pages.call_args[1]
    # Should have a date_from set (today's date)
    assert call_kwargs.get("date_from") is not None


# ---------------------------------------------------------------------------
# Tests: error handling — one bad document does not stop the pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_in_one_document_does_not_stop_pipeline() -> None:
    meta_ok = BOEDocumentMeta(
        identificador="BOE-A-OK",
        titulo="Good doc",
        fecha_publicacion="20200101",
        fecha_disposicion="20200101",
    )
    meta_bad = BOEDocumentMeta(
        identificador="BOE-A-BAD",
        titulo="Bad doc",
        fecha_publicacion="20200102",
        fecha_disposicion="20200102",
    )

    pipeline = _build_pipeline(boe_search_results=[meta_bad, meta_ok])

    call_count = 0

    async def _mock_get_document(doc_id: str) -> BOEDocument:
        nonlocal call_count
        call_count += 1
        if doc_id == "BOE-A-BAD":
            raise RuntimeError("Simulated network error")
        return _FAKE_DOC

    pipeline._boe.get_document = AsyncMock(side_effect=_mock_get_document)

    result = await pipeline.run_full()

    assert result.documents_processed == 1
    assert len(result.errors) == 1
    assert "BOE-A-BAD" in result.errors[0]
    assert call_count == 2  # Both documents were attempted


@pytest.mark.asyncio
async def test_multiple_errors_collected() -> None:
    metas = [
        BOEDocumentMeta(
            identificador=f"BOE-A-ERR-{i}",
            titulo=f"Error doc {i}",
            fecha_publicacion="20200101",
            fecha_disposicion="20200101",
        )
        for i in range(3)
    ]
    pipeline = _build_pipeline(boe_search_results=metas)
    pipeline._boe.get_document = AsyncMock(side_effect=RuntimeError("fail"))

    result = await pipeline.run_full()

    assert result.documents_processed == 0
    assert len(result.errors) == 3
    assert result.duration_seconds >= 0


# ---------------------------------------------------------------------------
# Tests: corpus version
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_corpus_version_auto_generated_when_none() -> None:
    pipeline = BOEIngestionPipeline(
        boe_client=MagicMock(),
        extractor=MagicMock(),
        chunker=MagicMock(),
        embedder=MagicMock(),
        store=MagicMock(),
        corpus_version=None,
    )
    # Should be in format YYYY-WNN
    version = pipeline._corpus_version
    assert len(version) == 8  # "2026-W14"
    assert version.startswith("20")
    assert "-W" in version


# ---------------------------------------------------------------------------
# Tests: embedding batching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_large_document_embeds_in_batches() -> None:
    n_chunks = 150
    chunks = _make_fake_chunks(n_chunks)
    # Embedder.encode will be called multiple times for batches
    embedder = MagicMock()
    all_embeddings = _make_fake_embeddings(n_chunks)

    batch_calls: list[int] = []

    def _batch_encode(texts: list[str]) -> list[dict]:
        batch_calls.append(len(texts))
        start = sum(batch_calls[:-1])
        return all_embeddings[start : start + len(texts)]

    embedder.encode = MagicMock(side_effect=_batch_encode)

    boe_client = MagicMock()
    boe_client.get_document = AsyncMock(return_value=_FAKE_DOC)

    chunker = MagicMock()
    chunker.chunk_document = MagicMock(return_value=chunks)

    store = MagicMock()
    store.upsert_chunks = AsyncMock(return_value=n_chunks)

    pipeline = BOEIngestionPipeline(
        boe_client=boe_client,
        extractor=MagicMock(extract=MagicMock(return_value="text")),
        chunker=chunker,
        embedder=embedder,
        store=store,
        corpus_version="2026-W14",
    )

    result = await pipeline.process_document("BOE-A-2010-6737")

    assert result == n_chunks
    # With batch_size=64: 150 -> batches of 64, 64, 22
    assert len(batch_calls) == 3
    assert batch_calls[0] == 64
    assert batch_calls[1] == 64
    assert batch_calls[2] == 22
