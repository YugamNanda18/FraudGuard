"""Semantic chunker for structured legal documents from the BOE."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from fraudai.ingestion.boe_client import BOEDocumentMeta  # noqa: TC001
from fraudai.ingestion.text_extractor import ExtractedArticle, ExtractedDocument  # noqa: TC001

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class ChunkMetadata(BaseModel):
    """Metadata attached to each legal chunk for vector store indexing."""

    boe_id: str
    norma_titulo: str
    articulo: str  # "Art. 18" or "Disposicion adicional primera"
    seccion: str  # "Titulo III, Capitulo II"
    rango: str  # "Ley", "Real Decreto"
    departamento: str
    materia_codigo: str  # First materia code (empty string if none)
    fecha_publicacion: str
    fecha_consolidacion: str
    estado_consolidacion: str


class LegalChunk(BaseModel):
    """A single semantic chunk of legal text with metadata."""

    text: str
    metadata: ChunkMetadata


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------

_DEFAULT_MAX_TOKENS = 2000


class LegalChunker:
    """Semantic chunker for legal texts. Base unit: one article = one chunk.

    Articles that exceed ``max_tokens`` are subdivided by paragraphs while
    preserving a context prefix.  The preamble is chunked by long paragraphs.
    Dispositions and annexes are individual chunks.
    """

    def __init__(
        self,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        overlap_context: bool = True,
    ) -> None:
        self._max_tokens = max_tokens
        self._overlap_context = overlap_context

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_document(
        self,
        doc: ExtractedDocument,
        doc_meta: BOEDocumentMeta,
    ) -> list[LegalChunk]:
        """Generate semantic chunks from a parsed legal document.

        Args:
            doc: Structured document produced by ``BOETextExtractor``.
            doc_meta: BOE metadata for the source document.

        Returns:
            List of ``LegalChunk`` objects ready for vector store ingestion.
        """
        chunks: list[LegalChunk] = []
        base_meta = self._build_base_metadata(doc, doc_meta)

        # Preamble
        if doc.preambulo:
            chunks.extend(self._chunk_preambulo(doc.preambulo, doc.titulo, base_meta))

        # Articles
        for art in doc.articulos:
            chunks.extend(self._chunk_article(art, doc.titulo, base_meta))

        # Dispositions
        for disp in doc.disposiciones:
            chunks.extend(self._chunk_article(disp, doc.titulo, base_meta))

        # Annexes
        for idx, anexo_text in enumerate(doc.anexos, start=1):
            meta = base_meta.model_copy(update={"articulo": f"Anexo {idx}", "seccion": ""})
            prefix = self._context_prefix(doc.titulo, "", f"Anexo {idx}")
            chunks.extend(self._split_long_text(anexo_text, prefix, meta))

        logger.info("Chunked document %s into %d chunks", doc_meta.identificador, len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # Internal methods
    # ------------------------------------------------------------------

    @staticmethod
    def _build_base_metadata(
        doc: ExtractedDocument,
        doc_meta: BOEDocumentMeta,
    ) -> ChunkMetadata:
        """Create a base metadata object from document and BOE metadata.

        The authoritative title comes from ``doc_meta.titulo`` (parsed from
        the BOE XML ``<metadatos>`` section) because the text extractor
        often receives plain-text content without HTML heading tags, which
        causes ``ExtractedDocument.titulo`` to be empty or unreliable.
        We fall back to ``doc.titulo`` only when the metadata title is
        missing.
        """
        materia_codigo = ""
        if doc_meta.materias:
            materia_codigo = doc_meta.materias[0]

        # Prefer the BOE metadata title (always present in XML) over the
        # extractor title (may be empty when <texto> lacks HTML headings).
        norma_titulo = doc_meta.titulo or doc.titulo

        return ChunkMetadata(
            boe_id=doc_meta.identificador,
            norma_titulo=norma_titulo,
            articulo="",
            seccion="",
            rango=doc_meta.rango,
            departamento=doc_meta.departamento,
            materia_codigo=materia_codigo,
            fecha_publicacion=doc_meta.fecha_publicacion,
            fecha_consolidacion=doc_meta.fecha_vigencia,
            estado_consolidacion=doc_meta.estado_consolidacion,
        )

    def _chunk_preambulo(
        self,
        preambulo: str,
        norma_titulo: str,
        base_meta: ChunkMetadata,
    ) -> list[LegalChunk]:
        """Chunk the preamble by long paragraphs."""
        meta = base_meta.model_copy(update={"articulo": "Preambulo", "seccion": ""})
        prefix = self._context_prefix(norma_titulo, "", "Preambulo")
        return self._split_long_text(preambulo, prefix, meta)

    def _chunk_article(
        self,
        article: ExtractedArticle,
        norma_titulo: str,
        base_meta: ChunkMetadata,
    ) -> list[LegalChunk]:
        """Chunk a single article or disposition."""
        meta = base_meta.model_copy(
            update={
                "articulo": article.numero,
                "seccion": article.seccion,
            }
        )

        prefix = self._context_prefix(norma_titulo, article.seccion, article.numero)

        # Build the full article text including title
        parts: list[str] = []
        if article.titulo:
            parts.append(f"{article.numero}. {article.titulo}")
        else:
            parts.append(f"{article.numero}.")
        if article.contenido:
            parts.append(article.contenido)
        full_text = "\n\n".join(parts)

        token_count = _estimate_tokens(full_text)
        if token_count <= self._max_tokens:
            text = f"{prefix} {full_text}" if self._overlap_context else full_text
            return [LegalChunk(text=text, metadata=meta)]

        # Article exceeds max_tokens: subdivide by paragraphs
        return self._split_long_text(full_text, prefix, meta)

    def _split_long_text(
        self,
        text: str,
        prefix: str,
        meta: ChunkMetadata,
    ) -> list[LegalChunk]:
        """Split text that exceeds max_tokens into paragraph-based sub-chunks."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        chunks: list[LegalChunk] = []
        current_parts: list[str] = []
        current_tokens = 0
        prefix_tokens = _estimate_tokens(prefix) if self._overlap_context else 0

        for paragraph in paragraphs:
            para_tokens = _estimate_tokens(paragraph)

            # If a single paragraph exceeds max_tokens on its own, include it
            # as its own chunk (we do not break mid-sentence).
            if para_tokens > self._max_tokens:
                # Flush accumulated content first
                if current_parts:
                    chunk_text = self._assemble_chunk(prefix, current_parts)
                    chunks.append(LegalChunk(text=chunk_text, metadata=meta))
                    current_parts = []
                    current_tokens = 0

                chunk_text = self._assemble_chunk(prefix, [paragraph])
                chunks.append(LegalChunk(text=chunk_text, metadata=meta))
                continue

            if current_tokens + para_tokens + prefix_tokens > self._max_tokens and current_parts:
                chunk_text = self._assemble_chunk(prefix, current_parts)
                chunks.append(LegalChunk(text=chunk_text, metadata=meta))
                current_parts = []
                current_tokens = 0

            current_parts.append(paragraph)
            current_tokens += para_tokens

        # Flush remainder
        if current_parts:
            chunk_text = self._assemble_chunk(prefix, current_parts)
            chunks.append(LegalChunk(text=chunk_text, metadata=meta))

        return chunks

    def _assemble_chunk(self, prefix: str, parts: list[str]) -> str:
        """Join parts with optional context prefix."""
        body = "\n\n".join(parts)
        if self._overlap_context and prefix:
            return f"{prefix} {body}"
        return body

    @staticmethod
    def _context_prefix(norma_titulo: str, seccion: str, articulo: str) -> str:
        """Build the context prefix string: ``[Ley 10/2010 -- Titulo III -- Capitulo II]``."""
        parts = [p for p in (norma_titulo, seccion, articulo) if p]
        return f"[{' -- '.join(parts)}]"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _estimate_tokens(text: str) -> int:
    """Fast token estimation via whitespace splitting.

    This is intentionally approximate -- we do not need a tokenizer for
    chunking boundary decisions.
    """
    return len(text.split())
