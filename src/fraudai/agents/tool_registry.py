"""Tool registry with dependency injection for FraudAI Agent.

Tools need access to shared services (retriever, sandbox, etc.) but
LangChain ``@tool`` functions are plain functions.  This registry
creates closures with injected dependencies so tools can use services
without relying on module-level globals.

When a ``ToolImplementations`` instance is provided, the registry
replaces stub tools with real implementations backed by the
SandboxEngine.  When no implementations are available, the original
stubs (which raise ``NotImplementedError``) are returned.

Usage::

    from fraudai.agents.tool_registry import ToolRegistry
    from fraudai.tools.implementations import ToolImplementations
    from fraudai.tools.sandbox import SandboxEngine

    sandbox = SandboxEngine()
    tool_impls = ToolImplementations(sandbox=sandbox)
    registry = ToolRegistry(
        retriever=legal_retriever,
        sandbox=sandbox,
        tool_impls=tool_impls,
    )
    harvey_tools = registry.get_tools_for_agent("harvey")
"""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool as langchain_tool

from fraudai.agents.tools import (
    adversarial_evasion,
    analyze_transactions,
    compliance_checklist,
    create_search_boe,
    data_quality_check,
    detect_patterns,
    generate_pipeline,
    generate_rules,
    generate_sar_report,
    graph_analysis,
    prompt_injection_suite,
    risk_scoring,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from fraudai.rag.retriever import LegalRetriever
    from fraudai.tools.implementations import ToolImplementations
    from fraudai.tools.sandbox import SandboxEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent -> tool names mapping (search_boe is injected separately)
# ---------------------------------------------------------------------------

_AGENT_STATIC_TOOLS: dict[str, list[Any]] = {
    "harvey": [analyze_transactions, detect_patterns, risk_scoring, generate_rules],
    "louis": [generate_sar_report, compliance_checklist],
    "jessica": [graph_analysis],
    "mike": [adversarial_evasion, prompt_injection_suite],
    "rachel": [generate_pipeline, data_quality_check],
}

# Agents that require the search_boe tool.
_AGENTS_WITH_SEARCH_BOE: frozenset[str] = frozenset(
    {"harvey", "louis", "jessica", "mike", "rachel"},
)

# Mapping from stub tool function name to ToolImplementations method name.
_TOOL_IMPL_METHOD: dict[str, str] = {
    "analyze_transactions": "analyze_transactions",
    "detect_patterns": "detect_patterns",
    "risk_scoring": "risk_scoring",
    "generate_rules": "generate_rules",
    "generate_sar_report": "generate_sar_report",
    "compliance_checklist": "compliance_checklist",
    "graph_analysis": "graph_analysis",
    "adversarial_evasion": "adversarial_evasion",
    "prompt_injection_suite": "prompt_injection_suite",
    "generate_pipeline": "generate_pipeline",
    "data_quality_check": "data_quality_check",
}


def _wrap_impl_as_tool(
    stub_tool: Any,
    impl_method: Callable[..., Any],
) -> Callable[..., Any]:
    """Create a LangChain tool backed by a real implementation method.

    Preserves the original tool's name, description, and schema while
    replacing its invocation logic with the real implementation.

    Args:
        stub_tool: The original LangChain ``@tool`` decorated function.
        impl_method: The bound method from ``ToolImplementations``.

    Returns:
        A new LangChain tool with the same metadata but real execution.
    """
    tool_name = getattr(stub_tool, "name", None) or getattr(stub_tool, "__name__", "unknown_tool")
    tool_description = (
        getattr(stub_tool, "description", None) or getattr(stub_tool, "__doc__", "") or ""
    )

    from langchain_core.tools import StructuredTool

    args_schema = getattr(stub_tool, "args_schema", None)

    async def _async_run(**kwargs: Any) -> Any:
        return await impl_method(**kwargs)

    return StructuredTool.from_function(
        coroutine=_async_run,
        name=tool_name,
        description=tool_description,
        args_schema=args_schema,
    )


class ToolRegistry:
    """Manages tool instances with injected dependencies.

    Tools need access to shared services (retriever, sandbox, etc.)
    but LangChain ``@tool`` functions are plain functions.  This registry
    creates closures with injected dependencies.

    Args:
        retriever: A fully initialised ``LegalRetriever`` for RAG tools.
        sandbox:   Optional sandbox engine for code execution tools.
        tool_impls: Optional ``ToolImplementations`` instance for real
            tool execution.  When provided, stubs are replaced with
            sandbox-backed implementations.
    """

    def __init__(
        self,
        retriever: LegalRetriever,
        sandbox: SandboxEngine | None = None,
        tool_impls: ToolImplementations | None = None,
    ) -> None:
        self._retriever = retriever
        self._sandbox = sandbox
        self._tool_impls = tool_impls
        self._search_boe: Callable[..., Any] | None = None
        self._impl_tools_cache: dict[str, Callable[..., Any]] = {}
        logger.info(
            "ToolRegistry initialized (retriever=%s, sandbox=%s, tool_impls=%s)",
            type(retriever).__name__,
            type(sandbox).__name__ if sandbox is not None else "None",
            type(tool_impls).__name__ if tool_impls is not None else "None",
        )

    # ------------------------------------------------------------------
    # Individual tool getters
    # ------------------------------------------------------------------

    def get_search_boe(self) -> Callable[..., Any]:
        """Return a ``search_boe`` tool bound to the retriever.

        The tool is created once and cached for the lifetime of the
        registry instance.

        Returns:
            An async LangChain tool function.
        """
        if self._search_boe is None:
            self._search_boe = create_search_boe(self._retriever)
            logger.debug("Created search_boe tool bound to retriever")
        return self._search_boe

    def _get_impl_tool(self, stub_tool: Any) -> Any:
        """Return an implementation-backed tool for the given stub.

        If ``ToolImplementations`` is available and has a method for this
        tool, wraps it as a LangChain tool.  Otherwise returns the stub.

        The wrapped tool is cached for the registry's lifetime.
        """
        tool_name = getattr(stub_tool, "name", getattr(stub_tool, "__name__", ""))

        if self._tool_impls is None:
            return stub_tool

        if tool_name in self._impl_tools_cache:
            return self._impl_tools_cache[tool_name]

        method_name = _TOOL_IMPL_METHOD.get(tool_name)
        if method_name is None:
            return stub_tool

        impl_method = getattr(self._tool_impls, method_name, None)
        if impl_method is None:
            logger.warning(
                "ToolImplementations has no method '%s' for tool '%s'",
                method_name,
                tool_name,
            )
            return stub_tool

        wrapped = _wrap_impl_as_tool(stub_tool, impl_method)
        self._impl_tools_cache[tool_name] = wrapped
        logger.debug("Created implementation-backed tool '%s'", tool_name)
        return wrapped

    # ------------------------------------------------------------------
    # Per-agent tool lists
    # ------------------------------------------------------------------

    def get_tools_for_agent(self, agent_name: str) -> list[Callable[..., Any]]:
        """Return tools for a specific agent with dependencies injected.

        When ``ToolImplementations`` is available, stub tools are replaced
        with real sandbox-backed implementations.  ``search_boe`` is
        always replaced with the retriever-bound version.

        Args:
            agent_name: Agent identifier (lowercase: "harvey", "louis", etc.).

        Returns:
            List of tool callables ready for binding to the LLM.

        Raises:
            ValueError: If *agent_name* is not a recognised agent.
        """
        key = agent_name.lower()

        if key not in _AGENT_STATIC_TOOLS:
            msg = f"Unknown agent '{agent_name}'. Valid agents: {sorted(_AGENT_STATIC_TOOLS)}"
            raise ValueError(msg)

        # Replace stubs with implementations where available
        tools: list[Callable[..., Any]] = [self._get_impl_tool(t) for t in _AGENT_STATIC_TOOLS[key]]

        if key in _AGENTS_WITH_SEARCH_BOE:
            tools.append(self.get_search_boe())

        logger.debug(
            "Returning %d tools for agent '%s': %s",
            len(tools),
            key,
            [getattr(t, "name", getattr(t, "__name__", repr(t))) for t in tools],
        )
        return tools
