"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: Message[];
  onRate?: (messageId: string, rating: number) => void;
}

export function MessageList({ messages, onRate }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <div className="mb-4 text-5xl opacity-30">{"\uD83D\uDEE1\uFE0F"}</div>
          <h2 className="mb-2 text-lg font-semibold text-zinc-300">
            FraudAI Agent
          </h2>
          <p className="max-w-md text-sm text-zinc-500 leading-relaxed">
            Your AI-powered fraud prevention assistant. Ask about regulatory
            compliance, transaction analysis, risk assessment, or legal research.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {[
              "What are the AML obligations under Spanish law?",
              "Analyze suspicious transaction patterns",
              "Draft a SAR report for this case",
              "Check BOE regulations on PBC",
            ].map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="rounded-lg border border-zinc-700/50 bg-zinc-800/50 px-3 py-2 text-xs text-zinc-400 hover:bg-zinc-700/50 hover:text-zinc-300 transition-colors"
                aria-label={`Send: ${suggestion}`}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-4"
      role="log"
      aria-label="Chat messages"
      aria-live="polite"
    >
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} onRate={onRate} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
