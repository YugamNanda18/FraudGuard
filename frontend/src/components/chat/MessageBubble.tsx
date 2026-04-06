"use client";

import { useState, useCallback } from "react";
import type { Message, AgentName } from "@/lib/types";
import { AGENTS } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { StreamingText } from "./StreamingText";
import { CitationCard } from "./CitationCard";
import { ToolResultCard } from "./ToolResultCard";

interface MessageBubbleProps {
  message: Message;
  onRate?: (messageId: string, rating: number) => void;
}

export function MessageBubble({ message, onRate }: MessageBubbleProps) {
  const [feedbackGiven, setFeedbackGiven] = useState<number | null>(null);
  const isUser = message.role === "user";
  const agentInfo =
    message.agent && message.agent in AGENTS
      ? AGENTS[message.agent as AgentName]
      : null;

  const handleRate = useCallback(
    (rating: number) => {
      if (feedbackGiven !== null) return;
      setFeedbackGiven(rating);
      onRate?.(message.id, rating);
    },
    [feedbackGiven, message.id, onRate],
  );

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
      role="article"
      aria-label={`${isUser ? "User" : agentInfo?.displayName ?? "Agent"} message`}
    >
      <div
        className={`
          max-w-[80%] rounded-2xl px-4 py-3
          ${
            isUser
              ? "bg-brand-600/20 text-zinc-100 rounded-br-md"
              : "bg-zinc-800 text-zinc-200 rounded-bl-md border border-zinc-700/50"
          }
        `}
      >
        {/* Agent badge */}
        {!isUser && agentInfo && (
          <div className="mb-2 flex items-center gap-2">
            <Badge color={`${agentInfo.color} text-white`}>
              {agentInfo.icon} {agentInfo.displayName}
            </Badge>
            {message.metadata && (
              <span className="text-[10px] text-zinc-500">
                {message.metadata.latency_ms}ms
              </span>
            )}
          </div>
        )}

        {/* Message content */}
        <div className="text-sm leading-relaxed">
          <StreamingText
            content={message.content}
            isStreaming={message.isStreaming ?? false}
          />
        </div>

        {/* Tool results */}
        {message.tool_results && message.tool_results.length > 0 && (
          <div className="mt-3 flex flex-col gap-2">
            {message.tool_results.map((tr, i) => (
              <ToolResultCard key={`${tr.tool_name}-${i}`} toolResult={tr} />
            ))}
          </div>
        )}

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 flex flex-col gap-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              Sources
            </span>
            {message.citations.map((c, i) => (
              <CitationCard key={`${c.boe_id}-${i}`} citation={c} index={i} />
            ))}
          </div>
        )}

        {/* Feedback buttons */}
        {!isUser && !message.isStreaming && onRate && (
          <div className="mt-2 flex items-center gap-1 border-t border-zinc-700/30 pt-2">
            <button
              type="button"
              onClick={() => handleRate(5)}
              className={`rounded p-1 text-xs transition-colors ${
                feedbackGiven === 5
                  ? "text-green-400"
                  : "text-zinc-600 hover:text-zinc-400"
              }`}
              aria-label="Rate positively"
              disabled={feedbackGiven !== null}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.633 10.5c.806 0 1.533-.446 2.031-1.08a9.041 9.041 0 012.861-2.4c.723-.384 1.35-.956 1.653-1.715a4.498 4.498 0 00.322-1.672V3a.75.75 0 01.75-.75A2.25 2.25 0 0116.5 4.5c0 1.152-.26 2.243-.723 3.218-.266.558.107 1.282.725 1.282h3.126c1.026 0 1.945.694 2.054 1.715.045.422.068.85.068 1.285a11.95 11.95 0 01-2.649 7.521c-.388.482-.987.729-1.605.729H14.23c-.483 0-.964-.078-1.423-.23l-3.114-1.04a4.501 4.501 0 00-1.423-.23H5.904M14.25 9h2.25M5.904 18.75c.083.228.22.442.406.625m-.406-.625H2.25l-.002-4.75h3.656c.296 0 .59.042.868.124" />
              </svg>
            </button>
            <button
              type="button"
              onClick={() => handleRate(1)}
              className={`rounded p-1 text-xs transition-colors ${
                feedbackGiven === 1
                  ? "text-red-400"
                  : "text-zinc-600 hover:text-zinc-400"
              }`}
              aria-label="Rate negatively"
              disabled={feedbackGiven !== null}
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 15h2.25m8.024-9.75c.011.05.028.1.052.148.591 1.2.924 2.55.924 3.977a8.96 8.96 0 01-.999 4.125m.023-8.25c-.076-.365-.183-.75-.35-1.125-.356-.81-1.021-1.476-1.946-1.875A6.757 6.757 0 0012 2.25c-1.357 0-2.573.461-3.478 1.125-.925.399-1.59 1.065-1.946 1.875a5.81 5.81 0 00-.35 1.125m12.023 0H3.75m16.5 0c.232 0 .459.03.672.085l.001.001c.622.18 1.077.726 1.077 1.394v.024l-.003.06c-.038.737-.203 1.446-.487 2.1-.326.753-.8 1.416-1.39 1.969-.345.324-.753.593-1.207.8m-13.416 0l-.003-.059c-.038-.737-.203-1.446-.487-2.1-.326-.753-.8-1.416-1.39-1.969a4.858 4.858 0 00-1.207-.8m16.5 0H3.75m0 0A2.25 2.25 0 001.5 9.75v.15c0 .406.11.79.298 1.12m1.952-1.27H18.75m-16.5 0A2.268 2.268 0 000 11.25v.15c0 1.087.616 2.031 1.518 2.502m.732-2.652v5.652c0 .667.292 1.267.753 1.675" />
              </svg>
            </button>
            {feedbackGiven !== null && (
              <span className="ml-2 text-[10px] text-zinc-500">
                Thanks for the feedback
              </span>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className={`mt-1 text-[10px] ${isUser ? "text-brand-300/50" : "text-zinc-600"}`}>
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}
