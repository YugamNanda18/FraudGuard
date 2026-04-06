"""Tests for BOETextExtractor with realistic BOE HTML fixtures."""

from __future__ import annotations

import pytest

from fraudai.ingestion.text_extractor import (
    BOETextExtractor,
    ExtractedArticle,
    ExtractedDocument,
)

# ---------------------------------------------------------------------------
# Fixtures: realistic BOE HTML
# ---------------------------------------------------------------------------

BOE_HTML_LEY = """\
<html>
<head>
  <title>Ley 10/2010, de 28 de abril, de prevencion del blanqueo de capitales.</title>
  <style>.boe { font-family: serif; }</style>
  <script>var ga = 'analytics';</script>
</head>
<body>
<header><div class="encabezado">BOE Header institucional</div></header>
<nav>Navegacion principal</nav>

<h1>Ley 10/2010, de 28 de abril, de prevencion del blanqueo de capitales
y de la financiacion del terrorismo.</h1>

<p>JUAN CARLOS I REY DE ESPANA</p>
<p>A todos los que la presente vieren y entendieren.</p>
<p>Sabed: Que las Cortes Generales han aprobado y Yo vengo en sancionar
la siguiente ley.</p>

<p>TITULO I</p>
<p>De las actividades y sujetos obligados</p>

<p>CAPITULO I</p>
<p>Actividades obligadas</p>

<p>Articulo 1. Objeto.</p>
<p>La presente ley tiene por objeto el establecimiento de obligaciones
de prevencion del blanqueo de capitales y de la financiacion del terrorismo.</p>
<p>En particular, impone obligaciones de identificacion, comunicacion
y conservacion de documentos.</p>

<p>Articulo 2. Sujetos obligados.</p>
<p>Seran sujetos obligados las entidades de credito, las entidades
aseguradoras y los corredores de seguros autorizados.</p>

<p>CAPITULO II</p>
<p>Diligencia debida</p>

<p>Articulo 3. Identificacion formal.</p>
<p>Los sujetos obligados identificaran a cuantas personas fisicas o
juridicas pretendan establecer relaciones de negocio.</p>

<p>TITULO II</p>
<p>De la organizacion institucional</p>

<p>Articulo 4. Comision de prevencion.</p>
<p>Se crea la Comision de Prevencion del Blanqueo de Capitales
e Infracciones Monetarias como organo colegiado adscrito a la
Secretaria de Estado de Economia.</p>

<p>Articulo 5. Servicio Ejecutivo de la Comision.</p>
<p>El Servicio Ejecutivo de la Comision actuara con plena autonomia
operativa frente a cualquier organo administrativo.</p>

<p>Disposicion adicional primera. Aplicacion supletoria.</p>
<p>En lo no previsto por esta ley se aplicara supletoriamente lo
dispuesto en la Ley 30/1992.</p>

<p>Disposicion transitoria primera. Procedimientos en curso.</p>
<p>Los procedimientos sancionadores iniciados con anterioridad a la
entrada en vigor de esta ley se regiran por la normativa anterior.</p>

<p>Disposicion derogatoria unica. Derogacion normativa.</p>
<p>Queda derogada la Ley 19/1993, de 28 de diciembre.</p>

<p>Disposicion final primera. Habilitacion normativa.</p>
<p>Se autoriza al Gobierno para dictar cuantas disposiciones sean
necesarias para el desarrollo y aplicacion de esta ley.</p>

<p>ANEXO I</p>
<p>Lista de actividades profesionales sujetas a obligaciones de
prevencion del blanqueo de capitales.</p>
<p>1. Auditores de cuentas.</p>
<p>2. Contables externos y asesores fiscales.</p>

<footer><div class="piePagina">Pie de pagina del BOE</div></footer>
</body>
</html>
"""

BOE_HTML_CIRCULAR = """\
<html>
<body>
<h2>Circular 1/2023, del Banco de Espana, sobre normas de informacion
financiera publica.</h2>
<p>El Banco de Espana, en uso de las facultades que le confiere la Ley
13/1994, ha dispuesto lo siguiente.</p>
<p>Las entidades de credito deberan remitir con periodicidad trimestral
los estados financieros correspondientes a su actividad.</p>
<p>Los modelos de estados financieros seran los establecidos en el anejo
de la presente circular.</p>
<p>La presente circular entrara en vigor el dia siguiente al de su
publicacion en el Boletin Oficial del Estado.</p>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Extractor instance
# ---------------------------------------------------------------------------


@pytest.fixture
def extractor() -> BOETextExtractor:
    return BOETextExtractor()


# ---------------------------------------------------------------------------
# Tests: structured law with articles
# ---------------------------------------------------------------------------


class TestExtractorWithArticles:
    """Tests for HTML containing a structured law (articles, titulos, etc)."""

    def test_titulo_extracted(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        assert "Ley 10/2010" in doc.titulo
        assert "blanqueo" in doc.titulo.lower()

    def test_preambulo_extracted(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        assert "JUAN CARLOS" in doc.preambulo
        assert "Cortes Generales" in doc.preambulo

    def test_articles_count(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        assert len(doc.articulos) == 5

    def test_article_numbers(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        numeros = [a.numero for a in doc.articulos]
        assert "Art. 1" in numeros
        assert "Art. 2" in numeros
        assert "Art. 3" in numeros
        assert "Art. 4" in numeros
        assert "Art. 5" in numeros

    def test_article_titles(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        art1 = next(a for a in doc.articulos if a.numero == "Art. 1")
        assert art1.titulo == "Objeto"

    def test_article_content(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        art1 = next(a for a in doc.articulos if a.numero == "Art. 1")
        assert "blanqueo de capitales" in art1.contenido
        assert "identificacion" in art1.contenido

    def test_section_hierarchy(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        art1 = next(a for a in doc.articulos if a.numero == "Art. 1")
        assert "Titulo I" in art1.seccion
        assert "Capitulo I" in art1.seccion

        art3 = next(a for a in doc.articulos if a.numero == "Art. 3")
        assert "Titulo I" in art3.seccion
        assert "Capitulo II" in art3.seccion

        art4 = next(a for a in doc.articulos if a.numero == "Art. 4")
        assert "Titulo II" in art4.seccion

    def test_disposiciones_count(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        assert len(doc.disposiciones) == 4

    def test_disposiciones_types(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        tipos = [d.numero.lower() for d in doc.disposiciones]
        assert any("adicional" in t for t in tipos)
        assert any("transitoria" in t for t in tipos)
        assert any("derogatoria" in t for t in tipos)
        assert any("final" in t for t in tipos)

    def test_disposicion_content(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        derogatoria = next(
            d for d in doc.disposiciones if "derogatoria" in d.numero.lower()
        )
        assert "Ley 19/1993" in derogatoria.contenido

    def test_anexos_extracted(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        assert len(doc.anexos) == 1
        assert "Auditores de cuentas" in doc.anexos[0]

    def test_noise_stripped(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_LEY)
        full_text = (
            doc.preambulo
            + " ".join(a.contenido for a in doc.articulos)
            + " ".join(d.contenido for d in doc.disposiciones)
        )
        assert "analytics" not in full_text
        assert "BOE Header institucional" not in full_text
        assert "Pie de pagina del BOE" not in full_text


# ---------------------------------------------------------------------------
# Tests: unstructured document (circular)
# ---------------------------------------------------------------------------


class TestExtractorWithCircular:
    """Tests for HTML without article structure (circular, resolution)."""

    def test_titulo_extracted(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_CIRCULAR)
        assert "Circular" in doc.titulo

    def test_no_individual_articles(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_CIRCULAR)
        # Should be treated as a single block since there are no articles
        assert len(doc.articulos) == 1
        assert doc.articulos[0].numero == "Texto completo"

    def test_full_text_preserved(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_CIRCULAR)
        block = doc.articulos[0].contenido
        assert "Banco de Espana" in block
        assert "entidades de credito" in block
        assert "estados financieros" in block

    def test_empty_disposiciones(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_CIRCULAR)
        assert doc.disposiciones == []

    def test_empty_preambulo_for_block(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract(BOE_HTML_CIRCULAR)
        # Preambulo is empty because everything went into the single block
        assert doc.preambulo == ""


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestExtractorEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_html(self, extractor: BOETextExtractor) -> None:
        doc = extractor.extract("")
        assert doc.titulo == ""
        assert doc.preambulo == ""
        assert doc.articulos == []

    def test_minimal_html_no_p_tags(self, extractor: BOETextExtractor) -> None:
        html = "<div>Articulo 1. Objeto.\nContenido del articulo primero.</div>"
        doc = extractor.extract(html)
        assert isinstance(doc, ExtractedDocument)

    def test_article_with_bis_suffix(self, extractor: BOETextExtractor) -> None:
        html = """
        <html><body>
        <h1>Ley X</h1>
        <p>Preambulo de la ley.</p>
        <p>Articulo 18 bis. Medidas reforzadas.</p>
        <p>Se aplicaran medidas reforzadas de diligencia debida.</p>
        </body></html>
        """
        doc = extractor.extract(html)
        assert len(doc.articulos) == 1
        assert doc.articulos[0].numero == "Art. 18 bis"
