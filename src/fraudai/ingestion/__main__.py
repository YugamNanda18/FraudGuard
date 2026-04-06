"""CLI entrypoint for the BOE ingestion pipeline.

Usage:
    python -m fraudai.ingestion                          # incremental (default)
    python -m fraudai.ingestion --mode full              # full re-index
    python -m fraudai.ingestion --doc-id BOE-A-2010-6737 # single document
    python -m fraudai.ingestion --corpus-version 2026-W14
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from fraudai.core.config import settings
from fraudai.ingestion.boe_client import BOEClient
from fraudai.ingestion.chunker import LegalChunker
from fraudai.ingestion.embeddings import EmbeddingGenerator
from fraudai.ingestion.pipeline import BOEIngestionPipeline, PipelineResult
from fraudai.ingestion.text_extractor import BOETextExtractor
from fraudai.rag.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fraudai.ingestion",
        description="BOE Ingestion Pipeline — download, chunk, embed, and index legislation.",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="incremental",
        help="Run mode: 'full' reprocesses everything; 'incremental' only new docs (default).",
    )
    parser.add_argument(
        "--doc-id",
        type=str,
        default=None,
        help="Process a single document by BOE identifier (e.g. BOE-A-2010-6737).",
    )
    parser.add_argument(
        "--corpus-version",
        type=str,
        default=None,
        help="Override the auto-generated corpus version label.",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Start date for incremental mode (AAAAMMDD format).",
    )
    return parser


def _print_result(result: PipelineResult) -> None:
    print(f"\n{'=' * 60}")
    print(f"  Corpus version:       {result.corpus_version}")
    print(f"  Documents processed:  {result.documents_processed}")
    print(f"  Chunks generated:     {result.chunks_generated}")
    print(f"  Chunks upserted:      {result.chunks_upserted}")
    print(f"  Errors:               {len(result.errors)}")
    print(f"  Duration:             {result.duration_seconds:.2f}s")
    print(f"{'=' * 60}")
    if result.errors:
        print("\nErrors:")
        for err in result.errors:
            print(f"  - {err}")


async def _run(args: argparse.Namespace) -> int:
    boe_client = BOEClient()
    extractor = BOETextExtractor()
    chunker = LegalChunker()
    embedder = EmbeddingGenerator()
    store = QdrantStore(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
    )

    pipeline = BOEIngestionPipeline(
        boe_client=boe_client,
        extractor=extractor,
        chunker=chunker,
        embedder=embedder,
        store=store,
        corpus_version=args.corpus_version,
    )

    try:
        if args.doc_id:
            logger.info("Processing single document: %s", args.doc_id)
            n_chunks = await pipeline.process_document(args.doc_id)
            print(f"\nDocument {args.doc_id}: {n_chunks} chunks upserted.")
            return 0

        if args.mode == "full":
            result = await pipeline.run_full()
        else:
            result = await pipeline.run_incremental(since_date=args.since)

        _print_result(result)
        return 1 if result.errors else 0

    finally:
        await boe_client.close()


def main() -> None:
    _configure_logging()
    parser = _build_parser()
    args = parser.parse_args()
    try:
        exit_code = asyncio.run(_run(args))
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        exit_code = 130
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
