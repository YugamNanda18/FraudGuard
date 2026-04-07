"""End-to-end ingestion pipeline: BOE API -> extract -> chunk -> embed -> Qdrant.

Orchestrates the full flow from legislation search/download through text
extraction, chunking, embedding generation, and vector store upsert.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from qdrant_client import models as qdrant_models

from fraudai.ingestion.boe_client import (  # noqa: TC001 — runtime usage in __init__ and bodies
    BOEClient,
    BOEDocumentMeta,
)
from fraudai.ingestion.chunker import LegalChunk, LegalChunker  # noqa: TC001
from fraudai.ingestion.embeddings import EmbeddingGenerator  # noqa: TC001
from fraudai.ingestion.text_extractor import BOETextExtractor  # noqa: TC001
from fraudai.rag.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class PipelineResult(BaseModel):
    """Summary of an ingestion pipeline run."""

    corpus_version: str = ""
    documents_processed: int = 0
    chunks_generated: int = 0
    chunks_upserted: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

_EMBED_BATCH_SIZE = 64


class BOEIngestionPipeline:
    """Pipeline completo: BOE API -> extract -> chunk -> embed -> Qdrant."""

    def __init__(
        self,
        boe_client: BOEClient,
        extractor: BOETextExtractor,
        chunker: LegalChunker,
        embedder: EmbeddingGenerator,
        store: QdrantStore,
        corpus_version: str | None = None,
    ) -> None:
        self._boe = boe_client
        self._extractor = extractor
        self._chunker = chunker
        self._embedder = embedder
        self._store = store
        self._corpus_version = corpus_version or self._generate_version()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_full(
        self,
        materias: list[str] | None = None,
    ) -> PipelineResult:
        """Full ingestion: search all legislation and (re-)process every document.

        Args:
            materias: Optional list of materia keywords to filter.  Defaults to
                all materias in ``CODIGOS_MATERIAS``.
        """
        start = time.monotonic()
        result = PipelineResult(corpus_version=self._corpus_version)

        logger.info(
            "Pipeline full run started (corpus_version=%s)",
            self._corpus_version,
        )

        docs = await self._search_documents(materias)
        logger.info("Pipeline found %d documents to process", len(docs))

        for doc_meta in docs:
            try:
                n_chunks = await self.process_document(doc_meta.identificador)
                result.documents_processed += 1
                result.chunks_generated += n_chunks
                result.chunks_upserted += n_chunks
            except Exception as exc:
                msg = f"Error processing {doc_meta.identificador}: {exc}"
                logger.error(msg)
                result.errors.append(msg)

        result.duration_seconds = round(time.monotonic() - start, 2)
        logger.info(
            "Pipeline full run completed: docs=%d chunks=%d errors=%d duration=%.2fs",
            result.documents_processed,
            result.chunks_upserted,
            len(result.errors),
            result.duration_seconds,
        )
        return result

    async def run_incremental(
        self,
        since_date: str | None = None,
    ) -> PipelineResult:
        """Incremental ingestion: only process documents published since a date.

        Args:
            since_date: Start date in ``AAAAMMDD`` format.  If ``None``,
                uses today's date (only today's publications).
        """
        start = time.monotonic()
        result = PipelineResult(corpus_version=self._corpus_version)

        if since_date is None:
            since_date = datetime.now(tz=UTC).strftime("%Y%m%d")

        logger.info(
            "Pipeline incremental run started (since=%s, corpus_version=%s)",
            since_date,
            self._corpus_version,
        )

        docs = await self._search_documents(date_from=since_date)
        logger.info(
            "Pipeline incremental: found %d documents since %s",
            len(docs),
            since_date,
        )

        for doc_meta in docs:
            try:
                n_chunks = await self.process_document(doc_meta.identificador)
                result.documents_processed += 1
                result.chunks_generated += n_chunks
                result.chunks_upserted += n_chunks
            except Exception as exc:
                msg = f"Error processing {doc_meta.identificador}: {exc}"
                logger.error(msg)
                result.errors.append(msg)

        result.duration_seconds = round(time.monotonic() - start, 2)
        logger.info(
            "Pipeline incremental run completed: docs=%d chunks=%d errors=%d duration=%.2fs",
            result.documents_processed,
            result.chunks_upserted,
            len(result.errors),
            result.duration_seconds,
        )
        return result

    async def process_document(self, doc_id: str, skip_existing: bool = True) -> int:
        """Process a single document end-to-end.

        Steps:
            0. Check if already indexed with current corpus version (dedup)
            1. Fetch full document from BOE API
            2. Extract structured text via ``BOETextExtractor``
            3. Chunk via ``LegalChunker``
            4. Generate embeddings (batched)
            5. Upsert to Qdrant

        Returns:
            Number of chunks generated and upserted.
        """
        logger.info("Processing document %s", doc_id)

        if skip_existing and await self._already_indexed(doc_id):
            logger.info(
                "Document %s already indexed with corpus version %s, skipping",
                doc_id,
                self._corpus_version,
            )
            return 0

        # 1. Fetch document
        boe_doc = await self._boe.get_document(doc_id)
        if not boe_doc.texto:
            logger.warning("Document %s has no text, skipping", doc_id)
            return 0

        # 2. Extract structured text
        extracted = self._extractor.extract(boe_doc.texto)

        # The text extractor may fail to find the title when the input is
        # plain text (no HTML headings).  Fall back to the BOE XML metadata
        # title which is always populated.
        if hasattr(extracted, "titulo") and not extracted.titulo and boe_doc.meta.titulo:
            extracted.titulo = boe_doc.meta.titulo

        # 3. Chunk — the chunker expects (ExtractedDocument, BOEDocumentMeta)
        chunks: list[LegalChunk] = self._chunker.chunk_document(extracted, boe_doc.meta)

        if not chunks:
            logger.warning("Document %s produced 0 chunks", doc_id)
            return 0

        # 4. Generate embeddings in batches
        texts = [c.text for c in chunks]
        embeddings = self._encode_batched(texts)

        # 5. Build Qdrant points and upsert
        qdrant_chunks = self._build_qdrant_chunks(chunks, embeddings)
        upserted = await self._store.upsert_chunks(
            QdrantStore.BOE_COLLECTION,
            qdrant_chunks,
        )

        logger.info(
            "Document %s: %d chunks generated, %d upserted",
            doc_id,
            len(chunks),
            upserted,
        )
        return upserted

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _search_documents(
        self,
        materias: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[BOEDocumentMeta]:
        """Search BOE for legislation documents matching our filters."""
        return await self._boe.search_all_pages(
            materias=materias,
            date_from=date_from,
            date_to=date_to,
        )

    def _encode_batched(self, texts: list[str]) -> list[dict[str, Any]]:
        """Encode texts in batches, returning combined dense+sparse vectors."""
        all_embeddings: list[dict[str, Any]] = []
        for i in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[i : i + _EMBED_BATCH_SIZE]
            batch_emb = self._embedder.encode(batch)
            all_embeddings.extend(batch_emb)
        return all_embeddings

    def _build_qdrant_chunks(
        self,
        chunks: list[LegalChunk],
        embeddings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Combine chunk data with embeddings into Qdrant-ready dicts."""
        now_iso = datetime.now(tz=UTC).isoformat()
        qdrant_chunks: list[dict[str, Any]] = []

        for chunk, emb in zip(chunks, embeddings, strict=True):
            sparse_data = emb.get("sparse", {})
            sparse_vector: qdrant_models.SparseVector | None = None
            if sparse_data and sparse_data.get("indices"):
                sparse_vector = qdrant_models.SparseVector(
                    indices=sparse_data["indices"],
                    values=sparse_data["values"],
                )

            metadata = chunk.metadata.model_dump()
            metadata["version_corpus"] = self._corpus_version
            metadata["fecha_ingestion"] = now_iso

            qdrant_chunks.append(
                {
                    "text": chunk.text,
                    "dense_vector": emb["dense"],
                    "sparse_vector": sparse_vector,
                    "metadata": metadata,
                }
            )

        return qdrant_chunks

    async def _already_indexed(self, doc_id: str) -> bool:
        """Check if a document is already indexed with the current corpus version."""
        try:
            from qdrant_client import models

            result = await self._store._client.scroll(
                collection_name=QdrantStore.BOE_COLLECTION,
                scroll_filter=models.Filter(must=[
                    models.FieldCondition(
                        key="boe_id",
                        match=models.MatchValue(value=doc_id),
                    ),
                    models.FieldCondition(
                        key="version_corpus",
                        match=models.MatchValue(value=self._corpus_version),
                    ),
                ]),
                limit=1,
            )
            points, _ = result
            return len(points) > 0
        except Exception:
            return False

    @staticmethod
    def _generate_version() -> str:
        """Generate a corpus version label from current ISO week (e.g. '2026-W14')."""
        now = datetime.now(tz=UTC)
        year, week, _ = now.isocalendar()
        return f"{year}-W{week:02d}"
