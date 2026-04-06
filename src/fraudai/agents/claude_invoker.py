"""LLM agent invoker with multi-provider support.

Supports Anthropic (Claude), Groq, and OpenAI-compatible providers.
Uses ``ChatAnthropic``, ``ChatGroq``, or ``ChatOpenAI`` from langchain
with tool binding, retry logic, and escalation detection.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage

from fraudai.core.metrics import AGENT_INVOCATIONS, AGENT_LATENCY, TOKENS_USED

if TYPE_CHECKING:
    from fraudai.agents.graph import AgentInvocationResult
    from fraudai.agents.state import AgentState

logger = logging.getLogger(__name__)

# Patterns that indicate an agent wants to escalate to another specialist.
_ESCALATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"I need to escalate", re.IGNORECASE),
    re.compile(r"This requires (\w+)", re.IGNORECASE),
    re.compile(r"recommend(?:ing)?\s+escalat(?:ion|ing)", re.IGNORECASE),
    re.compile(
        r"recommend(?:ing)?\s+(?:handoff|consulting|handing off)\s+(?:to\s+)?(\w+)",
        re.IGNORECASE,
    ),
    re.compile(r"escalat(?:e|ing)\s+to\s+(\w+)", re.IGNORECASE),
]

_KNOWN_AGENTS = {"harvey", "louis", "jessica", "mike", "rachel", "donna"}

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds


def _build_llm(
    provider: str,
    api_key: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> BaseChatModel:
    """Build the appropriate LangChain chat model for the given provider."""
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(  # type: ignore[call-arg]
            model=model,
            anthropic_api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    if provider == "groq":
        from langchain_groq import ChatGroq  # type: ignore[import-untyped]

        return ChatGroq(  # type: ignore[call-arg]
            model=model,
            groq_api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(  # type: ignore[call-arg]
            model=model,
            openai_api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    msg = f"Unknown LLM provider: {provider}. Supported: anthropic, groq, openai"
    raise ValueError(msg)


class ClaudeAgentInvoker:
    """Invokes LLM agents via langchain with tool use.

    Supports multiple providers (Anthropic, Groq, OpenAI) configured via
    the ``provider`` parameter. Encapsulates model construction, tool
    binding, retry logic, and escalation detection.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        provider: str = "anthropic",
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> None:
        self._model = _build_llm(provider, api_key, model, max_tokens, temperature)
        self._model_name = model
        self._provider = provider
        logger.info(
            "AgentInvoker initialised — provider=%s, model=%s, max_tokens=%d",
            provider,
            model,
            max_tokens,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def invoke(
        self,
        agent_name: str,
        system_prompt: str,
        tools: list[Any],
        state: AgentState,
    ) -> AgentInvocationResult:
        """Invoke Claude with agent personality, tools, and conversation history.

        Steps:
            1. Build message list from ``state["messages"]``.
            2. Bind tools to the model.
            3. Invoke with system prompt.
            4. Process tool calls if any.
            5. Detect escalation intent in the response.
            6. Return structured ``AgentInvocationResult``.

        Returns:
            Dict matching the ``AgentInvocationResult`` TypedDict contract.
        """
        import time as _time

        AGENT_INVOCATIONS.labels(agent_name=agent_name).inc()
        start = _time.monotonic()

        messages = self._build_messages(system_prompt, state)
        model = self._bind_tools(tools)

        ai_message = await self._invoke_with_retry(model, messages, agent_name)

        # Process tool calls and re-invoke LLM with results if needed
        tool_results = await self._process_tool_calls(ai_message, tools)

        if tool_results:
            # Send tool results back to LLM for final text response
            from langchain_core.messages import ToolMessage

            messages_with_tools = [*messages, ai_message]
            for tr in tool_results:
                tool_call_id = ""
                for tc in getattr(ai_message, "tool_calls", []):
                    tc_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                    if tc_name == tr["tool_name"]:
                        tool_call_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
                        break
                messages_with_tools.append(
                    ToolMessage(
                        content=str(tr.get("tool_output", tr.get("error", "No output"))),
                        tool_call_id=tool_call_id or tr["tool_name"],
                    )
                )
            # Re-invoke without tools to get final text response
            ai_message = await self._invoke_with_retry(
                self._model, messages_with_tools, agent_name
            )

        duration = _time.monotonic() - start
        AGENT_LATENCY.labels(agent_name=agent_name).observe(duration)

        # Extract content for analysis
        content = self._extract_content(ai_message)

        # Detect escalation intent
        escalation = self._detect_escalation(content, agent_name)

        # Build analysis summary from tool results
        analysis_summary = self._build_analysis_summary(agent_name, content, tool_results)

        # Log token usage if available
        self._log_token_usage(ai_message, agent_name)
        self._record_token_metrics(ai_message, agent_name)

        return {
            "message": ai_message,
            "tool_results": tool_results,
            "analysis_summary": analysis_summary,
            "escalation": escalation,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(system_prompt: str, state: AgentState) -> list[Any]:
        """Build the message list from system prompt and conversation history."""
        messages: list[Any] = [SystemMessage(content=system_prompt)]
        state_messages = state.get("messages") or []
        messages.extend(state_messages)
        return messages

    def _bind_tools(self, tools: list[Any]) -> ChatAnthropic:
        """Return a model copy with tools bound, or the bare model if no tools."""
        if tools:
            return self._model.bind_tools(tools)  # type: ignore[return-value]
        return self._model

    async def _invoke_with_retry(
        self,
        model: Any,
        messages: list[Any],
        agent_name: str,
    ) -> AIMessage:
        """Call the model with exponential backoff on transient failures."""
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await model.ainvoke(messages)
                logger.info(
                    "Agent '%s' invocation succeeded on attempt %d",
                    agent_name,
                    attempt,
                )
                return response  # type: ignore[no-any-return]
            except Exception as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Agent '%s' invocation failed (attempt %d/%d): %s — retrying in %.1fs",
                        agent_name,
                        attempt,
                        _MAX_RETRIES,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Agent '%s' invocation failed after %d attempts: %s",
                        agent_name,
                        _MAX_RETRIES,
                        exc,
                    )

        raise RuntimeError(
            f"Agent '{agent_name}' invocation failed after {_MAX_RETRIES} retries"
        ) from last_error

    @staticmethod
    async def _process_tool_calls(
        ai_message: AIMessage,
        tools: list[Any],
    ) -> list[dict[str, Any]]:
        """Execute any tool calls present in the AI message.

        Returns a list of dicts with keys ``tool_name``, ``tool_input``,
        ``tool_output``, and ``status``.
        """
        tool_calls = getattr(ai_message, "tool_calls", None)
        if not tool_calls:
            return []

        # Build a name -> callable lookup from the tools list
        tool_map: dict[str, Any] = {}
        for t in tools:
            name = getattr(t, "name", None)
            if name:
                tool_map[name] = t

        results: list[dict[str, Any]] = []
        for call in tool_calls:
            tool_name = (
                call.get("name", "") if isinstance(call, dict) else getattr(call, "name", "")
            )
            tool_args = (
                call.get("args", {}) if isinstance(call, dict) else getattr(call, "args", {})
            )

            if tool_name not in tool_map:
                results.append(
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_args,
                        "tool_output": None,
                        "status": "error",
                        "error": f"Tool '{tool_name}' not found in agent tool list",
                    }
                )
                logger.warning("Tool '%s' not found in available tools", tool_name)
                continue

            try:
                tool_fn = tool_map[tool_name]
                output = await tool_fn.ainvoke(tool_args)
                results.append(
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_args,
                        "tool_output": output,
                        "status": "success",
                    }
                )
                logger.info("Tool '%s' executed successfully", tool_name)
            except Exception as exc:
                results.append(
                    {
                        "tool_name": tool_name,
                        "tool_input": tool_args,
                        "tool_output": None,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                logger.error("Tool '%s' execution failed: %s", tool_name, exc)

        return results

    @staticmethod
    def _extract_content(ai_message: AIMessage) -> str:
        """Extract text content from an AIMessage."""
        content = ai_message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Content blocks (e.g. text + tool_use)
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "\n".join(parts)
        return str(content)

    @staticmethod
    def _detect_escalation(content: str, current_agent: str) -> dict[str, Any] | None:
        """Scan response content for escalation patterns.

        Returns an escalation dict if a pattern matches, otherwise ``None``.
        """
        for pattern in _ESCALATION_PATTERNS:
            match = pattern.search(content)
            if match:
                # Try to extract the target agent name from capture groups
                target: str | None = None
                if match.lastindex and match.lastindex >= 1:
                    candidate = match.group(1).lower()
                    if candidate in _KNOWN_AGENTS and candidate != current_agent:
                        target = candidate

                return {
                    "source": current_agent,
                    "target": target,
                    "reason": match.group(0),
                }
        return None

    @staticmethod
    def _build_analysis_summary(
        agent_name: str,
        content: str,
        tool_results: list[dict[str, Any]],
    ) -> str | None:
        """Build a brief summary of the agent's analysis for shared context.

        Returns ``None`` if the content is too short to be meaningful.
        """
        if not content or len(content) < 20:
            return None

        # Take the first 500 chars as a summary
        summary = content[:500].strip()
        if len(content) > 500:
            summary += "..."

        tool_count = len(tool_results)
        success_count = sum(1 for r in tool_results if r.get("status") == "success")

        if tool_count > 0:
            summary += f" [Tools: {success_count}/{tool_count} succeeded]"

        return summary

    @staticmethod
    def _record_token_metrics(ai_message: AIMessage, agent_name: str) -> None:
        """Record token usage in Prometheus counters."""
        usage = getattr(ai_message, "usage_metadata", None)
        if not usage:
            return
        input_tokens = (
            usage.get("input_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "input_tokens", 0)
        )
        output_tokens = (
            usage.get("output_tokens", 0)
            if isinstance(usage, dict)
            else getattr(usage, "output_tokens", 0)
        )
        if input_tokens:
            TOKENS_USED.labels(agent_name=agent_name, direction="input").inc(input_tokens)
        if output_tokens:
            TOKENS_USED.labels(agent_name=agent_name, direction="output").inc(output_tokens)

    def _log_token_usage(self, ai_message: AIMessage, agent_name: str) -> None:
        """Log token usage from the response metadata if available."""
        usage = getattr(ai_message, "usage_metadata", None)
        if usage:
            input_tokens = (
                usage.get("input_tokens", 0)
                if isinstance(usage, dict)
                else getattr(usage, "input_tokens", 0)
            )
            output_tokens = (
                usage.get("output_tokens", 0)
                if isinstance(usage, dict)
                else getattr(usage, "output_tokens", 0)
            )
            total = input_tokens + output_tokens
            logger.info(
                "Token usage for '%s' [%s]: input=%d, output=%d, total=%d",
                agent_name,
                self._model_name,
                input_tokens,
                output_tokens,
                total,
            )
        else:
            logger.debug("No token usage metadata available for agent '%s'", agent_name)
