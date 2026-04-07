"use client";

import { useState, useCallback, useRef } from "react";
import type {
  Message,
  AgentName,
  ChatResponse,
  ToolResult,
} from "@/lib/types";
import { streamChat } from "@/lib/sse";
import {
  sendMessage as apiSendMessage,
  uploadFile as apiUploadFile,
  confirmAction as apiConfirmAction,
  sendFeedback as apiFeedback,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Unique ID generator (avoids crypto dep in client components)
// ---------------------------------------------------------------------------

let counter = 0;
function uid(): string {
  counter += 1;
  return `msg_${Date.now()}_${counter}`;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentAgent, setCurrentAgent] = useState<AgentName | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const streamBufferRef = useRef<string>("");
  const rafRef = useRef<number | null>(null);
  const assistantIdRef = useRef<string>("");

  // -----------------------------------------------------------------------
  // Send a chat message (streaming)
  // -----------------------------------------------------------------------

  const sendMessage = useCallback(
    async (content: string, agentOverride?: AgentName) => {
      if (!content.trim() || isStreaming) return;

      // Append user message
      const userMsg: Message = {
        id: uid(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      const assistantId = uid();

      setMessages((prev) => [
        ...prev,
        userMsg,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          timestamp: new Date(),
          isStreaming: true,
        },
      ]);

      setIsStreaming(true);
      streamBufferRef.current = "";
      assistantIdRef.current = assistantId;

      // Flush accumulated tokens to React state at ~30fps
      // This prevents React 18 batching from swallowing individual token updates
      const flushBuffer = () => {
        const buf = streamBufferRef.current;
        const aid = assistantIdRef.current;
        if (buf) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aid ? { ...m, content: buf } : m,
            ),
          );
        }
        rafRef.current = requestAnimationFrame(flushBuffer);
      };
      rafRef.current = requestAnimationFrame(flushBuffer);

      const controller = streamChat(
        {
          message: content,
          session_id: sessionId,
          agent_override: agentOverride ?? null,
          language: "es",
        },
        // onToken — accumulate in ref, RAF flushes to state
        (token: string) => {
          streamBufferRef.current += token;
        },
        // onToolStart
        (toolName: string) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    tool_results: [
                      ...(m.tool_results ?? []),
                      { tool_name: toolName, status: "pending" as const, result: null, duration_ms: 0 },
                    ],
                  }
                : m,
            ),
          );
        },
        // onToolResult
        (result: ToolResult) => {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const tools = (m.tool_results ?? []).map((t) =>
                t.tool_name === result.tool_name && t.status === "pending" ? result : t,
              );
              return { ...m, tool_results: tools };
            }),
          );
        },
        // onDone — stop RAF, set final content with metadata
        (response: ChatResponse) => {
          if (rafRef.current) cancelAnimationFrame(rafRef.current);
          rafRef.current = null;

          setSessionId(response.session_id);
          setCurrentAgent(response.agent as AgentName);

          const finalContent = streamBufferRef.current || response.message || "No response generated.";
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: finalContent,
                    agent: response.agent,
                    citations: response.citations,
                    tool_results: response.tool_results?.length ? response.tool_results : m.tool_results,
                    metadata: response.metadata,
                    isStreaming: false,
                  }
                : m,
            ),
          );
          setIsStreaming(false);
          abortRef.current = null;
        },
        // onError — stop RAF, show error
        (error: string) => {
          if (rafRef.current) cancelAnimationFrame(rafRef.current);
          rafRef.current = null;

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: `Error: ${error}`, isStreaming: false }
                : m,
            ),
          );
          setIsStreaming(false);
          abortRef.current = null;
        },
      );

      abortRef.current = controller;
    },
    [isStreaming, sessionId],
  );

  // -----------------------------------------------------------------------
  // File upload
  // -----------------------------------------------------------------------

  const uploadFile = useCallback(
    async (file: File) => {
      if (!sessionId) return;
      try {
        const result = await apiUploadFile(sessionId, file);
        // Append system-style message about the upload
        const msg: Message = {
          id: uid(),
          role: "assistant",
          content: `File "${result.filename}" uploaded (${result.chunks_generated} chunks indexed).`,
          agent: "donna",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, msg]);
      } catch (err: unknown) {
        const msg: Message = {
          id: uid(),
          role: "assistant",
          content: `Upload failed: ${err instanceof Error ? err.message : "Unknown error"}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, msg]);
      }
    },
    [sessionId],
  );

  // -----------------------------------------------------------------------
  // HITL confirmation
  // -----------------------------------------------------------------------

  const confirmActionHandler = useCallback(
    async (actionId: string, approved: boolean) => {
      if (!sessionId) return;
      try {
        const response = await apiConfirmAction(sessionId, actionId, approved);
        const msg: Message = {
          id: uid(),
          role: "assistant",
          content: response.message,
          agent: response.agent,
          citations: response.citations,
          tool_results: response.tool_results,
          metadata: response.metadata,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, msg]);
      } catch (err: unknown) {
        const msg: Message = {
          id: uid(),
          role: "assistant",
          content: `Confirmation failed: ${err instanceof Error ? err.message : "Unknown error"}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, msg]);
      }
    },
    [sessionId],
  );

  // -----------------------------------------------------------------------
  // Feedback
  // -----------------------------------------------------------------------

  const rateFeedback = useCallback(
    async (messageId: string, rating: number) => {
      if (!sessionId) return;
      try {
        await apiFeedback(sessionId, messageId, rating);
      } catch {
        // Silently fail — feedback is non-critical
      }
    },
    [sessionId],
  );

  // -----------------------------------------------------------------------
  // Clear / cancel
  // -----------------------------------------------------------------------

  const clearChat = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setSessionId(null);
    setCurrentAgent(null);
    setIsStreaming(false);
  }, []);

  const cancelStream = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false, content: streamBufferRef.current || m.content } : m)),
    );
  }, []);

  return {
    messages,
    isStreaming,
    sessionId,
    currentAgent,
    sendMessage,
    uploadFile,
    confirmAction: confirmActionHandler,
    rateFeedback,
    clearChat,
    cancelStream,
  };
}
