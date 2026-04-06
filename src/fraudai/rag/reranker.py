"""Cross-encoder reranker for retrieval results.

Uses BGE-reranker-v2-m3 to rerank retrieved chunks by relevance
to the user query, improving precision of the top-k results.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fraudai.rag.retriever import RetrievalResult

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker for retrieval results.

    Uses BGE-reranker-v2-m3 for reranking retrieved chunks.
    The model is loaded lazily on first call to avoid importing
    sentence-transformers at module level.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._cross_encoder: object | None = None
        logger.info(
            "Reranker configured (model=%s, device=%s) — lazy loading",
            model_name,
            device or "auto",
        )

    def _load_model(self) -> None:
        """Load the CrossEncoder model on first use."""
        if self._cross_encoder is not None:
            return

        from sentence_transformers import CrossEncoder

        device = self._device
        if device is None:
            try:
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        logger.info(
            "Loading reranker model '%s' on device '%s'",
            self._model_name,
            device,
        )
        self._cross_encoder = CrossEncoder(self._model_name, device=device)
        logger.info("Reranker model loaded")

    def rerank(
        self,
        query: str,
        documents: list[RetrievalResult],
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Rerank documents by relevance to query. Returns top_k.

        Each document is scored by the cross-encoder against the query.
        Results are returned sorted by reranker score descending,
        with the ``score`` field updated to the cross-encoder score.

        Args:
            query:     The user query string.
            documents: Retrieval results to rerank.
            top_k:     Maximum number of results to return.

        Returns:
            Top-k documents sorted by cross-encoder relevance score.
        """
        if not documents:
            return []

        self._load_model()
        assert self._cross_encoder is not None

        pairs = [[query, doc.text] for doc in documents]
        scores = self._cross_encoder.predict(pairs)  # type: ignore[union-attr]

        # Pair each document with its reranker score.
        scored = list(zip(scores, documents, strict=True))
        scored.sort(key=lambda x: float(x[0]), reverse=True)

        reranked: list[RetrievalResult] = []
        for score, doc in scored[:top_k]:
            reranked.append(doc.model_copy(update={"score": float(score)}))

        logger.debug(
            "Reranked %d documents to top %d (best=%.4f, worst=%.4f)",
            len(documents),
            len(reranked),
            reranked[0].score if reranked else 0.0,
            reranked[-1].score if reranked else 0.0,
        )
        return reranked
