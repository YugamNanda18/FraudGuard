"""FraudAI Agent — multi-agent orchestration layer.

Public API:
    build_fraud_ai_graph  — compile the LangGraph orchestration graph
    AgentState            — shared state TypedDict
    FraudAgent            — abstract base class for specialist agents
    ClaudeAgentInvoker    — Claude API invoker with tool use and retry
    AGENT_PROMPTS         — registry of system prompts by agent name
    AGENT_TOOLS           — registry of tool lists by agent name
"""

from fraudai.agents.base import FraudAgent
from fraudai.agents.claude_invoker import ClaudeAgentInvoker
from fraudai.agents.graph import build_fraud_ai_graph
from fraudai.agents.prompts import AGENT_PROMPTS
from fraudai.agents.state import AgentState
from fraudai.agents.tools import AGENT_TOOLS

__all__ = [
    "AgentState",
    "AGENT_PROMPTS",
    "AGENT_TOOLS",
    "ClaudeAgentInvoker",
    "FraudAgent",
    "build_fraud_ai_graph",
]
