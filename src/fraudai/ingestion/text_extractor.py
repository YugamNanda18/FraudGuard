"""Extract and clean structured text from BOE HTML/XML documents."""

from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class ExtractedArticle(BaseModel):
    """A single article or disposition extracted from a BOE document."""

    numero: str  # "Art. 1", "Art. 18 bis", "Disposicion adicional primera"
    titulo: str = ""  # Title of the article if present
    contenido: str  # Clean text content
    seccion: str = ""  # "Titulo I, Capitulo II" -- full hierarchy


class ExtractedDocument(BaseModel):
    """Structured representation of a BOE legal document."""

    titulo: str
    preambulo: str = ""  # Exposicion de motivos
    articulos: list[ExtractedArticle] = Field(default_factory=list)
    disposiciones: list[ExtractedArticle] = Field(default_factory=list)
    anexos: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Regex patterns for BOE document structure
# ---------------------------------------------------------------------------

# Matches "Articulo 1.", "ARTICULO 1.", "Art. 1", "Articulo 18 bis.",
# "Articulo unico." etc.
_RE_ARTICLE = re.compile(
    r"^(?:ART[IÍ]CULO|Art\.?)\s+"
    r"([\w\dúÚ]+(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|octies))?)"
    r"\.?\s*(.*)$",
    re.IGNORECASE,
)

# Matches "Disposicion adicional primera", "DISPOSICION TRANSITORIA SEGUNDA", etc.
_RE_DISPOSICION = re.compile(
    r"^DISPOSICI[OÓ]N\s+"
    r"(ADICIONAL|TRANSITORIA|DEROGATORIA|FINAL)\s+"
    r"(.+?)\.?\s*$",
    re.IGNORECASE,
)

# Matches "TITULO I", "TITULO PRELIMINAR", "Titulo II"
_RE_TITULO = re.compile(
    r"^T[IÍ]TULO\s+(PRELIMINAR|[IVXLCDM]+|\d+)\b(.*)$",
    re.IGNORECASE,
)

# Matches "CAPITULO I", "Capitulo II"
_RE_CAPITULO = re.compile(
    r"^CAP[IÍ]TULO\s+([IVXLCDM]+|\d+)\b(.*)$",
    re.IGNORECASE,
)

# Matches "Seccion 1.", "SECCION 2."
_RE_SECCION = re.compile(
    r"^SECCI[OÓ]N\s+(\d+|[IVXLCDM]+)\.?\s*(.*)$",
    re.IGNORECASE,
)

# Matches "ANEXO", "ANEXO I", "Anexo II"
_RE_ANEXO = re.compile(
    r"^ANEXO\s*([IVXLCDM]*|\d*)\.?\s*(.*)$",
    re.IGNORECASE,
)

# Tags to strip entirely (content and tag)
_STRIP_TAGS = {"style", "script", "meta", "link", "head"}


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class BOETextExtractor:
    """Extract and clean text from BOE HTML/XML documents."""

    def extract(self, raw_html: str) -> ExtractedDocument:
        """Extract structured text from raw HTML of a BOE document.

        Args:
            raw_html: HTML or XML string from the BOE.

        Returns:
            An ``ExtractedDocument`` with parsed articles, dispositions and
            annexes.  If the document has no identifiable article structure
            (e.g. a circular), the entire text is placed as a single article.
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        self._strip_noise(soup)

        titulo = self._extract_title(soup)
        paragraphs = self._extract_paragraphs(soup)

        if not paragraphs:
            logger.warning("No paragraphs found in BOE HTML document")
            return ExtractedDocument(titulo=titulo)

        return self._parse_structure(titulo, paragraphs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_noise(soup: BeautifulSoup) -> None:
        """Remove style/script tags, headers, footers, and institutional boilerplate."""
        for tag_name in _STRIP_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove common BOE header/footer containers
        for selector in (
            "div.encabezado",
            "div.piePagina",
            "div.tituloDocumento",
            "header",
            "footer",
            "nav",
        ):
            for el in soup.select(selector):
                el.decompose()

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        """Try to find the document title from the HTML."""
        # <h1>, <h2>, or <title> are common title locations
        for tag_name in ("h1", "h2", "title"):
            tag = soup.find(tag_name)
            if tag and tag.get_text(strip=True):
                return _normalize_whitespace(tag.get_text(strip=True))

        # Fallback: first <p> that looks like a title (all caps or very short)
        first_p = soup.find("p")
        if first_p:
            text = first_p.get_text(strip=True)
            if text and len(text) < 300:
                return _normalize_whitespace(text)
        return ""

    @staticmethod
    def _extract_paragraphs(soup: BeautifulSoup) -> list[str]:
        """Extract all meaningful text paragraphs from the document."""
        paragraphs: list[str] = []

        # Try <p> tags first (most common in BOE HTML)
        p_tags = soup.find_all("p")
        if p_tags:
            for p in p_tags:
                text = _normalize_whitespace(p.get_text(strip=True))
                if text:
                    paragraphs.append(text)
        else:
            # Fallback: split the entire text by double newlines
            full_text = soup.get_text(separator="\n")
            for block in full_text.split("\n"):
                text = _normalize_whitespace(block.strip())
                if text:
                    paragraphs.append(text)

        return paragraphs

    def _parse_structure(
        self, titulo: str, paragraphs: list[str]
    ) -> ExtractedDocument:
        """Walk paragraphs and classify them into structural components."""
        preambulo_parts: list[str] = []
        articulos: list[ExtractedArticle] = []
        disposiciones: list[ExtractedArticle] = []
        anexos: list[str] = []

        # Tracking state
        current_titulo = ""
        current_capitulo = ""
        current_seccion_num = ""
        in_preambulo = True
        in_anexo = False
        current_anexo_parts: list[str] = []
        current_article: _ArticleAccumulator | None = None
        found_any_article = False

        for paragraph in paragraphs:
            # --- Anexo detection ---
            m_anexo = _RE_ANEXO.match(paragraph)
            if m_anexo:
                # Flush previous article
                self._flush_article(
                    current_article, articulos, disposiciones,
                    current_titulo, current_capitulo, current_seccion_num,
                )
                current_article = None
                # Flush previous anexo
                if current_anexo_parts:
                    anexos.append("\n\n".join(current_anexo_parts))
                current_anexo_parts = [paragraph]
                in_anexo = True
                in_preambulo = False
                continue

            if in_anexo:
                current_anexo_parts.append(paragraph)
                continue

            # --- Section hierarchy detection ---
            m_titulo = _RE_TITULO.match(paragraph)
            if m_titulo:
                self._flush_article(
                    current_article, articulos, disposiciones,
                    current_titulo, current_capitulo, current_seccion_num,
                )
                current_article = None
                current_titulo = f"Titulo {m_titulo.group(1)}"
                current_capitulo = ""
                current_seccion_num = ""
                in_preambulo = False
                continue

            m_capitulo = _RE_CAPITULO.match(paragraph)
            if m_capitulo:
                self._flush_article(
                    current_article, articulos, disposiciones,
                    current_titulo, current_capitulo, current_seccion_num,
                )
                current_article = None
                current_capitulo = f"Capitulo {m_capitulo.group(1)}"
                current_seccion_num = ""
                continue

            m_seccion = _RE_SECCION.match(paragraph)
            if m_seccion:
                self._flush_article(
                    current_article, articulos, disposiciones,
                    current_titulo, current_capitulo, current_seccion_num,
                )
                current_article = None
                current_seccion_num = f"Seccion {m_seccion.group(1)}"
                continue

            # --- Disposicion detection ---
            m_disp = _RE_DISPOSICION.match(paragraph)
            if m_disp:
                self._flush_article(
                    current_article, articulos, disposiciones,
                    current_titulo, current_capitulo, current_seccion_num,
                )
                tipo = m_disp.group(1).lower()
                nombre = m_disp.group(2).strip().rstrip(".")
                numero = f"Disposicion {tipo} {nombre}"
                current_article = _ArticleAccumulator(
                    numero=numero, is_disposicion=True,
                )
                in_preambulo = False
                found_any_article = True
                continue

            # --- Article detection ---
            m_art = _RE_ARTICLE.match(paragraph)
            if m_art:
                self._flush_article(
                    current_article, articulos, disposiciones,
                    current_titulo, current_capitulo, current_seccion_num,
                )
                art_num = m_art.group(1).strip()
                rest = m_art.group(2).strip().rstrip(".")
                current_article = _ArticleAccumulator(
                    numero=f"Art. {art_num}",
                    titulo=rest,
                )
                in_preambulo = False
                found_any_article = True
                continue

            # --- Content accumulation ---
            if current_article is not None:
                current_article.content_parts.append(paragraph)
            elif in_preambulo:
                preambulo_parts.append(paragraph)

        # Flush remaining
        self._flush_article(
            current_article, articulos, disposiciones,
            current_titulo, current_capitulo, current_seccion_num,
        )
        if current_anexo_parts:
            anexos.append("\n\n".join(current_anexo_parts))

        # If no articles were found, treat the whole text as a single block
        if not found_any_article:
            full_text = "\n\n".join(preambulo_parts)
            if full_text.strip():
                articulos.append(
                    ExtractedArticle(
                        numero="Texto completo",
                        titulo="",
                        contenido=full_text,
                        seccion="",
                    )
                )
                preambulo_parts = []

        return ExtractedDocument(
            titulo=titulo,
            preambulo="\n\n".join(preambulo_parts),
            articulos=articulos,
            disposiciones=disposiciones,
            anexos=anexos,
        )

    @staticmethod
    def _flush_article(
        acc: _ArticleAccumulator | None,
        articulos: list[ExtractedArticle],
        disposiciones: list[ExtractedArticle],
        current_titulo: str,
        current_capitulo: str,
        current_seccion_num: str,
    ) -> None:
        """Convert an accumulator into an ExtractedArticle and append it."""
        if acc is None:
            return

        seccion_parts = [
            p for p in (current_titulo, current_capitulo, current_seccion_num) if p
        ]
        seccion = ", ".join(seccion_parts)

        article = ExtractedArticle(
            numero=acc.numero,
            titulo=acc.titulo,
            contenido="\n\n".join(acc.content_parts),
            seccion=seccion,
        )

        if acc.is_disposicion:
            disposiciones.append(article)
        else:
            articulos.append(article)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _ArticleAccumulator:
    """Mutable accumulator for article content being parsed."""

    __slots__ = ("numero", "titulo", "content_parts", "is_disposicion")

    def __init__(
        self,
        numero: str,
        titulo: str = "",
        *,
        is_disposicion: bool = False,
    ) -> None:
        self.numero = numero
        self.titulo = titulo
        self.content_parts: list[str] = []
        self.is_disposicion = is_disposicion


def _normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into single spaces."""
    return re.sub(r"\s+", " ", text).strip()
