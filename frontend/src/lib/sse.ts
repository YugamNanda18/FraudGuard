import type { ChatRequest, ChatResponse, ToolResult, SSEEvent } from "./types";
import { getAuthToken } from "./api";

const rawApiBase =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const API_BASE = rawApiBase.replace(/\/$/, "");

// ---------------------------------------------------------------------------
// SSE line parser
// ---------------------------------------------------------------------------

/**
 * Parse a single SSE "data:" line into a typed event.
 * Returns null for keep-alive or malformed lines.
 */
function parseSSELine(line: string): SSEEvent | null {
  if (!line.startsWith("data:")) return null;

  const json = line.slice("data:".length).trim();
  if (!json || json === "[DONE]") return null;

  try {
    return JSON.parse(json) as SSEEvent;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Stream chat — fetch + ReadableStream SSE client
// ---------------------------------------------------------------------------

/**
 * Opens an SSE connection to POST /chat/stream and dispatches
 * typed callbacks as events arrive.
 *
 * Returns an AbortController so the caller can cancel the stream.
 */
export function streamChat(
  chatRequest: ChatRequest,
  onToken: (content: string) => void,
  onToolStart: (toolName: string) => void,
  onToolResult: (result: ToolResult) => void,
  onDone: (response: ChatResponse) => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();

  const run = async () => {
    try {
      const token = getAuthToken();
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(chatRequest),
        signal: controller.signal,
      });


      if (!res.ok) {
        const text = await res.text().catch(() => "Stream request failed");
        onError(`HTTP ${res.status}: ${text}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No readable stream in response");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines
        const parts = buffer.split("\n\n");
        // Keep the last (possibly incomplete) chunk in the buffer
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          // Each SSE event can have multiple lines (event:, data:, etc.)
          const lines = part.split("\n");
          for (const line of lines) {
            const event = parseSSELine(line);
            if (!event) continue;

            switch (event.type) {
              case "token":
                onToken(event.content);
                break;
              case "tool_start":
                onToolStart(event.tool_name);
                break;
              case "tool_result":
                onToolResult(event.tool_result);
                break;
              case "done":
                onDone(event.response);
                break;
              case "error":
                onError(event.message);
                break;
            }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        // User cancelled — not an error
        return;
      }
      onError(err instanceof Error ? err.message : "Unknown streaming error");
    }
  };

  run();

  return controller;
}
