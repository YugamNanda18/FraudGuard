"""Tests for LegalChunker with extracted document fixtures."""

from __future__ import annotations

import pytest

from fraudai.ingestion.boe_client import BOEDocumentMeta
from fraudai.ingestion.chunker import ChunkMetadata, LegalChunk, LegalChunker
from fraudai.ingestion.text_extractor import ExtractedArticle, ExtractedDocument

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SHORT_CONTENT = "Los sujetos obligados identificaran a cuantas personas fisicas o juridicas."

_LONG_PARAGRAPH_TEMPLATE = (
    "El presente articulo establece las condiciones y requisitos que deben "
    "cumplir los sujetos obligados en materia de prevencion del blanqueo de "
    "capitales, incluyendo la verificacion de la identidad del cliente, la "
    "obtencion de informacion sobre el proposito y la naturaleza prevista de "
    "la relacion de negocios, la realizacion de un seguimiento continuo de "
    "la relacion de negocios y el examen minucioso de las operaciones "
    "realizadas a fin de garantizar que sean coherentes con el conocimiento "
    "que tenga el sujeto obligado del cliente y de su perfil empresarial y "
    "de riesgo, incluido cuando sea necesario el origen de los fondos "
    "y la garantia de que los documentos datos o informaciones de que se "
    "disponga esten actualizados. "
)


def _make_doc_meta(**overrides: str) -> BOEDocumentMeta:
    defaults = {
        "identificador": "BOE-A-2010-6737",
        "titulo": "Ley 10/2010, de 28 de abril, de prevencion del blanqueo.",
        "fecha_publicacion": "20100429",
        "fecha_disposicion": "20100428",
        "rango": "Ley",
        "departamento": "Jefatura del Estado",
        "materias": ["Activos financieros"],
        "fecha_vigencia": "20100430",
        "estado_consolidacion": "Finalizado",
    }
    defaults.update(overrides)
    return BOEDocumentMeta(**defaults)


def _make_small_doc() -> ExtractedDocument:
    """A small law with 5 articles, 1 disposition, and a preamble."""
    articles = []
    for i in range(1, 6):
        articles.append(
            ExtractedArticle(
                numero=f"Art. {i}",
                titulo=f"Titulo del articulo {i}",
                contenido=f"Contenido del articulo {i}. {_SHORT_CONTENT}",
                seccion="Titulo I, Capitulo I" if i <= 3 else "Titulo II",
            )
        )
    return ExtractedDocument(
        titulo="Ley 10/2010, de prevencion del blanqueo de capitales.",
        preambulo="Exposicion de motivos. Las Cortes Generales han aprobado esta ley.",
        articulos=articles,
        disposiciones=[
            ExtractedArticle(
                numero="Disposicion adicional primera",
                titulo="Aplicacion supletoria",
                contenido="En lo no previsto se aplicara la Ley 30/1992.",
                seccion="",
            ),
        ],
        anexos=["ANEXO I\n\n1. Auditores.\n\n2. Contables."],
    )


def _make_long_article_doc(word_count: int = 2500) -> ExtractedDocument:
    """A document with a single article that exceeds max_tokens."""
    # Build text from repeated paragraph template to reach desired length
    paragraphs: list[str] = []
    current_words = 0
    idx = 0
    while current_words < word_count:
        idx += 1
        para = f"Apartado {idx}. {_LONG_PARAGRAPH_TEMPLATE}"
        paragraphs.append(para)
        current_words += len(para.split())

    content = "\n\n".join(paragraphs)
    return ExtractedDocument(
        titulo="Ley 10/2010, de prevencion del blanqueo.",
        preambulo="",
        articulos=[
            ExtractedArticle(
                numero="Art. 7",
                titulo="Medidas de diligencia debida",
                contenido=content,
                seccion="Titulo I, Capitulo III",
            )
        ],
        disposiciones=[],
        anexos=[],
    )


@pytest.fixture
def chunker() -> LegalChunker:
    return LegalChunker(max_tokens=2000, overlap_context=True)


@pytest.fixture
def small_doc() -> ExtractedDocument:
    return _make_small_doc()


@pytest.fixture
def long_doc() -> ExtractedDocument:
    return _make_long_article_doc(2500)


@pytest.fixture
def doc_meta() -> BOEDocumentMeta:
    return _make_doc_meta()


# ---------------------------------------------------------------------------
# Tests: small document (5 articles)
# ---------------------------------------------------------------------------


class TestChunkerSmallDocument:
    """Tests for a small, well-structured document."""

    def test_chunk_count(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        # 1 preambulo + 5 articles + 1 disposition + 1 annex = 8
        assert len(chunks) == 8

    def test_chunk_types(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        articulos = [c for c in chunks if c.metadata.articulo.startswith("Art.")]
        preambulos = [c for c in chunks if c.metadata.articulo == "Preambulo"]
        disposiciones = [c for c in chunks if "Disposicion" in c.metadata.articulo]
        anexos = [c for c in chunks if "Anexo" in c.metadata.articulo]
        assert len(articulos) == 5
        assert len(preambulos) == 1
        assert len(disposiciones) == 1
        assert len(anexos) == 1

    def test_each_chunk_has_text(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert chunk.text.strip() != ""

    def test_context_prefix_present(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        art1_chunk = next(c for c in chunks if c.metadata.articulo == "Art. 1")
        assert art1_chunk.text.startswith("[")
        assert "Ley 10/2010" in art1_chunk.text
        assert "Art. 1" in art1_chunk.text

    def test_context_prefix_disabled(
        self, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunker_no_ctx = LegalChunker(max_tokens=2000, overlap_context=False)
        chunks = chunker_no_ctx.chunk_document(small_doc, doc_meta)
        art1_chunk = next(c for c in chunks if c.metadata.articulo == "Art. 1")
        assert not art1_chunk.text.startswith("[")


# ---------------------------------------------------------------------------
# Tests: long article (exceeds max_tokens, must be subdivided)
# ---------------------------------------------------------------------------


class TestChunkerLongArticle:
    """Tests for an article that exceeds max_tokens."""

    def test_article_is_subdivided(
        self, chunker: LegalChunker, long_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(long_doc, doc_meta)
        # A 2500-word article with 2000 max_tokens should produce >1 chunk
        assert len(chunks) > 1

    def test_all_sub_chunks_within_limit(
        self, chunker: LegalChunker, long_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(long_doc, doc_meta)
        for chunk in chunks:
            # Allow some tolerance since the prefix adds tokens
            token_count = len(chunk.text.split())
            # Each chunk should be reasonably close to the limit, with some
            # tolerance for prefix and indivisible paragraphs
            assert token_count < 2500, (
                f"Chunk has {token_count} tokens, expected under 2500"
            )

    def test_all_sub_chunks_have_same_metadata(
        self, chunker: LegalChunker, long_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(long_doc, doc_meta)
        for chunk in chunks:
            assert chunk.metadata.articulo == "Art. 7"
            assert chunk.metadata.seccion == "Titulo I, Capitulo III"
            assert chunk.metadata.boe_id == "BOE-A-2010-6737"

    def test_all_sub_chunks_have_prefix(
        self, chunker: LegalChunker, long_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(long_doc, doc_meta)
        for chunk in chunks:
            assert "[" in chunk.text
            assert "Art. 7" in chunk.text


# ---------------------------------------------------------------------------
# Tests: metadata correctness
# ---------------------------------------------------------------------------


class TestChunkMetadata:
    """Verify metadata is correctly propagated from BOE document info."""

    def test_boe_id(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert chunk.metadata.boe_id == "BOE-A-2010-6737"

    def test_rango(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert chunk.metadata.rango == "Ley"

    def test_departamento(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert chunk.metadata.departamento == "Jefatura del Estado"

    def test_materia_codigo(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert chunk.metadata.materia_codigo == "Activos financieros"

    def test_fechas(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert chunk.metadata.fecha_publicacion == "20100429"
            assert chunk.metadata.fecha_consolidacion == "20100430"

    def test_estado_consolidacion(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert chunk.metadata.estado_consolidacion == "Finalizado"

    def test_norma_titulo(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert "Ley 10/2010" in chunk.metadata.norma_titulo

    def test_seccion_populated_for_articles(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        art1 = next(c for c in chunks if c.metadata.articulo == "Art. 1")
        assert art1.metadata.seccion == "Titulo I, Capitulo I"

    def test_empty_materia_when_none(
        self, small_doc: ExtractedDocument
    ) -> None:
        meta_no_materias = _make_doc_meta()
        meta_no_materias.materias = []
        chunker = LegalChunker()
        chunks = chunker.chunk_document(small_doc, meta_no_materias)
        for chunk in chunks:
            assert chunk.metadata.materia_codigo == ""


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestChunkerEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_document(
        self, chunker: LegalChunker, doc_meta: BOEDocumentMeta
    ) -> None:
        empty_doc = ExtractedDocument(titulo="Vacia", preambulo="", articulos=[], disposiciones=[])
        chunks = chunker.chunk_document(empty_doc, doc_meta)
        assert chunks == []

    def test_document_with_only_preambulo(
        self, chunker: LegalChunker, doc_meta: BOEDocumentMeta
    ) -> None:
        doc = ExtractedDocument(
            titulo="Ley X",
            preambulo="Exposicion de motivos larga con contenido relevante.",
        )
        chunks = chunker.chunk_document(doc, doc_meta)
        assert len(chunks) == 1
        assert chunks[0].metadata.articulo == "Preambulo"

    def test_chunk_is_legal_chunk_type(
        self, chunker: LegalChunker, small_doc: ExtractedDocument, doc_meta: BOEDocumentMeta
    ) -> None:
        chunks = chunker.chunk_document(small_doc, doc_meta)
        for chunk in chunks:
            assert isinstance(chunk, LegalChunk)
            assert isinstance(chunk.metadata, ChunkMetadata)
