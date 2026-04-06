"""Async HTTP client for the BOE (Boletin Oficial del Estado) open data API."""

from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class BOEDocumentMeta(BaseModel):
    """Metadata for a legislation document from the search API."""

    identificador: str
    titulo: str
    fecha_publicacion: str
    fecha_disposicion: str
    rango: str = ""
    departamento: str = ""
    materias: list[str] = Field(default_factory=list)
    url_pdf: str = ""
    url_html: str = ""
    url_eli: str = ""
    ambito: str = ""
    fecha_vigencia: str = ""
    vigencia_agotada: str = "N"
    estado_consolidacion: str = ""


class BOEReference(BaseModel):
    """A reference between BOE documents (e.g. MODIFICA, DEROGA)."""

    referencia: str
    tipo: str
    texto: str = ""


class BOEDocument(BaseModel):
    """Full document including text, analysis, and references."""

    meta: BOEDocumentMeta
    texto: str = ""
    materias: list[dict[str, str]] = Field(default_factory=list)
    notas: list[str] = Field(default_factory=list)
    referencias_anteriores: list[BOEReference] = Field(default_factory=list)
    referencias_posteriores: list[BOEReference] = Field(default_factory=list)


class BOESearchResult(BaseModel):
    """Paginated search result from the legislation API."""

    items: list[BOEDocumentMeta]
    offset: int
    limit: int
    has_more: bool


class BOESummaryItem(BaseModel):
    """A single disposition within a BOE summary."""

    identificador: str
    titulo: str
    url_pdf: str = ""
    url_html: str = ""
    seccion: str = ""
    departamento: str = ""


class BOESummary(BaseModel):
    """Daily BOE summary."""

    fecha: str
    publicacion: str = "BOE"
    disposiciones: list[BOESummaryItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BOEClientError(Exception):
    """Base exception for BOE API errors."""


class BOENotFoundError(BOEClientError):
    """Document or resource not found."""


class BOERateLimitError(BOEClientError):
    """Rate limit exceeded."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

_DEFAULT_TIMEOUT = 30.0
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds: 1, 2, 4
_MAX_CONCURRENT = 5


class BOEClient:
    """Async client for the BOE open data API.

    Uses httpx with retry/backoff, rate limiting via semaphore, and structured
    logging for every request.
    """

    BASE_URL = "https://www.boe.es/datosabiertos/api"
    XML_URL = "https://www.boe.es/diario_boe/xml.php"
    TEXT_URL = "https://www.boe.es/diario_boe/txt.php"

    def __init__(
        self,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
        max_concurrent: int = _MAX_CONCURRENT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Accept": "application/json"},
            follow_redirects=True,
        )

    async def __aenter__(self) -> BOEClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal HTTP
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with semaphore, retry, and backoff."""
        async with self._semaphore:
            last_exc: Exception | None = None
            for attempt in range(1, self._max_retries + 1):
                try:
                    logger.info(
                        "BOE request %s %s params=%s attempt=%d/%d",
                        method,
                        url,
                        params,
                        attempt,
                        self._max_retries,
                    )
                    response = await self._client.request(
                        method, url, params=params, headers=headers
                    )
                    if response.status_code == 404:
                        raise BOENotFoundError(f"Not found: {url} params={params}")
                    if response.status_code == 429:
                        raise BOERateLimitError("Rate limited by BOE API")
                    response.raise_for_status()
                    logger.info(
                        "BOE response %s %s status=%d size=%d",
                        method,
                        url,
                        response.status_code,
                        len(response.content),
                    )
                    return response
                except (BOENotFoundError, BOERateLimitError):
                    raise
                except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                    last_exc = exc
                    wait = _BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "BOE request failed attempt=%d/%d error=%s retrying_in=%.1fs",
                        attempt,
                        self._max_retries,
                        exc,
                        wait,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(wait)

            raise BOEClientError(
                f"Request failed after {self._max_retries} retries"
            ) from last_exc

    async def _get_json(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        resp = await self._request("GET", url, params=params)
        data: dict[str, Any] = resp.json()
        status_code = data.get("status", {}).get("code", "200")
        if status_code == "404":
            raise BOENotFoundError(f"API returned 404: {url}")
        if status_code not in ("200", "201"):
            raise BOEClientError(
                f"API error {status_code}: {data.get('status', {}).get('text')}"
            )
        return data

    async def _get_xml(self, url: str, params: dict[str, Any] | None = None) -> str:
        resp = await self._request(
            "GET", url, params=params, headers={"Accept": "application/xml"}
        )
        return resp.text

    # ------------------------------------------------------------------
    # Search legislation
    # ------------------------------------------------------------------

    async def search_legislation(
        self,
        materias: list[str] | None = None,
        text_query: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> BOESearchResult:
        """Search consolidated legislation with filters.

        Args:
            materias: Filter by subject keywords (matched against titulo).
            text_query: Free-text search against titulo field.
            date_from: Start date in AAAAMMDD format.
            date_to: End date in AAAAMMDD format.
            offset: Pagination offset.
            limit: Page size (max varies by API, typically up to 500).
        """
        params: dict[str, Any] = {"offset": offset, "limit": limit}

        # The BOE legislation-consolidada API does not support ElasticSearch
        # query param reliably for all field combinations.  We apply filters
        # client-side when the API does not natively support them.
        data = await self._get_json(f"{self.BASE_URL}/legislacion-consolidada", params)

        raw_items: list[dict[str, Any]] = data.get("data", []) or []
        items = [self._parse_search_item(item) for item in raw_items]

        # Client-side filters for fields not natively filterable
        if materias:
            lower_materias = [m.lower() for m in materias]
            items = [
                it
                for it in items
                if any(m in it.titulo.lower() for m in lower_materias)
            ]
        if text_query:
            q_lower = text_query.lower()
            items = [it for it in items if q_lower in it.titulo.lower()]
        if date_from:
            items = [it for it in items if it.fecha_publicacion >= date_from]
        if date_to:
            items = [it for it in items if it.fecha_publicacion <= date_to]

        has_more = len(raw_items) == limit
        return BOESearchResult(
            items=items, offset=offset, limit=limit, has_more=has_more
        )

    @staticmethod
    def _parse_search_item(raw: dict[str, Any]) -> BOEDocumentMeta:
        return BOEDocumentMeta(
            identificador=raw.get("identificador", ""),
            titulo=raw.get("titulo", ""),
            fecha_publicacion=raw.get("fecha_publicacion", ""),
            fecha_disposicion=raw.get("fecha_disposicion", ""),
            rango=raw.get("rango", {}).get("texto", "") if isinstance(raw.get("rango"), dict) else str(raw.get("rango", "")),
            departamento=raw.get("departamento", {}).get("texto", "") if isinstance(raw.get("departamento"), dict) else str(raw.get("departamento", "")),
            url_eli=raw.get("url_eli", ""),
            url_html=raw.get("url_html_consolidada", ""),
            ambito=raw.get("ambito", {}).get("texto", "") if isinstance(raw.get("ambito"), dict) else str(raw.get("ambito", "")),
            fecha_vigencia=raw.get("fecha_vigencia", ""),
            vigencia_agotada=raw.get("vigencia_agotada", "N"),
            estado_consolidacion=raw.get("estado_consolidacion", {}).get("texto", "") if isinstance(raw.get("estado_consolidacion"), dict) else str(raw.get("estado_consolidacion", "")),
        )

    # ------------------------------------------------------------------
    # Get document (full detail via XML endpoint)
    # ------------------------------------------------------------------

    async def get_document(self, doc_id: str) -> BOEDocument:
        """Fetch a full document by ID (e.g. BOE-A-2010-6737) via the XML endpoint."""
        xml_text = await self._get_xml(self.XML_URL, params={"id": doc_id})
        return self._parse_document_xml(xml_text)

    @staticmethod
    def _parse_document_xml(xml_text: str) -> BOEDocument:
        root = ET.fromstring(xml_text)
        meta_el = root.find("metadatos")

        def _text(parent: ET.Element | None, tag: str) -> str:
            if parent is None:
                return ""
            el = parent.find(tag)
            return (el.text or "").strip() if el is not None else ""

        identificador = _text(meta_el, "identificador")
        titulo = _text(meta_el, "titulo")
        fecha_pub = _text(meta_el, "fecha_publicacion")
        fecha_disp = _text(meta_el, "fecha_disposicion")
        rango = _text(meta_el, "rango")
        depto = _text(meta_el, "departamento")
        url_eli = _text(meta_el, "url_eli")
        url_pdf = _text(meta_el, "url_pdf")
        fecha_vig = _text(meta_el, "fecha_vigencia")
        vigencia_agotada = _text(meta_el, "vigencia_agotada") or "N"
        estado_el = meta_el.find("estado_consolidacion") if meta_el is not None else None
        estado_consolidacion = (estado_el.text or "").strip() if estado_el is not None else ""

        meta = BOEDocumentMeta(
            identificador=identificador,
            titulo=titulo,
            fecha_publicacion=fecha_pub,
            fecha_disposicion=fecha_disp,
            rango=rango,
            departamento=depto,
            url_eli=url_eli,
            url_pdf=f"https://www.boe.es{url_pdf}" if url_pdf.startswith("/") else url_pdf,
            url_html=f"https://www.boe.es/buscar/act.php?id={identificador}",
            fecha_vigencia=fecha_vig,
            vigencia_agotada=vigencia_agotada,
            estado_consolidacion=estado_consolidacion,
        )

        # Materias
        materias: list[dict[str, str]] = []
        analisis = root.find("analisis")
        if analisis is not None:
            for mat in analisis.findall(".//materia"):
                materias.append({
                    "codigo": mat.get("codigo", ""),
                    "texto": (mat.text or "").strip(),
                })
            meta.materias = [m["texto"] for m in materias if m["texto"]]

        # Notas
        notas: list[str] = []
        if analisis is not None:
            for nota in analisis.findall(".//nota"):
                text = (nota.text or "").strip()
                if text:
                    notas.append(text)

        # Referencias
        refs_ant: list[BOEReference] = []
        refs_post: list[BOEReference] = []
        if analisis is not None:
            for ref_el in analisis.findall(".//anteriores/anterior"):
                palabra_el = ref_el.find("palabra")
                refs_ant.append(BOEReference(
                    referencia=ref_el.get("referencia", ""),
                    tipo=(palabra_el.text or "").strip() if palabra_el is not None else "",
                    texto=_text(ref_el, "texto"),
                ))
            for ref_el in analisis.findall(".//posteriores/posterior"):
                palabra_el = ref_el.find("palabra")
                refs_post.append(BOEReference(
                    referencia=ref_el.get("referencia", ""),
                    tipo=(palabra_el.text or "").strip() if palabra_el is not None else "",
                    texto=_text(ref_el, "texto"),
                ))

        # Texto
        texto_el = root.find("texto")
        text_parts: list[str] = []
        if texto_el is not None:
            for p in texto_el:
                content = ET.tostring(p, encoding="unicode", method="text").strip()
                if content:
                    text_parts.append(content)
        texto = "\n\n".join(text_parts)

        return BOEDocument(
            meta=meta,
            texto=texto,
            materias=materias,
            notas=notas,
            referencias_anteriores=refs_ant,
            referencias_posteriores=refs_post,
        )

    # ------------------------------------------------------------------
    # Get document text only
    # ------------------------------------------------------------------

    async def get_document_text(self, doc_id: str) -> str:
        """Fetch the consolidated text of a document by ID.

        Uses the XML endpoint and extracts only the <texto> section.
        """
        doc = await self.get_document(doc_id)
        if not doc.texto:
            logger.warning("BOE document %s has no text content", doc_id)
        return doc.texto

    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------

    async def get_summary(self, date: str) -> BOESummary:
        """Fetch the BOE summary for a given date (AAAAMMDD format)."""
        data = await self._get_json(f"{self.BASE_URL}/boe/sumario/{date}")
        return self._parse_summary(data)

    @staticmethod
    def _parse_summary(data: dict[str, Any]) -> BOESummary:
        sumario = data.get("data", {}).get("sumario", {})
        meta = sumario.get("metadatos", {})
        fecha = meta.get("fecha_publicacion", "")
        publicacion = meta.get("publicacion", "BOE")

        disposiciones: list[BOESummaryItem] = []

        for diario in sumario.get("diario", []):
            for seccion in diario.get("seccion", []):
                seccion_nombre = seccion.get("nombre", "")
                deptos = seccion.get("departamento", [])
                if isinstance(deptos, dict):
                    deptos = [deptos]

                for depto in deptos:
                    depto_nombre = depto.get("nombre", "")

                    # Items can be nested under "epigrafe" or "texto.epigrafe"
                    epigrafes: list[dict[str, Any]] = []
                    if "epigrafe" in depto:
                        eps = depto["epigrafe"]
                        epigrafes = eps if isinstance(eps, list) else [eps]

                    texto_obj = depto.get("texto", {})
                    if isinstance(texto_obj, dict) and "epigrafe" in texto_obj:
                        eps = texto_obj["epigrafe"]
                        epigrafes.extend(eps if isinstance(eps, list) else [eps])

                    for epigrafe in epigrafes:
                        items_raw = epigrafe.get("item", [])
                        if isinstance(items_raw, dict):
                            items_raw = [items_raw]

                        for item in items_raw:
                            url_pdf_obj = item.get("url_pdf", {})
                            url_pdf = url_pdf_obj.get("texto", "") if isinstance(url_pdf_obj, dict) else str(url_pdf_obj)

                            disposiciones.append(BOESummaryItem(
                                identificador=item.get("identificador", ""),
                                titulo=item.get("titulo", ""),
                                url_pdf=url_pdf,
                                url_html=item.get("url_html", ""),
                                seccion=seccion_nombre,
                                departamento=depto_nombre,
                            ))

        return BOESummary(
            fecha=fecha,
            publicacion=publicacion,
            disposiciones=disposiciones,
        )

    async def get_summaries_range(
        self, date_from: str, date_to: str
    ) -> list[BOESummary]:
        """Fetch summaries for a date range (AAAAMMDD format).

        Skips dates that return 404 (weekends, holidays with no BOE).
        """
        dates = self._date_range(date_from, date_to)
        logger.info(
            "BOE fetching summaries for %d dates from %s to %s",
            len(dates),
            date_from,
            date_to,
        )
        tasks = [self._safe_get_summary(d) for d in dates]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def _safe_get_summary(self, date: str) -> BOESummary | None:
        try:
            return await self.get_summary(date)
        except BOENotFoundError:
            logger.debug("BOE no summary for date %s (likely weekend/holiday)", date)
            return None

    @staticmethod
    def _date_range(date_from: str, date_to: str) -> list[str]:
        fmt = "%Y%m%d"
        start = datetime.strptime(date_from, fmt)
        end = datetime.strptime(date_to, fmt)
        dates: list[str] = []
        current = start
        while current <= end:
            dates.append(current.strftime(fmt))
            current += timedelta(days=1)
        return dates

    # ------------------------------------------------------------------
    # Paginated search (iterate all pages)
    # ------------------------------------------------------------------

    async def search_all_pages(
        self,
        materias: list[str] | None = None,
        text_query: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        max_pages: int = 100,
    ) -> list[BOEDocumentMeta]:
        """Iterate through all result pages, collecting every document.

        Args:
            max_pages: Safety limit to prevent unbounded iteration.
        """
        all_items: list[BOEDocumentMeta] = []
        offset = 0

        for page in range(1, max_pages + 1):
            logger.info("BOE search_all_pages page=%d offset=%d", page, offset)
            result = await self.search_legislation(
                materias=materias,
                text_query=text_query,
                date_from=date_from,
                date_to=date_to,
                offset=offset,
                limit=limit,
            )
            all_items.extend(result.items)
            if not result.has_more:
                break
            offset += limit

        logger.info("BOE search_all_pages collected %d items in %d pages", len(all_items), page)
        return all_items
