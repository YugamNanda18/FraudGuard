"""Tests for BOEClient with mocked HTTP responses."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from fraudai.ingestion.boe_client import (
    BOEClient,
    BOEClientError,
    BOEDocument,
    BOEDocumentMeta,
    BOENotFoundError,
    BOESearchResult,
    BOESummary,
)

# ---------------------------------------------------------------------------
# Fixtures: mock response data
# ---------------------------------------------------------------------------

SEARCH_ITEM_RAW = {
    "fecha_actualizacion": "20260406T125514Z",
    "identificador": "BOE-A-2010-6737",
    "ambito": {"codigo": "1", "texto": "Estatal"},
    "departamento": {"codigo": "7723", "texto": "Jefatura del Estado"},
    "rango": {"codigo": "1300", "texto": "Ley"},
    "fecha_disposicion": "20100428",
    "numero_oficial": "10/2010",
    "titulo": (
        "Ley 10/2010, de 28 de abril, de prevencion del blanqueo "
        "de capitales y de la financiacion del terrorismo."
    ),
    "diario": "Boletin Oficial del Estado",
    "fecha_publicacion": "20100429",
    "diario_numero": "103",
    "fecha_vigencia": "20100430",
    "vigencia_agotada": "N",
    "estado_consolidacion": {"codigo": "3", "texto": "Finalizado"},
    "url_eli": "https://www.boe.es/eli/es/l/2010/04/28/10",
    "url_html_consolidada": "https://www.boe.es/buscar/act.php?id=BOE-A-2010-6737",
}

SEARCH_RESPONSE_JSON = json.dumps({
    "status": {"code": "200", "text": "ok"},
    "data": [SEARCH_ITEM_RAW],
}).encode()

SEARCH_EMPTY_RESPONSE_JSON = json.dumps({
    "status": {"code": "200", "text": "ok"},
    "data": "",
}).encode()

DOCUMENT_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<documento fecha_actualizacion="20260323132601">
  <metadatos>
    <identificador>BOE-A-2010-6737</identificador>
    <origen_legislativo codigo="1">Estatal</origen_legislativo>
    <departamento codigo="7723">Jefatura del Estado</departamento>
    <rango codigo="1300">Ley</rango>
    <fecha_disposicion>20100428</fecha_disposicion>
    <numero_oficial>10/2010</numero_oficial>
    <titulo>Ley 10/2010, de 28 de abril, de prevencion del blanqueo de capitales.</titulo>
    <diario codigo="BOE">Boletin Oficial del Estado</diario>
    <fecha_publicacion>20100429</fecha_publicacion>
    <diario_numero>103</diario_numero>
    <url_pdf>/boe/dias/2010/04/29/pdfs/BOE-A-2010-6737.pdf</url_pdf>
    <fecha_vigencia>20100430</fecha_vigencia>
    <vigencia_agotada>N</vigencia_agotada>
    <estado_consolidacion codigo="3">Finalizado</estado_consolidacion>
    <url_eli>https://www.boe.es/eli/es/l/2010/04/28/10</url_eli>
  </metadatos>
  <analisis>
    <materias>
      <materia codigo="60" orden="">Activos financieros</materia>
      <materia codigo="459" orden="">Delincuencia organizada</materia>
    </materias>
    <notas/>
    <referencias>
      <anteriores>
        <anterior referencia="BOE-A-1993-30991" orden="1010">
          <palabra codigo="210">DEROGA</palabra>
          <texto>la Ley 19/1993, de 28 de diciembre</texto>
        </anterior>
      </anteriores>
      <posteriores>
        <posterior referencia="BOE-A-2014-4742" orden="1010">
          <palabra codigo="270">MODIFICA</palabra>
          <texto>arts. 2 y 42 por Real Decreto-ley 7/2021</texto>
        </posterior>
      </posteriores>
    </referencias>
  </analisis>
  <texto>
    <p>JUAN CARLOS I REY DE ESPANA</p>
    <p>Articulo 1. Objeto.</p>
    <p>La presente ley tiene por objeto la prevencion del blanqueo de capitales.</p>
  </texto>
</documento>
"""

SUMMARY_RESPONSE_JSON = json.dumps({
    "status": {"code": "200", "text": "ok"},
    "data": {
        "sumario": {
            "metadatos": {
                "publicacion": "BOE",
                "fecha_publicacion": "20250101",
            },
            "diario": [
                {
                    "numero": "1",
                    "sumario_diario": {
                        "identificador": "BOE-S-2025-1",
                        "url_pdf": {
                            "szBytes": "239991",
                            "texto": "https://www.boe.es/boe/dias/2025/01/01/pdfs/BOE-S-2025-1.pdf",
                        },
                    },
                    "seccion": [
                        {
                            "codigo": "1",
                            "nombre": "I. Disposiciones generales",
                            "departamento": {
                                "codigo": "8162",
                                "nombre": "COMUNITAT VALENCIANA",
                                "texto": {
                                    "epigrafe": [
                                        {
                                            "nombre": "Simplificacion administrativa",
                                            "item": {
                                                "identificador": "BOE-A-2025-1",
                                                "titulo": "Ley 6/2024, de simplificacion administrativa.",
                                                "url_pdf": {
                                                    "szBytes": "2245004",
                                                    "texto": "https://www.boe.es/boe/dias/2025/01/01/pdfs/BOE-A-2025-1.pdf",
                                                },
                                                "url_html": "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2025-1",
                                            },
                                        }
                                    ]
                                },
                            },
                        }
                    ],
                }
            ],
        }
    },
}).encode()


# ---------------------------------------------------------------------------
# Transport factory
# ---------------------------------------------------------------------------


def _make_transport(
    handler: httpx.MockTransport | None = None,
) -> httpx.MockTransport:
    """Return the given transport or a default that always 200s."""
    return handler or httpx.MockTransport(
        lambda req: httpx.Response(200, json={"status": {"code": "200"}, "data": []})
    )


def _build_client(
    transport: httpx.MockTransport, **kwargs: object
) -> BOEClient:
    http_client = httpx.AsyncClient(transport=transport)
    return BOEClient(client=http_client, max_retries=1, **kwargs)


# ---------------------------------------------------------------------------
# Tests: search_legislation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_legislation_returns_parsed_items() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=SEARCH_RESPONSE_JSON)
    )
    async with _build_client(transport) as client:
        result = await client.search_legislation(offset=0, limit=50)

    assert isinstance(result, BOESearchResult)
    assert len(result.items) == 1
    item = result.items[0]
    assert item.identificador == "BOE-A-2010-6737"
    assert item.rango == "Ley"
    assert item.departamento == "Jefatura del Estado"
    assert "blanqueo" in item.titulo.lower()


@pytest.mark.asyncio
async def test_search_legislation_client_side_materia_filter() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=SEARCH_RESPONSE_JSON)
    )
    async with _build_client(transport) as client:
        result = await client.search_legislation(materias=["blanqueo"])
        assert len(result.items) == 1

        result_no_match = await client.search_legislation(materias=["ciberseguridad"])
        assert len(result_no_match.items) == 0


@pytest.mark.asyncio
async def test_search_legislation_text_query_filter() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=SEARCH_RESPONSE_JSON)
    )
    async with _build_client(transport) as client:
        result = await client.search_legislation(text_query="terrorismo")
        assert len(result.items) == 1

        result_miss = await client.search_legislation(text_query="medioambiente")
        assert len(result_miss.items) == 0


@pytest.mark.asyncio
async def test_search_legislation_date_filters() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=SEARCH_RESPONSE_JSON)
    )
    async with _build_client(transport) as client:
        result = await client.search_legislation(date_from="20100101", date_to="20101231")
        assert len(result.items) == 1

        result_before = await client.search_legislation(date_from="20200101")
        assert len(result_before.items) == 0


@pytest.mark.asyncio
async def test_search_has_more_flag() -> None:
    # When API returns exactly `limit` items, has_more should be True
    two_items = json.dumps({
        "status": {"code": "200", "text": "ok"},
        "data": [SEARCH_ITEM_RAW, SEARCH_ITEM_RAW],
    }).encode()
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=two_items)
    )
    async with _build_client(transport) as client:
        result = await client.search_legislation(limit=2)
        assert result.has_more is True


# ---------------------------------------------------------------------------
# Tests: get_document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_document_parses_xml() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=DOCUMENT_XML)
    )
    async with _build_client(transport) as client:
        doc = await client.get_document("BOE-A-2010-6737")

    assert isinstance(doc, BOEDocument)
    assert doc.meta.identificador == "BOE-A-2010-6737"
    assert doc.meta.rango == "Ley"
    assert "https://www.boe.es/boe/" in doc.meta.url_pdf
    assert len(doc.materias) == 2
    assert doc.materias[0]["texto"] == "Activos financieros"
    assert len(doc.referencias_anteriores) == 1
    assert doc.referencias_anteriores[0].tipo == "DEROGA"
    assert len(doc.referencias_posteriores) == 1
    assert "blanqueo" in doc.texto.lower()


@pytest.mark.asyncio
async def test_get_document_text_returns_string() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=DOCUMENT_XML)
    )
    async with _build_client(transport) as client:
        text = await client.get_document_text("BOE-A-2010-6737")

    assert isinstance(text, str)
    assert "blanqueo" in text.lower()
    assert "JUAN CARLOS" in text


# ---------------------------------------------------------------------------
# Tests: get_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_summary_parses_response() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=SUMMARY_RESPONSE_JSON)
    )
    async with _build_client(transport) as client:
        summary = await client.get_summary("20250101")

    assert isinstance(summary, BOESummary)
    assert summary.fecha == "20250101"
    assert summary.publicacion == "BOE"
    assert len(summary.disposiciones) >= 1
    disp = summary.disposiciones[0]
    assert disp.identificador == "BOE-A-2025-1"
    assert disp.departamento == "COMUNITAT VALENCIANA"
    assert "simplificacion" in disp.titulo.lower()


@pytest.mark.asyncio
async def test_get_summaries_range_skips_missing_dates() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        url_str = str(request.url)
        if "20250102" in url_str:
            return httpx.Response(
                404,
                json={"status": {"code": "404", "text": "No encontrado"}},
            )
        return httpx.Response(200, content=SUMMARY_RESPONSE_JSON)

    transport = httpx.MockTransport(handler)
    async with _build_client(transport) as client:
        summaries = await client.get_summaries_range("20250101", "20250103")

    # 3 dates requested; date 20250102 returns 404 -> 2 results
    assert len(summaries) == 2
    assert call_count == 3


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_404_raises_not_found() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(404, text="Not Found")
    )
    async with _build_client(transport) as client:
        with pytest.raises(BOENotFoundError):
            await client.search_legislation()


@pytest.mark.asyncio
async def test_500_raises_client_error_after_retries() -> None:
    attempt = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt
        attempt += 1
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    async with _build_client(transport, max_retries=2) as client:
        with pytest.raises(BOEClientError):
            await client.search_legislation()

    assert attempt == 2


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt() -> None:
    attempt = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            return httpx.Response(500, text="Server Error")
        return httpx.Response(200, content=SEARCH_RESPONSE_JSON)

    transport = httpx.MockTransport(handler)
    async with _build_client(transport, max_retries=3) as client:
        result = await client.search_legislation()

    assert len(result.items) == 1
    assert attempt == 2


# ---------------------------------------------------------------------------
# Tests: pagination (search_all_pages)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_all_pages_iterates_until_no_more() -> None:
    page_num = 0
    item_a = {**SEARCH_ITEM_RAW, "identificador": "BOE-A-2010-0001"}
    item_b = {**SEARCH_ITEM_RAW, "identificador": "BOE-A-2010-0002"}
    item_c = {**SEARCH_ITEM_RAW, "identificador": "BOE-A-2010-0003"}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal page_num
        page_num += 1
        if page_num == 1:
            body = {"status": {"code": "200", "text": "ok"}, "data": [item_a, item_b]}
        elif page_num == 2:
            body = {"status": {"code": "200", "text": "ok"}, "data": [item_c]}
        else:
            body = {"status": {"code": "200", "text": "ok"}, "data": ""}
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    async with _build_client(transport) as client:
        items = await client.search_all_pages(limit=2)

    assert len(items) == 3
    ids = [i.identificador for i in items]
    assert "BOE-A-2010-0001" in ids
    assert "BOE-A-2010-0003" in ids


@pytest.mark.asyncio
async def test_search_all_pages_respects_max_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        two_items = [SEARCH_ITEM_RAW, SEARCH_ITEM_RAW]
        return httpx.Response(
            200,
            json={"status": {"code": "200", "text": "ok"}, "data": two_items},
        )

    transport = httpx.MockTransport(handler)
    async with _build_client(transport) as client:
        items = await client.search_all_pages(limit=2, max_pages=3)

    # 3 pages x 2 items = 6
    assert len(items) == 6


# ---------------------------------------------------------------------------
# Tests: rate limiting (semaphore)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency() -> None:
    max_concurrent_seen = 0
    current_concurrent = 0
    lock = asyncio.Lock()

    async def tracked_handler(request: httpx.Request) -> httpx.Response:
        nonlocal max_concurrent_seen, current_concurrent
        async with lock:
            current_concurrent += 1
            if current_concurrent > max_concurrent_seen:
                max_concurrent_seen = current_concurrent

        await asyncio.sleep(0.05)

        async with lock:
            current_concurrent -= 1

        return httpx.Response(200, content=SEARCH_RESPONSE_JSON)

    transport = httpx.MockTransport(tracked_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = BOEClient(client=http_client, max_retries=1, max_concurrent=2)

    async with client:
        tasks = [client.search_legislation() for _ in range(6)]
        await asyncio.gather(*tasks)

    assert max_concurrent_seen <= 2


# ---------------------------------------------------------------------------
# Tests: context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_closes_client() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"status": {"code": "200"}, "data": []})
    )
    client = _build_client(transport)
    async with client:
        pass
    # After close, internal client should be closed
    assert client._client.is_closed


@pytest.mark.asyncio
async def test_empty_data_response_returns_empty_items() -> None:
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, content=SEARCH_EMPTY_RESPONSE_JSON)
    )
    async with _build_client(transport) as client:
        result = await client.search_legislation()

    assert result.items == []
    assert result.has_more is False
