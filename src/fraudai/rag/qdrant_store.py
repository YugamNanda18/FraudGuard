"""Qdrant vector store management for FraudAI Agent.

Handles collection lifecycle, upsert, and hybrid search (dense + sparse)
for BOE legislation, EU regulation, and ephemeral session collections.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client import models
from qdrant_client.async_qdrant_client import AsyncQdrantClient

logger = logging.getLogger(__name__)


class QdrantStore:
    """Manages Qdrant collections and CRUD operations."""

    BOE_COLLECTION = "boe_legislation"
    EU_COLLECTION = "eu_regulation"
    DENSE_DIM = 1024  # BGE-M3

    # Payload fields that require indexing for efficient filtering.
    _BOE_PAYLOAD_INDEXES: list[tuple[str, models.PayloadSchemaType]] = [
        ("boe_id", models.PayloadSchemaType.KEYWORD),
        ("materia_codigo", models.PayloadSchemaType.KEYWORD),
        ("fecha_publicacion", models.PayloadSchemaType.DATETIME),
        ("estado_consolidacion", models.PayloadSchemaType.KEYWORD),
        ("version_corpus", models.PayloadSchemaType.KEYWORD),
    ]

    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self._client = AsyncQdrantClient(host=host, port=port)
        logger.info("QdrantStore initialized (host=%s, port=%d)", host, port)

    # ------------------------------------------------------------------
    # Collection initialization
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create static collections if they do not already exist."""
        await self.create_boe_collection()
        await self._create_legislation_collection(
            self.EU_COLLECTION,
            with_sparse=True,
        )
        logger.info("Qdrant collections initialized")

    async def create_boe_collection(self) -> None:
        """Create the BOE legislation collection.

        Schema:
            Dense vectors  - 1024-dim cosine (BGE-M3)
            Sparse vectors - BM25 lexical weights
            Payload        - boe_id, norma_titulo, articulo, seccion,
                             materia_codigo, fecha_publicacion,
                             fecha_consolidacion, estado_consolidacion,
                             version_corpus, fecha_ingestion, rango,
                             departamento
        """
        await self._create_legislation_collection(
            self.BOE_COLLECTION,
            with_sparse=True,
        )
        # Create payload indexes for efficient filtering.
        for field_name, schema_type in self._BOE_PAYLOAD_INDEXES:
            await self._client.create_payload_index(
                collection_name=self.BOE_COLLECTION,
                field_name=field_name,
                field_schema=schema_type,
            )
        logger.info(
            "BOE collection ready with %d payload indexes",
            len(self._BOE_PAYLOAD_INDEXES),
        )

    async def _create_legislation_collection(
        self,
        name: str,
        *,
        with_sparse: bool = True,
    ) -> None:
        """Create a legislation collection if it does not exist."""
        collections = await self._client.get_collections()
        existing = {c.name for c in collections.collections}
        if name in existing:
            logger.info("Collection '%s' already exists, skipping creation", name)
            return

        sparse_config: dict[str, models.SparseVectorParams] | None = None
        if with_sparse:
            sparse_config = {
                "bm25": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False),
                ),
            }

        await self._client.create_collection(
            collection_name=name,
            vectors_config={
                "dense": models.VectorParams(
                    size=self.DENSE_DIM,
                    distance=models.Distance.COSINE,
                ),
            },
            sparse_vectors_config=sparse_config,
        )
        logger.info("Created collection '%s'", name)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def upsert_chunks(
        self,
        collection: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Insert or update chunks in a collection.

        Each chunk dict must contain:
            text          - chunk text (stored in payload)
            dense_vector  - list[float] of length DENSE_DIM
            sparse_vector - models.SparseVector | None
            metadata      - dict with payload fields

        Returns the number of points upserted.
        """
        if not chunks:
            return 0

        points: list[models.PointStruct] = []
        for chunk in chunks:
            vector: dict[str, Any] = {"dense": chunk["dense_vector"]}
            if chunk.get("sparse_vector") is not None:
                vector["bm25"] = chunk["sparse_vector"]

            point_id = chunk.get("id") or str(uuid.uuid4())

            payload = {**chunk.get("metadata", {}), "text": chunk["text"]}

            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                ),
            )

        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            await self._client.upsert(
                collection_name=collection,
                points=batch,
            )

        logger.info(
            "Upserted %d points into '%s'",
            len(points),
            collection,
        )
        return len(points)

    # ------------------------------------------------------------------
    # Hybrid search
    # ------------------------------------------------------------------

    async def hybrid_search(
        self,
        collection: str,
        dense_vector: list[float],
        sparse_vector: models.SparseVector | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Hybrid search combining dense and sparse vectors.

        Uses Qdrant v1.7+ ``query_points`` with ``prefetch`` for
        dense retrieval fused with sparse BM25 scoring via RRF.

        Args:
            collection:    Target collection name.
            dense_vector:  Dense embedding (1024-dim float list).
            sparse_vector: Optional sparse BM25 vector.
            filters:       Optional metadata filters as
                           ``{"field": {"match": {"value": ...}}}``.
            limit:         Maximum results to return.

        Returns:
            List of dicts with ``id``, ``score``, ``payload``.
        """
        query_filter = self._build_filter(filters) if filters else None

        # If no sparse vector, fall back to dense-only search.
        if sparse_vector is None:
            results = await self._client.query_points(
                collection_name=collection,
                query=dense_vector,
                using="dense",
                query_filter=query_filter,
                limit=limit,
            )
            return self._format_results(results)

        # Hybrid: prefetch dense candidates, fuse with sparse via RRF.
        prefetch_dense = models.Prefetch(
            query=dense_vector,
            using="dense",
            limit=limit * 3,
        )
        prefetch_sparse = models.Prefetch(
            query=models.SparseVector(
                indices=sparse_vector.indices,
                values=sparse_vector.values,
            ),
            using="bm25",
            limit=limit * 3,
        )

        results = await self._client.query_points(
            collection_name=collection,
            prefetch=[prefetch_dense, prefetch_sparse],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=query_filter,
            limit=limit,
        )
        return self._format_results(results)

    @staticmethod
    def _build_filter(
        filters: dict[str, Any],
    ) -> models.Filter:
        """Convert a flat filter dict to a Qdrant Filter.

        Supports two formats:
            Simple:  ``{"field": "value"}``
            Nested:  ``{"field": {"match": {"value": "..."}}}``
        """
        conditions: list[models.FieldCondition] = []
        for key, value in filters.items():
            if isinstance(value, dict) and "match" in value:
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value["match"]["value"]),
                    ),
                )
            else:
                conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    ),
                )
        # list[FieldCondition] is a subtype but list is invariant in mypy
        return models.Filter(must=conditions)  # type: ignore[arg-type]

    @staticmethod
    def _format_results(
        results: models.QueryResponse,
    ) -> list[dict[str, Any]]:
        """Normalize query results into plain dicts."""
        formatted: list[dict[str, Any]] = []
        for point in results.points:
            formatted.append(
                {
                    "id": point.id,
                    "score": point.score,
                    "payload": point.payload,
                },
            )
        return formatted

    # ------------------------------------------------------------------
    # Session collections (per-tenant, ephemeral)
    # ------------------------------------------------------------------

    async def create_session_collection(self, tenant_id: str) -> str:
        """Create an ephemeral collection for a tenant session.

        Session collections use dense vectors only (no sparse).

        Returns the collection name.
        """
        collection_name = f"session_{tenant_id}"

        collections = await self._client.get_collections()
        existing = {c.name for c in collections.collections}
        if collection_name in existing:
            logger.info(
                "Session collection '%s' already exists",
                collection_name,
            )
            return collection_name

        await self._client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=self.DENSE_DIM,
                    distance=models.Distance.COSINE,
                ),
            },
        )
        logger.info("Created session collection '%s'", collection_name)
        return collection_name

    async def delete_session_collection(self, tenant_id: str) -> None:
        """Delete a tenant session collection."""
        collection_name = f"session_{tenant_id}"
        await self._client.delete_collection(collection_name=collection_name)
        logger.info("Deleted session collection '%s'", collection_name)

    # ------------------------------------------------------------------
    # Corpus versioning
    # ------------------------------------------------------------------

    async def get_corpus_version(self) -> str | None:
        """Return the most recent corpus version indexed in BOE collection.

        Scrolls a single point ordered by ``version_corpus`` descending.
        Returns ``None`` if the collection is empty.
        """
        result = await self._client.scroll(
            collection_name=self.BOE_COLLECTION,
            limit=1,
            order_by=models.OrderBy(
                key="version_corpus",
                direction=models.Direction.DESC,
            ),
        )
        points, _ = result
        if not points:
            return None
        payload = points[0].payload or {}
        version = payload.get("version_corpus")
        return str(version) if version is not None else None

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Verify that Qdrant is reachable and healthy."""
        try:
            await self._client.get_collections()
            return True
        except Exception:
            logger.exception("Qdrant health check failed")
            return False
