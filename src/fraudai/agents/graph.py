"""LangGraph orchestration graph for FraudAI Agent.

Implements the StateGraph defined in ADR-003 (F0.5):
    START -> donna -> {harvey | louis | jessica | mike (via HITL) | rachel | clarify}
    agent -> {responder | escalate -> donna}
    responder -> END

Nodes for specialist agents are stubs calling ``invoke_claude_agent()`` —
the real implementation connecting to Claude API will be added in F4.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from fraudai.agents.prompts import AGENT_PROMPTS
from fraudai.agents.state import AgentState
from fraudai.agents.tools import AGENT_TOOLS

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)


# =========================================================================
# Placeholder — will be replaced in F4
# =========================================================================


async def classify_intent_local(message: str) -> dict[str, Any]:
    """Classify user intent using local Ollama model (Llama 3.1 8B).

    Stub — returns a placeholder classification.  Real implementation
    will call Ollama in F4.

    Returns:
        Dict with keys ``agent`` (str) and ``language`` ("es" | "en").
    """
    logger.warning("classify_intent_local is a stub — returning default routing")
    return {"agent": "harvey", "language": "es", "confidence": 0.0}


async def invoke_claude_agent(
    agent_name: str,
    system_prompt: str,
    tools: list,
    state: AgentState,
) -> dict[str, Any]:
    """Invoke a Claude-backed specialist agent.

    Stub — returns a placeholder response.  Real implementation will call
    the Anthropic API via ``langchain-anthropic`` in F4.

    Returns:
        Dict with keys ``message`` (AIMessage), ``tool_results`` (list),
        ``analysis_summary`` (str | None), ``escalation`` (dict | None).
    """
    logger.warning(
        "invoke_claude_agent('%s') is a stub — returning placeholder", agent_name
    )
    return {
        "message": AIMessage(
            content=f"[{agent_name}] Stub response — implementation pending (F4)."
        ),
        "tool_results": [],
        "analysis_summary": None,
        "escalation": None,
    }


# =========================================================================
# Routing functions
# =========================================================================


def route_from_donna(state: AgentState) -> str:
    """Route from Donna to the appropriate specialist or clarification.

    If ``current_agent`` is set by Donna's classification, route there.
    Mike always goes through human_confirmation first.  If no agent was
    determined, ask the user for clarification.
    """
    agent = state.get("current_agent")
    if agent == "mike":
        return "mike_confirmation"
    if agent in {"harvey", "louis", "jessica", "rachel"}:
        return agent
    return "clarify"


def route_after_agent(state: AgentState) -> str:
    """Decide whether the agent responds directly or escalates.

    If the agent set an ``escalation_request``, return to Donna for
    re-routing.  Otherwise proceed to the responder node.
    """
    if state.get("escalation_request"):
        return "escalate"
    return "respond"


def route_after_confirmation(state: AgentState) -> str:
    """Route after human confirmation for Mike's red teaming actions.

    If the user rejected, go straight to responder with a cancellation
    message.  Otherwise proceed to Mike's agent node.
    """
    if state.get("needs_human_confirmation"):
        return "rejected"
    return "approved"


# =========================================================================
# Graph nodes
# =========================================================================


async def donna_router_node(state: AgentState) -> dict[str, Any]:
    """Donna: classify user intent with local model and update routing.

    Uses Ollama (Llama 3.1 8B Q4_K_M) for lightweight intent
    classification into one of five specialist categories.
    """
    last_message = state["messages"][-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    classification = await classify_intent_local(user_text)

    return {
        "current_agent": classification.get("agent"),
        "previous_agent": state.get("current_agent"),
        "language": classification.get("language", "es"),
        "turn_count": state.get("turn_count", 0) + 1,
    }


async def _specialist_node(
    agent_name: str,
    state: AgentState,
) -> dict[str, Any]:
    """Generic specialist node — calls invoke_claude_agent with the
    appropriate prompt and tools for *agent_name*.
    """
    response = await invoke_claude_agent(
        agent_name=agent_name,
        system_prompt=AGENT_PROMPTS[agent_name],
        tools=AGENT_TOOLS.get(agent_name, []),
        state=state,
    )

    shared_ctx = dict(state.get("shared_context") or {})
    if response.get("analysis_summary"):
        shared_ctx["last_analysis"] = response["analysis_summary"]

    return {
        "messages": [response["message"]],
        "tool_results": response.get("tool_results", []),
        "shared_context": shared_ctx,
        "escalation_request": response.get("escalation"),
    }


async def harvey_agent_node(state: AgentState) -> dict[str, Any]:
    """Harvey Specter: transaction fraud analysis."""
    return await _specialist_node("harvey", state)


async def louis_agent_node(state: AgentState) -> dict[str, Any]:
    """Louis Litt: AML/KYC/compliance."""
    return await _specialist_node("louis", state)


async def jessica_agent_node(state: AgentState) -> dict[str, Any]:
    """Jessica Pearson: fraud intelligence and investigation."""
    return await _specialist_node("jessica", state)


async def mike_agent_node(state: AgentState) -> dict[str, Any]:
    """Mike Ross: AI red teaming and adversarial security."""
    return await _specialist_node("mike", state)


async def rachel_agent_node(state: AgentState) -> dict[str, Any]:
    """Rachel Zane: data engineering and feature intelligence."""
    return await _specialist_node("rachel", state)


async def human_confirmation_node(state: AgentState) -> dict[str, Any]:
    """Pause the graph for human approval before Mike executes.

    Uses LangGraph ``interrupt()`` to suspend execution.  The frontend
    must resume via ``Command(resume={"approved": True/False})``.
    """
    last_message = state["messages"][-1]
    user_text = (
        last_message.content
        if hasattr(last_message, "content")
        else str(last_message)
    )
    action_desc = (
        f"Mike Ross wants to execute red teaming tools. "
        f"Last user request: {user_text}"
    )

    user_decision = interrupt(
        {
            "action": "confirm_red_teaming",
            "description": action_desc,
            "warning": (
                "This action will execute offensive security tools against "
                "the specified target."
            ),
        }
    )

    approved = user_decision.get("approved", False) if isinstance(user_decision, dict) else False

    return {
        "needs_human_confirmation": not approved,
    }


async def responder_node(state: AgentState) -> dict[str, Any]:
    """Format the final response to the user.

    In the current stub this is a pass-through — the last message in
    state already contains the agent's response.  In F4 this node will
    handle response formatting, citation injection, and streaming setup.
    """
    # If the user rejected Mike's action, add a cancellation message
    if state.get("needs_human_confirmation") and state.get("current_agent") == "mike":
        return {
            "messages": [
                AIMessage(
                    content="Red teaming action cancelled by user. "
                    "No offensive tools were executed."
                )
            ],
            "needs_human_confirmation": False,
        }

    # Pass-through: the specialist's response is already in messages
    return {}


# =========================================================================
# Graph builder
# =========================================================================


def build_fraud_ai_graph() -> CompiledStateGraph:
    """Build and compile the FraudAI orchestration graph.

    Returns a compiled ``StateGraph`` with MemorySaver checkpointer
    (suitable for development and testing).  Production deployments
    should replace with ``PostgresSaver``.
    """
    graph = StateGraph(AgentState)

    # --- Nodes ---
    graph.add_node("donna", donna_router_node)
    graph.add_node("harvey", harvey_agent_node)
    graph.add_node("louis", louis_agent_node)
    graph.add_node("jessica", jessica_agent_node)
    graph.add_node("mike", mike_agent_node)
    graph.add_node("rachel", rachel_agent_node)
    graph.add_node("human_confirmation", human_confirmation_node)
    graph.add_node("responder", responder_node)

    # --- Edges ---

    # START -> Donna always
    graph.add_edge(START, "donna")

    # Donna -> specialist via conditional routing
    graph.add_conditional_edges(
        "donna",
        route_from_donna,
        {
            "harvey": "harvey",
            "louis": "louis",
            "jessica": "jessica",
            "mike_confirmation": "human_confirmation",
            "rachel": "rachel",
            "clarify": "responder",
        },
    )

    # Each specialist -> responder OR escalation back to Donna
    for agent_name in ("harvey", "louis", "jessica", "mike", "rachel"):
        graph.add_conditional_edges(
            agent_name,
            route_after_agent,
            {
                "respond": "responder",
                "escalate": "donna",
            },
        )

    # Human confirmation -> Mike (approved) or responder (rejected)
    graph.add_conditional_edges(
        "human_confirmation",
        route_after_confirmation,
        {
            "approved": "mike",
            "rejected": "responder",
        },
    )

    # Responder -> END
    graph.add_edge("responder", END)

    # --- Compile ---
    checkpointer = MemorySaver()

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_confirmation"],
    )
