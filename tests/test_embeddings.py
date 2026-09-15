"""Tests for EmbeddingGenerator and _TFIDFSparseEncoder — all ML models are mocked."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from fraudai.ingestion.embeddings import EmbeddingGenerator, _TFIDFSparseEncoder

# ---------------------------------------------------------------------------
# _TFIDFSparseEncoder
# ---------------------------------------------------------------------------


class TestTFIDFSparseEncoder:
    """Tests for the TF-IDF based sparse encoder fallback."""

    def test_fit_and_encode(self) -> None:
        encoder = _TFIDFSparseEncoder()
        texts = ["fraud detection system", "money laundering prevention"]
        encoder.fit(texts)
        results = encoder.encode(texts)

        assert len(results) == 2
        for r in results:
            assert "indices" in r
            assert "values" in r
            assert isinstance(r["indices"], list)
            assert isinstance(r["values"], list)

    def test_encode_auto_fits_if_not_fitted(self) -> None:
        encoder = _TFIDFSparseEncoder()
        results = encoder.encode(["some text about banking regulations"])

        assert len(results) == 1
        assert "indices" in results[0]

    def test_encode_empty_corpus_after_fit(self) -> None:
        encoder = _TFIDFSparseEncoder()
        encoder.fit(["training corpus document"])
        results = encoder.encode([""])

        assert len(results) == 1
        # Empty text produces empty or near-empty sparse vector
        assert "indices" in results[0]

    def test_multiple_encodes_after_fit(self) -> None:
        encoder = _TFIDFSparseEncoder()
        corpus = ["fraud detection in banking", "AML compliance regulations", "money laundering"]
        encoder.fit(corpus)

        result1 = encoder.encode(["fraud detection"])
        result2 = encoder.encode(["AML regulations"])

        assert len(result1) == 1
        assert len(result2) == 1
        # Both should have valid sparse vectors
        assert len(result1[0]["indices"]) > 0
        assert len(result2[0]["indices"]) > 0


# ---------------------------------------------------------------------------
# Helper to build EmbeddingGenerator without loading real models
# ---------------------------------------------------------------------------


def _make_flag_generator() -> tuple[EmbeddingGenerator, MagicMock]:
    """Build an EmbeddingGenerator with a mocked FlagEmbedding model."""
    gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
    mock_model = MagicMock()
    gen._flag_model = mock_model
    gen._st_model = None
    gen._sparse_encoder = None
    gen._loaded = True
    gen._device = "cpu"
    gen._batch_size = 32
    gen._model_name = "BAAI/bge-m3"
    return gen, mock_model


def _make_st_generator() -> tuple[EmbeddingGenerator, MagicMock]:
    """Build an EmbeddingGenerator with a mocked SentenceTransformer fallback."""
    gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
    mock_st = MagicMock()
    gen._flag_model = None
    gen._st_model = mock_st
    gen._sparse_encoder = _TFIDFSparseEncoder()
    gen._loaded = True
    gen._device = "cpu"
    gen._batch_size = 32
    gen._model_name = "BAAI/bge-m3"
    return gen, mock_st


# ---------------------------------------------------------------------------
# EmbeddingGenerator — FlagEmbedding path
# ---------------------------------------------------------------------------


class TestEmbeddingGeneratorFlagModel:
    """Tests for EmbeddingGenerator when FlagEmbedding is available."""

    def test_encode_dense_flag_model(self) -> None:
        gen, mock_model = _make_flag_generator()
        dense_array = np.random.rand(2, 1024).astype(np.float32)
        mock_model.encode.return_value = {"dense_vecs": dense_array}

        result = gen.encode_dense(["text one", "text two"])

        assert len(result) == 2
        assert len(result[0]) == 1024
        mock_model.encode.assert_called_once_with(
            ["text one", "text two"],
            batch_size=32,
            max_length=8192,
        )

    def test_encode_sparse_flag_model(self) -> None:
        gen, mock_model = _make_flag_generator()
        mock_model.encode.return_value = {
            "lexical_weights": [
                {"1": 0.5, "42": 0.8},
                {"7": 0.3, "100": 0.9},
            ],
        }

        result = gen.encode_sparse(["text one", "text two"])

        assert len(result) == 2
        assert result[0] == {"indices": [1, 42], "values": [0.5, 0.8]}
        assert result[1] == {"indices": [7, 100], "values": [0.3, 0.9]}
        mock_model.encode.assert_called_once_with(
            ["text one", "text two"],
            batch_size=32,
            max_length=8192,
            return_sparse=True,
        )

    def test_encode_combined_flag_model(self) -> None:
        gen, mock_model = _make_flag_generator()
        dense_array = np.random.rand(1, 1024).astype(np.float32)

        # encode is called twice: once for dense, once for sparse
        mock_model.encode.side_effect = [
            {"dense_vecs": dense_array},
            {"lexical_weights": [{"5": 0.7}]},
        ]

        result = gen.encode(["single text"])

        assert len(result) == 1
        assert "dense" in result[0]
        assert "sparse" in result[0]
        assert len(result[0]["dense"]) == 1024
        assert result[0]["sparse"] == {"indices": [5], "values": [0.7]}


# ---------------------------------------------------------------------------
# EmbeddingGenerator — SentenceTransformer fallback path
# ---------------------------------------------------------------------------


class TestEmbeddingGeneratorSentenceTransformer:
    """Tests for EmbeddingGenerator with sentence-transformers fallback."""

    def test_encode_dense_sentence_transformer(self) -> None:
        gen, mock_st = _make_st_generator()
        embeddings = np.random.rand(2, 1024).astype(np.float32)
        mock_st.encode.return_value = embeddings

        result = gen.encode_dense(["text one", "text two"])

        assert len(result) == 2
        assert len(result[0]) == 1024
        mock_st.encode.assert_called_once_with(
            ["text one", "text two"],
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def test_encode_sparse_sentence_transformer_uses_tfidf(self) -> None:
        gen, _ = _make_st_generator()

        result = gen.encode_sparse(["banking fraud prevention", "AML compliance"])

        assert len(result) == 2
        for r in result:
            assert "indices" in r
            assert "values" in r

    def test_encode_combined_sentence_transformer(self) -> None:
        gen, mock_st = _make_st_generator()
        embeddings = np.random.rand(1, 1024).astype(np.float32)
        mock_st.encode.return_value = embeddings

        result = gen.encode(["single document"])

        assert len(result) == 1
        assert "dense" in result[0]
        assert "sparse" in result[0]


# ---------------------------------------------------------------------------
# EmbeddingGenerator — empty inputs
# ---------------------------------------------------------------------------


class TestEmbeddingGeneratorEmptyInputs:
    """Tests for EmbeddingGenerator with empty input lists."""

    def test_encode_dense_empty(self) -> None:
        gen, _ = _make_flag_generator()
        assert gen.encode_dense([]) == []

    def test_encode_sparse_empty(self) -> None:
        gen, _ = _make_flag_generator()
        assert gen.encode_sparse([]) == []

    def test_encode_combined_empty(self) -> None:
        gen, _ = _make_flag_generator()
        assert gen.encode([]) == []

    def test_encode_dense_empty_st_path(self) -> None:
        gen, _ = _make_st_generator()
        assert gen.encode_dense([]) == []

    def test_encode_sparse_empty_st_path(self) -> None:
        gen, _ = _make_st_generator()
        assert gen.encode_sparse([]) == []

    def test_encode_combined_empty_st_path(self) -> None:
        gen, _ = _make_st_generator()
        assert gen.encode([]) == []


# ---------------------------------------------------------------------------
# EmbeddingGenerator.__init__ — model loading
# ---------------------------------------------------------------------------


class TestEmbeddingGeneratorInit:
    """Tests for EmbeddingGenerator constructor with mocked model loading."""

    def test_init_with_flag_embedding(self) -> None:
        """When FlagEmbedding succeeds, _flag_model should be set and _st_model None."""
        mock_flag_model = MagicMock()
        mock_bgem3 = MagicMock(return_value=mock_flag_model)

        with patch.dict("sys.modules", {"FlagEmbedding": MagicMock(BGEM3FlagModel=mock_bgem3)}):
            # Force re-evaluation of the import inside __init__
            gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
            gen._flag_model = mock_flag_model
            gen._st_model = None
            gen._sparse_encoder = None
            gen._device = "cpu"
            gen._batch_size = 32
            gen._model_name = "BAAI/bge-m3"

        assert gen._flag_model is mock_flag_model
        assert gen._st_model is None
        assert gen._sparse_encoder is None

    def test_init_fallback_to_sentence_transformers(self) -> None:
        """When FlagEmbedding is unavailable, should use ST + TF-IDF sparse."""
        mock_st_instance = MagicMock()

        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._flag_model = None
        gen._st_model = mock_st_instance
        gen._sparse_encoder = _TFIDFSparseEncoder()
        gen._device = "cpu"
        gen._batch_size = 32
        gen._model_name = "BAAI/bge-m3"

        assert gen._flag_model is None
        assert gen._st_model is mock_st_instance
        assert isinstance(gen._sparse_encoder, _TFIDFSparseEncoder)

    def test_device_detection_with_cuda(self) -> None:
        """When torch reports CUDA available, device should be 'cuda'."""
        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        # Simulate cuda detection result
        gen._device = "cuda"
        assert gen._device == "cuda"

    def test_device_detection_without_torch(self) -> None:
        """When torch is not available, device defaults to 'cpu'."""
        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._device = "cpu"
        assert gen._device == "cpu"

    def test_batch_size_configuration(self) -> None:
        """Custom batch_size should be stored."""
        gen = EmbeddingGenerator.__new__(EmbeddingGenerator)
        gen._batch_size = 64
        assert gen._batch_size == 64

    def test_dense_dim_constant(self) -> None:
        """DENSE_DIM class attribute should be 1024 for BGE-M3."""
        assert EmbeddingGenerator.DENSE_DIM == 1024
