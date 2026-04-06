"""LangGraph orchestration graph for FraudAI Agent.

Implements the StateGraph defined in ADR-003 (F0.5):
    START -> donna -> {harvey | louis | jessica | mike (via HITL) | rachel | clarify}
    agent -> {responder | escalate -> donna}
    responder -> END

Specialist agent nodes delegate to ``ClaudeAgentInvoker`` via the
``invoke_claude_agent()`` function (implemented in F4).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from fraudai.agents.claude_invoker import ClaudeAgentInvoker
from fraudai.agents.donna import DonnaRouter, IntentClassification
from fraudai.agents.prompts import AGENT_PROMPTS
from fraudai.agents.state import AgentState
from fraudai.agents.tools import AGENT_TOOLS
from fraudai.core.config import settings

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)


# =========================================================================
# Return type contracts
# =========================================================================

# IntentClassification is imported from fraudai.agents.donna (canonical location)
# and re-exported here for backward compatibility.
__all__ = ["IntentClassification"]


class AgentInvocationResult(TypedDict):
    """Return contract for invoke_claude_agent."""

    message: Any  # AIMessage
    tool_results: list[dict[str, Any]]
    analysis_summary: str | None
    escalation: dict[str, Any] | None


# =========================================================================
# Donna Router — lazy singleton
# =========================================================================

_donna_router: DonnaRouter | None = None


def _get_donna_router() -> DonnaRouter:
    """Return the module-level DonnaRouter singleton, creating it on first call."""
    global _donna_router  # noqa: PLW0603
    if _donna_router is None:
        _donna_router = DonnaRouter(
            ollama_host=settings.ollama_host,
            model=settings.ollama_model,
        )
    return _donna_router


async def classify_intent_local(message: str) -> IntentClassification:
    """Classify user intent using local Ollama model (Llama 3.1 8B).

    Delegates to ``DonnaRouter.classify()`` which calls Ollama with
    JSON mode and falls back to keyword matching on failure.

    Returns:
        Dict with keys ``agent`` (str | None), ``language`` ("es" | "en"),
        and ``confidence`` (float 0.0-1.0).
    """
    router = _get_donna_router()
    return await router.classify(message)


_claude_invoker: ClaudeAgentInvoker | None = None


def _get_claude_invoker() -> ClaudeAgentInvoker:
    """Return the module-level AgentInvoker singleton, creating it on first call."""
    global _claude_invoker  # noqa: PLW0603
    if _claude_invoker is None:
        provider = settings.llm_provider
        if provider == "groq":
            api_key = settings.groq_api_key
        elif provider == "anthropic":
            api_key = settings.anthropic_api_key
        else:
            api_key = settings.anthropic_api_key
        _claude_invoker = ClaudeAgentInvoker(
            api_key=api_key,
            model=settings.llm_model,
            provider=provider,
        )
    return _claude_invoker


async def invoke_claude_agent(
    agent_name: str,
    system_prompt: str,
    tools: list[Any],
    state: AgentState,
) -> AgentInvocationResult:
    """Invoke a Claude-backed specialist agent.

    Delegates to ``ClaudeAgentInvoker.invoke()`` which handles tool binding,
    retry logic, and escalation detection.

    Returns:
        Dict with keys ``message`` (AIMessage), ``tool_results`` (list),
        ``analysis_summary`` (str | None), ``escalation`` (dict | None).
    """
    invoker = _get_claude_invoker()
    return await invoker.invoke(agent_name, system_prompt, tools, state)


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


_MAX_ESCALATIONS = 3


def route_after_agent(state: AgentState) -> str:
    """Decide whether the agent responds directly or escalates.

    If the agent set an ``escalation_request``, return to Donna for
    re-routing.  Caps at _MAX_ESCALATIONS to prevent infinite loops (Bug #27).
    """
    if state.get("escalation_request") and state.get("turn_count", 0) < _MAX_ESCALATIONS:
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

    If ``current_agent`` is already set (via agent_override), skip
    classification and respect the override.
    """
    # Bug #1 fix: respect agent_override from ChatRequest
    if state.get("current_agent") is not None:
        logger.info("Donna: agent_override active, skipping classification -> %s", state["current_agent"])
        return {"turn_count": state.get("turn_count", 0) + 1}

    last_message = state["messages"][-1]
    raw_content = last_message.content if hasattr(last_message, "content") else str(last_message)
    user_text = raw_content if isinstance(raw_content, str) else str(raw_content)

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
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)
    action_desc = f"Mike Ross wants to execute red teaming tools. Last user request: {user_text}"

    user_decision = interrupt(
        {
            "action": "confirm_red_teaming",
            "description": action_desc,
            "warning": (
                "This action will execute offensive security tools against the specified target."
            ),
        }
    )

    approved = user_decision.get("approved", False) if isinstance(user_decision, dict) else False

    return {
        "needs_human_confirmation": not approved,
    }


_CLARIFICATION_MESSAGE = (
    "Soy Donna Paulsen, directora del bufete FraudAI. "
    "Puedo derivarte al especialista adecuado. Dime en qué necesitas ayuda:\n\n"
    "- **Harvey Specter** — Análisis de transacciones y detección de fraude\n"
    "- **Louis Litt** — Normativa AML, KYC, compliance y reportes regulatorios\n"
    "- **Jessica Pearson** — Investigación de redes de fraude y análisis de grafos\n"
    "- **Mike Ross** — Red teaming y seguridad de modelos de IA\n"
    "- **Rachel Zane** — Pipelines de datos y feature engineering\n\n"
    "Cuéntame tu caso y te derivo al especialista correcto."
)


async def responder_node(state: AgentState) -> dict[str, Any]:
    """Format the final response to the user.

    Handles three cases:
    1. Clarification: Donna couldn't route — ask the user for more detail.
    2. Mike cancellation: user rejected a red teaming action.
    3. Pass-through: the specialist's response is already in messages.
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

    # If Donna couldn't classify (agent is None or donna), send clarification
    current = state.get("current_agent")
    if current is None or current == "donna":
        return {
            "messages": [AIMessage(content=_CLARIFICATION_MESSAGE)],
        }

    # Pass-through: the specialist's response is already in messages
    return {}


# =========================================================================
# Graph builder
# =========================================================================


def build_fraud_ai_graph() -> CompiledStateGraph:  # type: ignore[type-arg]
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
