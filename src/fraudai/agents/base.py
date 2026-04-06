"""Base class for FraudAI Agent specialists.

Provides the abstract interface that every specialist agent (Harvey, Louis,
Jessica, Mike, Rachel) must implement.  Donna (router) does NOT use this
base class — it runs a local model with a different invocation path.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fraudai.agents.state import AgentState

logger = logging.getLogger(__name__)


class FraudAgent(ABC):
    """Base class for all FraudAI specialist agents.

    Attributes:
        name:          Agent identifier (e.g. ``"harvey"``).
        system_prompt: Full system prompt injected into every LLM call.
        tools:         List of LangChain ``@tool`` functions the agent may
                       invoke.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list[Any],
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        logger.info("Initialized agent '%s' with %d tools", name, len(tools))

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def invoke(self, state: AgentState) -> dict[str, Any]:
        """Process the current graph state and return state updates.

        Implementations should:
        1. Build the message payload from ``state["messages"]``.
        2. Call the backing LLM (Claude API) with ``self.system_prompt``
           and ``self.tools``.
        3. Handle any tool calls and collect results.
        4. Return a dict of state updates (at minimum ``messages`` and
           ``tool_results``).

        Args:
            state: The current ``AgentState`` snapshot.

        Returns:
            Dict of partial state updates to merge back into the graph.
        """
        ...

    # ------------------------------------------------------------------
    # Helpers (available to subclasses)
    # ------------------------------------------------------------------

    def should_escalate(self, state: AgentState) -> dict[str, Any] | None:
        """Check whether the current state warrants escalation.

        Subclasses may override this to implement domain-specific
        escalation logic (e.g. Harvey detects money laundering and
        recommends Louis).

        Returns:
            An escalation request dict or ``None``.
        """
        return None

    def __repr__(self) -> str:
        return f"FraudAgent(name={self.name!r}, tools={len(self.tools)})"
