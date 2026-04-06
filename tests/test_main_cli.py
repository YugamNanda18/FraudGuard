"""Tests for the ingestion CLI entrypoint — all external calls are mocked."""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fraudai.ingestion.__main__ import (
    _build_parser,
    _print_result,
    _run,
    main,
)
from fraudai.ingestion.pipeline import PipelineResult

# ---------------------------------------------------------------------------
# _build_parser
# ---------------------------------------------------------------------------


class TestBuildParser:
    """Tests for the argument parser factory."""

    def test_returns_parser(self) -> None:
        parser = _build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_default_mode_is_incremental(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.mode == "incremental"

    def test_mode_full(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--mode", "full"])
        assert args.mode == "full"

    def test_doc_id_default_is_none(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.doc_id is None

    def test_doc_id_set(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--doc-id", "BOE-A-2010-6737"])
        assert args.doc_id == "BOE-A-2010-6737"

    def test_corpus_version_default_none(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.corpus_version is None

    def test_corpus_version_set(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--corpus-version", "2026-W14"])
        assert args.corpus_version == "2026-W14"

    def test_since_default_none(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.since is None

    def test_since_set(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--since", "20260101"])
        assert args.since == "20260101"


# ---------------------------------------------------------------------------
# _print_result
# ---------------------------------------------------------------------------


class TestPrintResult:
    """Tests for the _print_result display function."""

    def test_prints_result_no_errors(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = PipelineResult(
            corpus_version="2026-W14",
            documents_processed=10,
            chunks_generated=150,
            chunks_upserted=150,
            errors=[],
            duration_seconds=12.5,
        )
        _print_result(result)
        captured = capsys.readouterr()
        assert "2026-W14" in captured.out
        assert "10" in captured.out
        assert "150" in captured.out
        assert "12.50s" in captured.out
        # The summary table always shows "Errors: 0", but the detailed
        # error list section ("\nErrors:\n  - ...") should not appear.
        assert "\nErrors:\n" not in captured.out

    def test_prints_result_with_errors(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = PipelineResult(
            corpus_version="2026-W14",
            documents_processed=5,
            chunks_generated=40,
            chunks_upserted=35,
            errors=["Failed to process BOE-A-2010-0001"],
            duration_seconds=5.3,
        )
        _print_result(result)
        captured = capsys.readouterr()
        assert "Errors:" in captured.out
        assert "Failed to process BOE-A-2010-0001" in captured.out


# ---------------------------------------------------------------------------
# _run  — async core logic
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for the async _run function."""

    @patch("fraudai.ingestion.__main__.QdrantStore")
    @patch("fraudai.ingestion.__main__.EmbeddingGenerator")
    @patch("fraudai.ingestion.__main__.LegalChunker")
    @patch("fraudai.ingestion.__main__.BOETextExtractor")
    @patch("fraudai.ingestion.__main__.BOEClient")
    @patch("fraudai.ingestion.__main__.BOEIngestionPipeline")
    async def test_run_single_doc(
        self,
        mock_pipeline_cls: MagicMock,
        mock_boe_client_cls: MagicMock,
        mock_extractor_cls: MagicMock,
        mock_chunker_cls: MagicMock,
        mock_embedder_cls: MagicMock,
        mock_store_cls: MagicMock,
    ) -> None:
        mock_pipeline = AsyncMock()
        mock_pipeline.process_document = AsyncMock(return_value=42)
        mock_pipeline_cls.return_value = mock_pipeline

        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_boe_client_cls.return_value = mock_client

        args = argparse.Namespace(
            doc_id="BOE-A-2010-6737",
            mode="incremental",
            corpus_version=None,
            since=None,
        )

        exit_code = await _run(args)
        assert exit_code == 0
        mock_pipeline.process_document.assert_awaited_once_with("BOE-A-2010-6737")
        mock_client.close.assert_awaited_once()

    @patch("fraudai.ingestion.__main__.QdrantStore")
    @patch("fraudai.ingestion.__main__.EmbeddingGenerator")
    @patch("fraudai.ingestion.__main__.LegalChunker")
    @patch("fraudai.ingestion.__main__.BOETextExtractor")
    @patch("fraudai.ingestion.__main__.BOEClient")
    @patch("fraudai.ingestion.__main__.BOEIngestionPipeline")
    async def test_run_full_mode(
        self,
        mock_pipeline_cls: MagicMock,
        mock_boe_client_cls: MagicMock,
        mock_extractor_cls: MagicMock,
        mock_chunker_cls: MagicMock,
        mock_embedder_cls: MagicMock,
        mock_store_cls: MagicMock,
    ) -> None:
        result = PipelineResult(
            corpus_version="2026-W14",
            documents_processed=10,
            chunks_generated=150,
            chunks_upserted=150,
            errors=[],
            duration_seconds=12.5,
        )
        mock_pipeline = AsyncMock()
        mock_pipeline.run_full = AsyncMock(return_value=result)
        mock_pipeline_cls.return_value = mock_pipeline

        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_boe_client_cls.return_value = mock_client

        args = argparse.Namespace(
            doc_id=None,
            mode="full",
            corpus_version=None,
            since=None,
        )

        exit_code = await _run(args)
        assert exit_code == 0
        mock_pipeline.run_full.assert_awaited_once()
        mock_client.close.assert_awaited_once()

    @patch("fraudai.ingestion.__main__.QdrantStore")
    @patch("fraudai.ingestion.__main__.EmbeddingGenerator")
    @patch("fraudai.ingestion.__main__.LegalChunker")
    @patch("fraudai.ingestion.__main__.BOETextExtractor")
    @patch("fraudai.ingestion.__main__.BOEClient")
    @patch("fraudai.ingestion.__main__.BOEIngestionPipeline")
    async def test_run_incremental_mode(
        self,
        mock_pipeline_cls: MagicMock,
        mock_boe_client_cls: MagicMock,
        mock_extractor_cls: MagicMock,
        mock_chunker_cls: MagicMock,
        mock_embedder_cls: MagicMock,
        mock_store_cls: MagicMock,
    ) -> None:
        result = PipelineResult(
            corpus_version="2026-W14",
            documents_processed=3,
            chunks_generated=40,
            chunks_upserted=40,
            errors=[],
            duration_seconds=5.0,
        )
        mock_pipeline = AsyncMock()
        mock_pipeline.run_incremental = AsyncMock(return_value=result)
        mock_pipeline_cls.return_value = mock_pipeline

        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_boe_client_cls.return_value = mock_client

        args = argparse.Namespace(
            doc_id=None,
            mode="incremental",
            corpus_version=None,
            since="20260101",
        )

        exit_code = await _run(args)
        assert exit_code == 0
        mock_pipeline.run_incremental.assert_awaited_once_with(since_date="20260101")
        mock_client.close.assert_awaited_once()

    @patch("fraudai.ingestion.__main__.QdrantStore")
    @patch("fraudai.ingestion.__main__.EmbeddingGenerator")
    @patch("fraudai.ingestion.__main__.LegalChunker")
    @patch("fraudai.ingestion.__main__.BOETextExtractor")
    @patch("fraudai.ingestion.__main__.BOEClient")
    @patch("fraudai.ingestion.__main__.BOEIngestionPipeline")
    async def test_run_full_with_errors_returns_1(
        self,
        mock_pipeline_cls: MagicMock,
        mock_boe_client_cls: MagicMock,
        mock_extractor_cls: MagicMock,
        mock_chunker_cls: MagicMock,
        mock_embedder_cls: MagicMock,
        mock_store_cls: MagicMock,
    ) -> None:
        result = PipelineResult(
            corpus_version="2026-W14",
            documents_processed=5,
            chunks_generated=40,
            chunks_upserted=35,
            errors=["Error 1"],
            duration_seconds=5.0,
        )
        mock_pipeline = AsyncMock()
        mock_pipeline.run_full = AsyncMock(return_value=result)
        mock_pipeline_cls.return_value = mock_pipeline

        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_boe_client_cls.return_value = mock_client

        args = argparse.Namespace(
            doc_id=None,
            mode="full",
            corpus_version=None,
            since=None,
        )

        exit_code = await _run(args)
        assert exit_code == 1

    @patch("fraudai.ingestion.__main__.QdrantStore")
    @patch("fraudai.ingestion.__main__.EmbeddingGenerator")
    @patch("fraudai.ingestion.__main__.LegalChunker")
    @patch("fraudai.ingestion.__main__.BOETextExtractor")
    @patch("fraudai.ingestion.__main__.BOEClient")
    @patch("fraudai.ingestion.__main__.BOEIngestionPipeline")
    async def test_run_always_closes_client(
        self,
        mock_pipeline_cls: MagicMock,
        mock_boe_client_cls: MagicMock,
        mock_extractor_cls: MagicMock,
        mock_chunker_cls: MagicMock,
        mock_embedder_cls: MagicMock,
        mock_store_cls: MagicMock,
    ) -> None:
        """BOEClient.close() should always be called even on failure."""
        mock_pipeline = AsyncMock()
        mock_pipeline.run_full = AsyncMock(side_effect=RuntimeError("boom"))
        mock_pipeline_cls.return_value = mock_pipeline

        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        mock_boe_client_cls.return_value = mock_client

        args = argparse.Namespace(
            doc_id=None,
            mode="full",
            corpus_version=None,
            since=None,
        )

        with pytest.raises(RuntimeError, match="boom"):
            await _run(args)

        mock_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# main — sync entrypoint
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() sync entry point."""

    @patch("fraudai.ingestion.__main__.sys")
    @patch("fraudai.ingestion.__main__.asyncio")
    @patch("fraudai.ingestion.__main__._build_parser")
    @patch("fraudai.ingestion.__main__._configure_logging")
    def test_main_calls_asyncio_run(
        self,
        mock_logging: MagicMock,
        mock_parser_fn: MagicMock,
        mock_asyncio: MagicMock,
        mock_sys: MagicMock,
    ) -> None:
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = argparse.Namespace(
            doc_id=None, mode="incremental", corpus_version=None, since=None
        )
        mock_parser_fn.return_value = mock_parser
        mock_asyncio.run.return_value = 0

        main()

        mock_logging.assert_called_once()
        mock_asyncio.run.assert_called_once()
        mock_sys.exit.assert_called_once_with(0)

    @patch("fraudai.ingestion.__main__.sys")
    @patch("fraudai.ingestion.__main__.asyncio")
    @patch("fraudai.ingestion.__main__._build_parser")
    @patch("fraudai.ingestion.__main__._configure_logging")
    def test_main_keyboard_interrupt(
        self,
        mock_logging: MagicMock,
        mock_parser_fn: MagicMock,
        mock_asyncio: MagicMock,
        mock_sys: MagicMock,
    ) -> None:
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = argparse.Namespace(
            doc_id=None, mode="incremental", corpus_version=None, since=None
        )
        mock_parser_fn.return_value = mock_parser
        mock_asyncio.run.side_effect = KeyboardInterrupt

        main()

        mock_sys.exit.assert_called_once_with(130)
