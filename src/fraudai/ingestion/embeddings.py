"""Embedding generation for legal document chunks.

Produces dense (BGE-M3, 1024-dim) and sparse (BM25-style) representations
for hybrid search in Qdrant.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sparse fallback via scikit-learn TF-IDF
# ---------------------------------------------------------------------------


class _TFIDFSparseEncoder:
    """Lightweight sparse encoder using TF-IDF as BM25 approximation.

    Used when the loaded model does not natively support sparse output
    (e.g. sentence-transformers wrapper of BGE-M3 lacks ``return_sparse``).
    """

    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            max_features=30_000,
            sublinear_tf=True,
            dtype=np.float32,
        )
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        self._vectorizer.fit(corpus)
        self._fitted = True

    def encode(self, texts: list[str]) -> list[dict[str, Any]]:
        """Return sparse representations as ``{"indices": [...], "values": [...]}``."""
        if not self._fitted:
            self.fit(texts)
        matrix = self._vectorizer.transform(texts)
        results: list[dict[str, Any]] = []
        for row_idx in range(matrix.shape[0]):
            row = matrix.getrow(row_idx)
            indices = row.indices.tolist()
            values = row.data.tolist()
            results.append({"indices": indices, "values": values})
        return results


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class EmbeddingGenerator:
    """Generates dense (BGE-M3) and sparse (BM25) embeddings for legal chunks.

    Dense embeddings are produced via ``sentence-transformers``.  For sparse
    representations the class first attempts to use FlagEmbedding's native
    multi-representation output.  If that library is not installed or fails,
    it falls back to a TF-IDF sparse encoder from scikit-learn.
    """

    DENSE_DIM = 1024

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        if device is None:
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        self._device = device
        self._batch_size = batch_size
        self._model_name = model_name

        # Try FlagEmbedding first (native multi-vector support)
        self._flag_model: Any | None = None
        self._st_model: SentenceTransformer | None = None
        self._sparse_encoder: _TFIDFSparseEncoder | None = None

        try:
            from FlagEmbedding import BGEM3FlagModel  # type: ignore[import-untyped]

            logger.info(
                "Loading FlagEmbedding model '%s' on device '%s'",
                model_name,
                device,
            )
            self._flag_model = BGEM3FlagModel(
                model_name,
                use_fp16=(device == "cuda"),
            )
            logger.info("FlagEmbedding model loaded — native dense+sparse available")
        except (ImportError, Exception) as exc:
            logger.info(
                "FlagEmbedding not available (%s), falling back to "
                "sentence-transformers + TF-IDF sparse",
                exc,
            )
            from sentence_transformers import SentenceTransformer

            self._st_model = SentenceTransformer(model_name, device=device)
            self._sparse_encoder = _TFIDFSparseEncoder()
            logger.info(
                "SentenceTransformer model '%s' loaded on '%s'",
                model_name,
                device,
            )

    # ------------------------------------------------------------------
    # Dense
    # ------------------------------------------------------------------

    def encode_dense(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embeddings of ``DENSE_DIM`` dimensions.

        Processes texts in batches of ``self._batch_size``.
        """
        if not texts:
            return []

        if self._flag_model is not None:
            output = self._flag_model.encode(
                texts,
                batch_size=self._batch_size,
                max_length=8192,
            )
            # FlagEmbedding returns a dict with 'dense_vecs' key
            dense: np.ndarray = output["dense_vecs"]
            return dense.tolist()

        assert self._st_model is not None
        embeddings = self._st_model.encode(
            texts,
            batch_size=self._batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Sparse
    # ------------------------------------------------------------------

    def encode_sparse(self, texts: list[str]) -> list[dict[str, Any]]:
        """Generate sparse BM25-style representations.

        Returns a list of ``{"indices": [...], "values": [...]}``.
        """
        if not texts:
            return []

        if self._flag_model is not None:
            output = self._flag_model.encode(
                texts,
                batch_size=self._batch_size,
                max_length=8192,
                return_sparse=True,
            )
            lexical_weights: list[dict[str, float]] = output["lexical_weights"]
            results: list[dict[str, Any]] = []
            for token_weights in lexical_weights:
                indices = [int(k) for k in token_weights.keys()]
                values = list(token_weights.values())
                results.append({"indices": indices, "values": values})
            return results

        assert self._sparse_encoder is not None
        return self._sparse_encoder.encode(texts)

    # ------------------------------------------------------------------
    # Combined
    # ------------------------------------------------------------------

    def encode(self, texts: list[str]) -> list[dict[str, Any]]:
        """Generate both dense and sparse representations.

        Returns a list of dicts, each containing:
            ``{"dense": list[float], "sparse": {"indices": [...], "values": [...]}}``.
        """
        if not texts:
            return []

        dense_vecs = self.encode_dense(texts)
        sparse_vecs = self.encode_sparse(texts)

        return [
            {"dense": d, "sparse": s}
            for d, s in zip(dense_vecs, sparse_vecs)
        ]
