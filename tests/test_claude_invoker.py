"""Tests for ClaudeAgentInvoker -- all API calls mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from fraudai.agents.claude_invoker import ClaudeAgentInvoker

# Placeholder value for the api_key parameter in tests.
# This is NOT a real key -- it never reaches any API because ChatAnthropic
# is always mocked.
_PLACEHOLDER_KEY = "FAKE_NOT_A_REAL_KEY"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _base_state(**overrides: Any) -> dict[str, Any]:
    """Build a minimal AgentState dict for testing."""
    state: dict[str, Any] = {
        "messages": [HumanMessage(content="Analyze this transaction for fraud.")],
        "current_agent": "harvey",
        "previous_agent": None,
        "session_id": "test-session",
        "tenant_id": "test-tenant",
        "user_tier": "pro",
        "shared_context": {},
        "uploaded_documents": [],
        "tool_results": [],
        "escalation_request": None,
        "needs_human_confirmation": False,
        "language": "es",
        "turn_count": 1,
    }
    state.update(overrides)
    return state


def _make_ai_message(
    content: str = "Analysis complete.",
    tool_calls: list[dict[str, Any]] | None = None,
    usage_metadata: dict[str, int] | None = None,
) -> AIMessage:
    """Build an AIMessage with optional tool_calls and usage metadata."""
    msg = AIMessage(content=content)
    if tool_calls is not None:
        msg.tool_calls = tool_calls  # type: ignore[attr-defined]
    if usage_metadata is not None:
        msg.usage_metadata = usage_metadata  # type: ignore[attr-defined]
    return msg


def _make_mock_tool(name: str, return_value: Any = None) -> MagicMock:
    """Create a mock LangChain tool with the given name."""
    mock_tool = MagicMock()
    mock_tool.name = name
    mock_tool.ainvoke = AsyncMock(return_value=return_value or {"result": f"{name}_output"})
    return mock_tool


def _mock_model_returning(ai_msg: AIMessage) -> MagicMock:
    """Create a mock ChatAnthropic that returns *ai_msg* on ainvoke.

    Sets up both ``model.ainvoke`` (used when tools=[]) and
    ``model.bind_tools().ainvoke`` (used when tools are provided).
    """
    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(return_value=ai_msg)
    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(return_value=ai_msg)
    mock_model.bind_tools = MagicMock(return_value=mock_bound)
    return mock_model


# ---------------------------------------------------------------------------
# Test: simple invocation (no tool calls)
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_invoke_simple_response(mock_chat_cls: MagicMock) -> None:
    """Model returns a plain text response with no tool calls."""
    ai_msg = _make_ai_message(
        content="This transaction shows no anomalies.",
        usage_metadata={"input_tokens": 100, "output_tokens": 50},
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()
    tools = [_make_mock_tool("analyze_transactions")]

    result = await invoker.invoke("harvey", "You are Harvey.", tools, state)

    assert result["message"] is ai_msg
    assert result["tool_results"] == []
    assert result["escalation"] is None
    assert result["analysis_summary"] is not None
    assert "no anomalies" in result["analysis_summary"]


# ---------------------------------------------------------------------------
# Test: invocation with tool call
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_invoke_with_tool_call(mock_chat_cls: MagicMock) -> None:
    """Model returns a tool call; the tool is executed and result captured."""
    tool_call = {
        "name": "analyze_transactions",
        "args": {"data_path": "/sandbox/txns.csv", "file_format": "csv"},
        "id": "call_001",
    }
    ai_msg = _make_ai_message(
        content="Let me analyze these transactions.",
        tool_calls=[tool_call],
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    mock_tool = _make_mock_tool(
        "analyze_transactions",
        return_value={"anomalies": 3, "total": 100},
    )

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [mock_tool], state)

    assert len(result["tool_results"]) == 1
    tr = result["tool_results"][0]
    assert tr["tool_name"] == "analyze_transactions"
    assert tr["status"] == "success"
    assert tr["tool_output"] == {"anomalies": 3, "total": 100}
    mock_tool.ainvoke.assert_awaited_once_with(
        {"data_path": "/sandbox/txns.csv", "file_format": "csv"}
    )


# ---------------------------------------------------------------------------
# Test: tool call with missing tool
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_invoke_tool_not_found(mock_chat_cls: MagicMock) -> None:
    """Model calls a tool that is not in the agent's tool list."""
    tool_call = {"name": "nonexistent_tool", "args": {}, "id": "call_002"}
    ai_msg = _make_ai_message(content="Calling tool.", tool_calls=[tool_call])
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [], state)

    assert len(result["tool_results"]) == 1
    tr = result["tool_results"][0]
    assert tr["status"] == "error"
    assert "not found" in tr["error"]


# ---------------------------------------------------------------------------
# Test: tool execution failure
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_invoke_tool_execution_error(mock_chat_cls: MagicMock) -> None:
    """Tool raises an exception during execution."""
    tool_call = {"name": "analyze_transactions", "args": {}, "id": "call_003"}
    ai_msg = _make_ai_message(content="Running analysis.", tool_calls=[tool_call])
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    failing_tool = _make_mock_tool("analyze_transactions")
    failing_tool.ainvoke = AsyncMock(
        side_effect=NotImplementedError("Sandbox execution not yet connected (F4)")
    )

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [failing_tool], state)

    assert len(result["tool_results"]) == 1
    tr = result["tool_results"][0]
    assert tr["status"] == "error"
    assert "Sandbox execution not yet connected" in tr["error"]


# ---------------------------------------------------------------------------
# Test: escalation detection
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_escalation_detected_explicit(mock_chat_cls: MagicMock) -> None:
    """Agent explicitly says 'I need to escalate'."""
    ai_msg = _make_ai_message(
        content="I detected money laundering patterns. I need to escalate this to compliance."
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [], state)

    assert result["escalation"] is not None
    assert result["escalation"]["source"] == "harvey"


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_escalation_detected_with_target(mock_chat_cls: MagicMock) -> None:
    """Agent says 'escalate to louis' -- target agent extracted."""
    ai_msg = _make_ai_message(
        content="These patterns require compliance review. Escalating to Louis for SAR filing."
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [], state)

    assert result["escalation"] is not None
    assert result["escalation"]["source"] == "harvey"
    assert result["escalation"]["target"] == "louis"


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_escalation_recommend_handoff(mock_chat_cls: MagicMock) -> None:
    """Agent uses 'recommend handoff to Harvey' phrasing."""
    ai_msg = _make_ai_message(
        content="Data is clean. I recommend handoff to Harvey for fraud analysis."
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("rachel", "You are Rachel.", [], state)

    assert result["escalation"] is not None
    assert result["escalation"]["source"] == "rachel"
    assert result["escalation"]["target"] == "harvey"


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_no_escalation_on_normal_response(mock_chat_cls: MagicMock) -> None:
    """Normal response without escalation patterns returns None."""
    ai_msg = _make_ai_message(
        content="Analysis complete. No suspicious patterns detected."
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [], state)

    assert result["escalation"] is None


# ---------------------------------------------------------------------------
# Test: system prompt passed correctly (personality maintained)
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_system_prompt_passed_correctly(mock_chat_cls: MagicMock) -> None:
    """System prompt is injected as the first message in the conversation."""
    ai_msg = _make_ai_message(content="Response.")
    mock_model = _mock_model_returning(ai_msg)
    mock_chat_cls.return_value = mock_model

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    system_prompt = "You are Harvey Specter, senior fraud analyst."
    state = _base_state(
        messages=[HumanMessage(content="Check this transaction.")]
    )

    await invoker.invoke("harvey", system_prompt, [_make_mock_tool("t1")], state)

    # Verify ainvoke was called with correct message structure
    mock_bound = mock_model.bind_tools.return_value
    call_args = mock_bound.ainvoke.call_args
    messages = call_args[0][0]

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == system_prompt
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "Check this transaction."


# ---------------------------------------------------------------------------
# Test: retry on API error
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.asyncio.sleep", new_callable=AsyncMock)
@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_retry_on_api_error_recovers(
    mock_chat_cls: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Model fails twice then succeeds on third attempt."""
    ai_msg = _make_ai_message(content="Success after retries.")

    # No tools passed, so ainvoke is called directly on the model (no bind_tools).
    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(
        side_effect=[
            ConnectionError("API unavailable"),
            TimeoutError("Request timed out"),
            ai_msg,
        ]
    )
    mock_chat_cls.return_value = mock_model

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [], state)

    assert result["message"] is ai_msg
    assert mock_model.ainvoke.await_count == 3
    assert mock_sleep.await_count == 2


@patch("fraudai.agents.claude_invoker.asyncio.sleep", new_callable=AsyncMock)
@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_retry_exhausted_raises(
    mock_chat_cls: MagicMock,
    mock_sleep: AsyncMock,
) -> None:
    """Model fails all 3 attempts -- raises RuntimeError."""
    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(
        side_effect=ConnectionError("API permanently down")
    )
    mock_chat_cls.return_value = mock_model

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    with pytest.raises(RuntimeError, match="failed after 3 retries"):
        await invoker.invoke("harvey", "You are Harvey.", [], state)

    assert mock_model.ainvoke.await_count == 3
    assert mock_sleep.await_count == 2


# ---------------------------------------------------------------------------
# Test: token counting / usage logging
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_token_usage_logged(
    mock_chat_cls: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Token usage metadata is logged when available."""
    ai_msg = _make_ai_message(
        content="Done.",
        usage_metadata={"input_tokens": 250, "output_tokens": 80},
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    with caplog.at_level("INFO", logger="fraudai.agents.claude_invoker"):
        await invoker.invoke("harvey", "You are Harvey.", [], state)

    token_logs = [r for r in caplog.records if "Token usage" in r.message]
    assert len(token_logs) == 1
    assert "input=250" in token_logs[0].message
    assert "output=80" in token_logs[0].message
    assert "total=330" in token_logs[0].message


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_no_token_usage_no_error(mock_chat_cls: MagicMock) -> None:
    """Missing usage metadata does not cause an error."""
    ai_msg = _make_ai_message(content="Done.")
    # Ensure usage_metadata is not set (default AIMessage)
    ai_msg.usage_metadata = None  # type: ignore[assignment]
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    # Should not raise
    result = await invoker.invoke("harvey", "You are Harvey.", [], state)
    assert result["message"] is ai_msg


# ---------------------------------------------------------------------------
# Test: empty messages state
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_empty_messages_state(mock_chat_cls: MagicMock) -> None:
    """Invocation works when state has an empty messages list."""
    ai_msg = _make_ai_message(content="Hello, how can I help?")
    mock_model = _mock_model_returning(ai_msg)
    mock_chat_cls.return_value = mock_model

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state(messages=[])

    # Pass a tool so bind_tools path is taken (easier to inspect call args).
    result = await invoker.invoke(
        "harvey", "You are Harvey.", [_make_mock_tool("t1")], state
    )

    assert result["message"] is ai_msg

    # Verify only the system message was sent (no conversation history)
    mock_bound = mock_model.bind_tools.return_value
    call_args = mock_bound.ainvoke.call_args
    messages = call_args[0][0]
    assert len(messages) == 1
    assert isinstance(messages[0], SystemMessage)


# ---------------------------------------------------------------------------
# Test: no tools bound when tool list is empty
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_no_tools_skips_bind(mock_chat_cls: MagicMock) -> None:
    """When no tools are provided, bind_tools is NOT called."""
    ai_msg = _make_ai_message(content="No tools needed.")

    mock_model = MagicMock()
    mock_model.ainvoke = AsyncMock(return_value=ai_msg)
    mock_model.bind_tools = MagicMock()
    mock_chat_cls.return_value = mock_model

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [], state)

    mock_model.bind_tools.assert_not_called()
    mock_model.ainvoke.assert_awaited_once()
    assert result["message"] is ai_msg


# ---------------------------------------------------------------------------
# Test: analysis summary
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_analysis_summary_with_short_content(mock_chat_cls: MagicMock) -> None:
    """Content shorter than 20 chars returns None for analysis_summary."""
    ai_msg = _make_ai_message(content="OK")
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [_make_mock_tool("t1")], state)

    assert result["analysis_summary"] is None


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_analysis_summary_includes_tool_count(mock_chat_cls: MagicMock) -> None:
    """Analysis summary appends tool execution count when tools were used."""
    tool_call = {"name": "analyze_transactions", "args": {}, "id": "call_004"}
    ai_msg = _make_ai_message(
        content="Found 5 suspicious transactions in the dataset.",
        tool_calls=[tool_call],
    )
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    mock_tool = _make_mock_tool("analyze_transactions", {"count": 5})

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [mock_tool], state)

    assert result["analysis_summary"] is not None
    assert "[Tools: 1/1 succeeded]" in result["analysis_summary"]


# ---------------------------------------------------------------------------
# Test: content extraction from list-type content blocks
# ---------------------------------------------------------------------------


@patch("fraudai.agents.claude_invoker.ChatAnthropic")
async def test_content_extraction_from_blocks(mock_chat_cls: MagicMock) -> None:
    """AIMessage with list content blocks is extracted correctly."""
    ai_msg = AIMessage(content=[
        {"type": "text", "text": "First block."},
        {"type": "text", "text": "Second block."},
    ])
    mock_chat_cls.return_value = _mock_model_returning(ai_msg)

    invoker = ClaudeAgentInvoker(api_key=_PLACEHOLDER_KEY)
    state = _base_state()

    result = await invoker.invoke("harvey", "You are Harvey.", [_make_mock_tool("t1")], state)

    assert result["analysis_summary"] is not None
    assert "First block." in result["analysis_summary"]
    assert "Second block." in result["analysis_summary"]


# ---------------------------------------------------------------------------
# Test: graph integration -- invoke_claude_agent uses invoker singleton
# ---------------------------------------------------------------------------


@patch("fraudai.agents.graph._claude_invoker", None)
@patch("fraudai.agents.graph.ClaudeAgentInvoker")
async def test_graph_invoke_claude_agent_uses_singleton(
    mock_invoker_cls: MagicMock,
) -> None:
    """invoke_claude_agent in graph.py creates and reuses the singleton."""
    from fraudai.agents.graph import invoke_claude_agent

    mock_instance = MagicMock()
    mock_instance.invoke = AsyncMock(return_value={
        "message": AIMessage(content="test response"),
        "tool_results": [],
        "analysis_summary": None,
        "escalation": None,
    })
    mock_invoker_cls.return_value = mock_instance

    state = _base_state()
    await invoke_claude_agent("harvey", "prompt", [], state)
    await invoke_claude_agent("louis", "prompt2", [], state)

    # Constructor called only once (singleton)
    mock_invoker_cls.assert_called_once()
    # invoke called twice
    assert mock_instance.invoke.await_count == 2
