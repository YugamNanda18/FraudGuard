"""Tests for ToolRegistry and create_search_boe — all external calls are mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from fraudai.agents.tool_registry import ToolRegistry
from fraudai.agents.tools import create_search_boe
from fraudai.rag.retriever import RetrievalResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_retrieval_result(
    idx: int = 0,
    text: str = "Article text",
    score: float = 0.9,
    boe_id: str = "BOE-A-2010-6737",
    norma_titulo: str = "Ley 10/2010, de 28 de abril",
    articulo: str = "Art. 18",
    collection: str = "boe_legislation",
) -> RetrievalResult:
    """Build a RetrievalResult for tests."""
    return RetrievalResult(
        text=text,
        score=score,
        metadata={
            "boe_id": boe_id,
            "norma_titulo": norma_titulo,
            "articulo": articulo,
            "fecha_publicacion": "2010-04-29",
            "fecha_consolidacion": "2025-12-01",
            "estado_consolidacion": "vigente",
        },
        boe_id=boe_id,
        norma_titulo=norma_titulo,
        articulo=articulo,
        collection=collection,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_retriever() -> MagicMock:
    """Return a mocked LegalRetriever with async retrieve and sync format_citations."""
    retriever = MagicMock()
    retriever.retrieve = AsyncMock(
        return_value=[
            _make_retrieval_result(idx=0, score=0.95, text="Artículo 18. Examen especial"),
            _make_retrieval_result(idx=1, score=0.88, text="Artículo 2. Sujetos obligados"),
        ],
    )
    retriever.format_citations.return_value = [
        {
            "boe_id": "BOE-A-2010-6737",
            "norma_titulo": "Ley 10/2010, de 28 de abril",
            "articulo": "Art. 18",
            "texto_relevante": "Artículo 18. Examen especial",
            "score": 0.95,
            "fecha_publicacion": "2010-04-29",
            "estado_consolidacion": "vigente",
            "collection": "boe_legislation",
        },
        {
            "boe_id": "BOE-A-2010-6737",
            "norma_titulo": "Ley 10/2010, de 28 de abril",
            "articulo": "Art. 2",
            "texto_relevante": "Artículo 2. Sujetos obligados",
            "score": 0.88,
            "fecha_publicacion": "2010-04-29",
            "estado_consolidacion": "vigente",
            "collection": "boe_legislation",
        },
    ]
    return retriever


@pytest.fixture
def registry(mock_retriever: MagicMock) -> ToolRegistry:
    """Return a ToolRegistry wired to the mock retriever."""
    return ToolRegistry(retriever=mock_retriever)


# ---------------------------------------------------------------------------
# Tests: create_search_boe
# ---------------------------------------------------------------------------


class TestCreateSearchBoe:
    """Tests for the create_search_boe factory function."""

    def test_returns_tool_with_ainvoke(self, mock_retriever: MagicMock) -> None:
        """create_search_boe should return a LangChain tool with ainvoke."""
        tool_fn = create_search_boe(mock_retriever)

        assert hasattr(tool_fn, "ainvoke")
        assert hasattr(tool_fn, "name")

    def test_returned_tool_has_name(self, mock_retriever: MagicMock) -> None:
        """The returned tool should have the name 'search_boe'."""
        tool_fn = create_search_boe(mock_retriever)

        assert tool_fn.name == "search_boe"

    async def test_calls_retriever_retrieve(self, mock_retriever: MagicMock) -> None:
        """search_boe should call retriever.retrieve with the correct args."""
        tool_fn = create_search_boe(mock_retriever)

        await tool_fn.ainvoke({"query": "blanqueo de capitales", "k": 10})

        mock_retriever.retrieve.assert_called_once_with(
            "blanqueo de capitales", k=10, filters=None,
        )

    async def test_calls_retriever_with_filters(self, mock_retriever: MagicMock) -> None:
        """search_boe should forward filters to retriever.retrieve."""
        tool_fn = create_search_boe(mock_retriever)
        filters = {"materia_codigo": "derecho financiero"}

        await tool_fn.ainvoke({"query": "PBC", "k": 5, "filters": filters})

        mock_retriever.retrieve.assert_called_once_with(
            "PBC", k=5, filters=filters,
        )

    async def test_returns_formatted_citations(self, mock_retriever: MagicMock) -> None:
        """search_boe should return the output of format_citations."""
        tool_fn = create_search_boe(mock_retriever)

        result = await tool_fn.ainvoke({"query": "sujetos obligados"})

        # format_citations is called with the results from retrieve.
        mock_retriever.format_citations.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["boe_id"] == "BOE-A-2010-6737"
        assert result[0]["articulo"] == "Art. 18"

    async def test_calls_retriever_with_default_k(self, mock_retriever: MagicMock) -> None:
        """search_boe should use k=20 as default."""
        tool_fn = create_search_boe(mock_retriever)

        await tool_fn.ainvoke({"query": "test"})

        mock_retriever.retrieve.assert_called_once_with(
            "test", k=20, filters=None,
        )

    async def test_empty_results(self, mock_retriever: MagicMock) -> None:
        """search_boe should handle empty results from retriever."""
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_retriever.format_citations.return_value = []
        tool_fn = create_search_boe(mock_retriever)

        result = await tool_fn.ainvoke({"query": "nonexistent regulation"})

        assert result == []
        mock_retriever.retrieve.assert_called_once()
        mock_retriever.format_citations.assert_called_once_with([])


# ---------------------------------------------------------------------------
# Tests: ToolRegistry
# ---------------------------------------------------------------------------


class TestToolRegistry:
    """Tests for the ToolRegistry class."""

    def test_get_search_boe_returns_tool(self, registry: ToolRegistry) -> None:
        """get_search_boe should return a LangChain tool."""
        tool_fn = registry.get_search_boe()

        assert hasattr(tool_fn, "ainvoke")
        assert tool_fn.name == "search_boe"

    def test_get_search_boe_caches_instance(self, registry: ToolRegistry) -> None:
        """get_search_boe should return the same instance on repeated calls."""
        tool_a = registry.get_search_boe()
        tool_b = registry.get_search_boe()

        assert tool_a is tool_b

    def test_get_tools_for_agent_harvey(self, registry: ToolRegistry) -> None:
        """Harvey should get transaction tools + search_boe."""
        tools = registry.get_tools_for_agent("harvey")

        tool_names = [getattr(t, "name", getattr(t, "__name__", repr(t))) for t in tools]
        assert "analyze_transactions" in tool_names
        assert "detect_patterns" in tool_names
        assert "risk_scoring" in tool_names
        assert "generate_rules" in tool_names
        assert "search_boe" in tool_names
        assert len(tools) == 5

    def test_get_tools_for_agent_louis(self, registry: ToolRegistry) -> None:
        """Louis should get compliance tools + search_boe."""
        tools = registry.get_tools_for_agent("louis")

        tool_names = [getattr(t, "name", getattr(t, "__name__", repr(t))) for t in tools]
        assert "generate_sar_report" in tool_names
        assert "compliance_checklist" in tool_names
        assert "search_boe" in tool_names
        assert len(tools) == 3

    def test_get_tools_for_agent_jessica(self, registry: ToolRegistry) -> None:
        """Jessica should get graph tools + search_boe."""
        tools = registry.get_tools_for_agent("jessica")

        tool_names = [getattr(t, "name", getattr(t, "__name__", repr(t))) for t in tools]
        assert "graph_analysis" in tool_names
        assert "search_boe" in tool_names
        assert len(tools) == 2

    def test_get_tools_for_agent_mike(self, registry: ToolRegistry) -> None:
        """Mike should get red teaming tools + search_boe."""
        tools = registry.get_tools_for_agent("mike")

        tool_names = [getattr(t, "name", getattr(t, "__name__", repr(t))) for t in tools]
        assert "adversarial_evasion" in tool_names
        assert "prompt_injection_suite" in tool_names
        assert "search_boe" in tool_names
        assert len(tools) == 3

    def test_get_tools_for_agent_rachel(self, registry: ToolRegistry) -> None:
        """Rachel should get data engineering tools + search_boe."""
        tools = registry.get_tools_for_agent("rachel")

        tool_names = [getattr(t, "name", getattr(t, "__name__", repr(t))) for t in tools]
        assert "generate_pipeline" in tool_names
        assert "data_quality_check" in tool_names
        assert "search_boe" in tool_names
        assert len(tools) == 3

    def test_get_tools_for_agent_case_insensitive(self, registry: ToolRegistry) -> None:
        """Agent name matching should be case-insensitive."""
        tools_lower = registry.get_tools_for_agent("louis")
        tools_upper = registry.get_tools_for_agent("LOUIS")
        tools_mixed = registry.get_tools_for_agent("Louis")

        assert len(tools_lower) == len(tools_upper) == len(tools_mixed)

    def test_get_tools_for_agent_unknown_raises(self, registry: ToolRegistry) -> None:
        """Unknown agent name should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown agent 'unknown'"):
            registry.get_tools_for_agent("unknown")

    def test_search_boe_is_bound_version(
        self,
        registry: ToolRegistry,
    ) -> None:
        """search_boe in agent tools should be the retriever-bound version, not the stub."""
        tools = registry.get_tools_for_agent("louis")
        search_boe_tools = [t for t in tools if getattr(t, "name", "") == "search_boe"]

        assert len(search_boe_tools) == 1
        # The bound version is the same object returned by get_search_boe.
        assert search_boe_tools[0] is registry.get_search_boe()

    async def test_search_boe_in_agent_tools_is_functional(
        self,
        registry: ToolRegistry,
        mock_retriever: MagicMock,
    ) -> None:
        """search_boe obtained via get_tools_for_agent should call the retriever."""
        tools = registry.get_tools_for_agent("louis")
        search_boe_tool = next(t for t in tools if getattr(t, "name", "") == "search_boe")

        result = await search_boe_tool.ainvoke({"query": "AML compliance"})

        mock_retriever.retrieve.assert_called_once_with(
            "AML compliance", k=20, filters=None,
        )
        assert isinstance(result, list)
        assert len(result) == 2

    def test_all_agents_get_search_boe(self, registry: ToolRegistry) -> None:
        """Every agent should have search_boe in their tool list."""
        for agent_name in ("harvey", "louis", "jessica", "mike", "rachel"):
            tools = registry.get_tools_for_agent(agent_name)
            tool_names = [getattr(t, "name", getattr(t, "__name__", repr(t))) for t in tools]
            assert "search_boe" in tool_names, f"{agent_name} missing search_boe"
