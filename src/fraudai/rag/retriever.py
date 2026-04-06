"""Legal document retriever for FraudAI Agent.

Orchestrates the full retrieval pipeline:
    query -> dense+sparse encoding -> hybrid search -> rerank -> format citations

Designed to be called by agent nodes (Harvey, Louis, etc.) to inject
legal context into their LLM prompts.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from fraudai.core.metrics import RETRIEVAL_LATENCY, RETRIEVAL_RESULTS
from fraudai.rag.prompt_templates import (
    LOUIS_RAG_TEMPLATE,
    RAG_CONTEXT_TEMPLATE,
    SINGLE_RESULT_TEMPLATE,
)
from fraudai.rag.qdrant_store import QdrantStore

if TYPE_CHECKING:
    from fraudai.ingestion.embeddings import EmbeddingGenerator
    from fraudai.rag.reranker import Reranker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RetrievalResult(BaseModel):
    """A single retrieval result with text, score, and legal metadata."""

    text: str
    score: float
    metadata: dict[str, Any]
    boe_id: str
    norma_titulo: str
    articulo: str
    collection: str


# ---------------------------------------------------------------------------
# Agent-specific defaults
# ---------------------------------------------------------------------------

_AGENT_DEFAULTS: dict[str, dict[str, Any]] = {
    "louis": {
        "k": 20,
        "collection": QdrantStore.BOE_COLLECTION,
        "template": "louis",
    },
    "harvey": {
        "k": 10,
        "collection": QdrantStore.BOE_COLLECTION,
        "template": "generic",
    },
    "jessica": {
        "k": 10,
        "collection": QdrantStore.BOE_COLLECTION,
        "template": "generic",
    },
    "mike": {
        "k": 10,
        "collection": QdrantStore.BOE_COLLECTION,
        "template": "generic",
    },
    "rachel": {
        "k": 10,
        "collection": QdrantStore.BOE_COLLECTION,
        "template": "generic",
    },
}


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class LegalRetriever:
    """Retrieves relevant legal context from Qdrant for agent queries.

    Pipeline: query -> dense+sparse encoding -> hybrid search -> rerank -> format citations
    """

    def __init__(
        self,
        store: QdrantStore,
        embedder: EmbeddingGenerator,
        reranker: Reranker | None = None,
        default_k: int = 10,
        rerank_k: int = 20,
    ) -> None:
        self._store = store
        self._embedder = embedder
        self._reranker = reranker
        self._default_k = default_k
        self._rerank_k = rerank_k
        logger.info(
            "LegalRetriever initialized (default_k=%d, rerank_k=%d, reranker=%s)",
            default_k,
            rerank_k,
            "enabled" if reranker is not None else "disabled",
        )

    # ------------------------------------------------------------------
    # Core retrieval
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        collection: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Full retrieval pipeline: embed -> search -> rerank -> return.

        Args:
            query:      User query text.
            k:          Number of final results to return. Defaults to ``default_k``.
            collection: Target Qdrant collection. Defaults to ``boe_legislation``.
            filters:    Optional metadata filters (e.g. ``{"estado_consolidacion": "vigente"}``).

        Returns:
            Ranked list of ``RetrievalResult`` objects.
        """
        import time as _time

        final_k = k or self._default_k
        target_collection = collection or QdrantStore.BOE_COLLECTION

        start = _time.monotonic()

        # Step 1: Encode the query (dense + sparse) in a thread to avoid blocking.
        embeddings = await asyncio.to_thread(self._embedder.encode, [query])
        dense_vector: list[float] = embeddings[0]["dense"]
        sparse_dict: dict[str, Any] = embeddings[0]["sparse"]

        from qdrant_client import models as qmodels

        sparse_vector = qmodels.SparseVector(
            indices=sparse_dict["indices"],
            values=sparse_dict["values"],
        )

        # Step 2: Hybrid search. Fetch more if reranking is enabled.
        search_limit = self._rerank_k if self._reranker is not None else final_k

        raw_results = await self._store.hybrid_search(
            collection=target_collection,
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            filters=filters,
            limit=search_limit,
        )

        # Step 3: Convert raw results to RetrievalResult models.
        results = self._parse_results(raw_results, target_collection)

        # Step 4: Rerank if a reranker is available (in thread to avoid blocking).
        if self._reranker is not None and results:
            results = await asyncio.to_thread(self._reranker.rerank, query, results, final_k)
        else:
            results = results[:final_k]

        # --- Prometheus metrics ---
        duration = _time.monotonic() - start
        RETRIEVAL_LATENCY.labels(collection=target_collection).observe(duration)
        RETRIEVAL_RESULTS.labels(collection=target_collection).observe(len(results))

        logger.info(
            "Retrieved %d results for query (collection=%s, k=%d, reranked=%s)",
            len(results),
            target_collection,
            final_k,
            self._reranker is not None,
        )
        return results

    # ------------------------------------------------------------------
    # Agent-specific retrieval
    # ------------------------------------------------------------------

    async def retrieve_for_agent(
        self,
        query: str,
        agent_name: str,
    ) -> list[RetrievalResult]:
        """Retrieve with agent-specific defaults.

        Each agent has tuned retrieval parameters:
            - Louis: k=20 (exhaustive legal citations)
            - Harvey: k=10 (focused fraud context)
            - Others: k=10 (general)

        Args:
            query:      User query text.
            agent_name: Agent identifier (lowercase: "louis", "harvey", etc.).

        Returns:
            Ranked list of ``RetrievalResult`` objects.
        """
        defaults = _AGENT_DEFAULTS.get(agent_name.lower(), {})
        k = defaults.get("k", self._default_k)
        collection = defaults.get("collection", QdrantStore.BOE_COLLECTION)

        logger.debug(
            "Retrieving for agent '%s' with k=%d, collection='%s'",
            agent_name,
            k,
            collection,
        )
        return await self.retrieve(query=query, k=k, collection=collection)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_context(
        self,
        results: list[RetrievalResult],
        corpus_version: str = "unknown",
        agent_name: str | None = None,
    ) -> str:
        """Format retrieval results as context string for LLM prompt injection.

        Args:
            results:        List of retrieval results.
            corpus_version: Corpus version identifier for traceability.
            agent_name:     Optional agent name to select template (e.g. "louis").

        Returns:
            Formatted context string ready for prompt injection.
        """
        if not results:
            return ""

        # Format individual results.
        formatted_passages: list[str] = []
        for result in results:
            passage = SINGLE_RESULT_TEMPLATE.format(
                norma_titulo=result.norma_titulo,
                articulo=result.articulo,
                fecha_publicacion=result.metadata.get("fecha_publicacion", "N/A"),
                fecha_consolidacion=result.metadata.get("fecha_consolidacion", "N/A"),
                estado=result.metadata.get("estado_consolidacion", "N/A"),
                boe_id=result.boe_id,
                text=result.text,
            )
            formatted_passages.append(passage)

        context_block = "\n\n".join(formatted_passages)

        # Select template based on agent.
        use_louis = (
            agent_name is not None
            and _AGENT_DEFAULTS.get(agent_name.lower(), {}).get("template") == "louis"
        )

        if use_louis:
            return LOUIS_RAG_TEMPLATE.format(
                context=context_block,
                corpus_version=corpus_version,
            )

        return RAG_CONTEXT_TEMPLATE.format(
            context=context_block,
            corpus_version=corpus_version,
            n_results=len(results),
        )

    def format_citations(self, results: list[RetrievalResult]) -> list[dict[str, Any]]:
        """Format results as structured citations for API response.

        Returns a list of citation dicts suitable for inclusion in
        the API response body, allowing the frontend to render
        clickable legal references.

        Args:
            results: List of retrieval results.

        Returns:
            List of citation dicts with keys: boe_id, norma_titulo,
            articulo, score, fecha_publicacion, estado_consolidacion.
        """
        citations: list[dict[str, Any]] = []
        for result in results:
            citations.append(
                {
                    "boe_id": result.boe_id,
                    "norma_titulo": result.norma_titulo,
                    "articulo": result.articulo,
                    "texto_relevante": result.text[:500],
                    "score": round(result.score, 4),
                    "fecha_publicacion": result.metadata.get("fecha_publicacion", ""),
                    "estado_consolidacion": result.metadata.get("estado_consolidacion", ""),
                    "collection": result.collection,
                }
            )
        return citations

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_results(
        raw_results: list[dict[str, Any]],
        collection: str,
    ) -> list[RetrievalResult]:
        """Convert raw Qdrant results to RetrievalResult models."""
        parsed: list[RetrievalResult] = []
        for raw in raw_results:
            payload = raw.get("payload", {})
            parsed.append(
                RetrievalResult(
                    text=payload.get("text", ""),
                    score=float(raw.get("score", 0.0)),
                    metadata=payload,
                    boe_id=payload.get("boe_id", ""),
                    norma_titulo=payload.get("norma_titulo", ""),
                    articulo=payload.get("articulo", ""),
                    collection=collection,
                ),
            )
        return parsed
