"use client";

import { useState } from "react";
import type { AgentName, HealthResponse } from "@/lib/types";
import { AGENTS } from "@/lib/types";
import { Button } from "@/components/ui/Button";

interface StoredSession {
  id: string;
  createdAt: string;
  turnCount: number;
}

interface SidebarProps {
  sessions: StoredSession[];
  health: HealthResponse | null;
  currentSessionId: string | null;
  selectedAgent: AgentName | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onSelectAgent: (agent: AgentName | null) => void;
}

const agentList = Object.values(AGENTS);

export function Sidebar({
  sessions,
  health,
  currentSessionId,
  selectedAgent,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onSelectAgent,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (collapsed) {
    return (
      <aside className="flex w-14 flex-col items-center border-r border-zinc-800 bg-zinc-950 py-4">
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
          aria-label="Expand sidebar"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
          </svg>
        </button>

        {/* Health dot */}
        <div className="mt-auto mb-2">
          <div
            className={`h-2.5 w-2.5 rounded-full ${
              health?.status === "healthy"
                ? "bg-green-500"
                : health?.status === "degraded"
                  ? "bg-yellow-500"
                  : "bg-red-500"
            }`}
            title={health?.status ?? "unknown"}
          />
        </div>
      </aside>
    );
  }

  return (
    <aside className="flex w-72 flex-col border-r border-zinc-800 bg-zinc-950">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">{"\uD83D\uDEE1\uFE0F"}</span>
          <h1 className="text-sm font-bold text-zinc-100 tracking-tight">
            FraudAI Agent
          </h1>
        </div>
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 transition-colors"
          aria-label="Collapse sidebar"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* New chat button */}
      <div className="px-3 py-3">
        <Button
          variant="primary"
          size="md"
          className="w-full"
          onClick={onNewChat}
        >
          <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          New Chat
        </Button>
      </div>

      {/* Agent selector */}
      <div className="px-3 pb-2">
        <p className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
          Agents
        </p>
        <div className="flex flex-col gap-1">
          {agentList.map((agent) => (
            <button
              key={agent.name}
              type="button"
              onClick={() =>
                onSelectAgent(
                  selectedAgent === agent.name ? null : agent.name,
                )
              }
              className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs transition-colors ${
                selectedAgent === agent.name
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-300"
              }`}
              aria-pressed={selectedAgent === agent.name}
              aria-label={`Select agent ${agent.displayName}: ${agent.description}`}
            >
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${agent.color} text-white`}
              >
                {agent.icon}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium">{agent.displayName}</p>
                <p className="truncate text-[10px] text-zinc-500">
                  {agent.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {sessions.length > 0 && (
          <>
            <p className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
              Sessions
            </p>
            <div className="flex flex-col gap-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`group flex items-center gap-2 rounded-lg px-2.5 py-2 text-xs transition-colors ${
                    currentSessionId === session.id
                      ? "bg-zinc-800 text-zinc-100"
                      : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-300"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelectSession(session.id)}
                    className="min-w-0 flex-1 text-left"
                    aria-label={`Load session ${session.id}`}
                  >
                    <p className="truncate font-mono text-[10px]">
                      {session.id.slice(0, 12)}...
                    </p>
                    <p className="text-[10px] text-zinc-600">
                      {new Date(session.createdAt).toLocaleDateString()}
                    </p>
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteSession(session.id)}
                    className="invisible rounded p-1 text-zinc-600 hover:text-red-400 group-hover:visible transition-colors"
                    aria-label={`Delete session ${session.id}`}
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Health status */}
      <div className="border-t border-zinc-800 px-4 py-3">
        <div className="flex items-center gap-2 text-xs">
          <div
            className={`h-2 w-2 rounded-full ${
              health?.status === "healthy"
                ? "bg-green-500"
                : health?.status === "degraded"
                  ? "bg-yellow-500"
                  : "bg-red-500"
            }`}
          />
          <span className="text-zinc-500">
            {health?.status === "healthy"
              ? "All systems operational"
              : health?.status === "degraded"
                ? "Degraded performance"
                : "System unavailable"}
          </span>
        </div>
        {health?.corpus_version && (
          <p className="mt-1 text-[10px] text-zinc-600">
            Corpus: {health.corpus_version}
          </p>
        )}
      </div>
    </aside>
  );
}
