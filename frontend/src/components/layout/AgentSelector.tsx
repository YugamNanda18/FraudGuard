"use client";

import { useState } from "react";
import type { AgentName } from "@/lib/types";
import { AGENTS } from "@/lib/types";
import AgentAvatar from "@/components/ui/AgentAvatar";

// ---------------------------------------------------------------------------
// Agent Selector — sidebar panel for agent override (bypass Donna routing)
// ---------------------------------------------------------------------------

interface AgentSelectorProps {
  /** Currently selected override. null = Auto (Donna). */
  selectedAgent: AgentName | null;
  onSelect: (agent: AgentName | null) => void;
}

const SELECTABLE_AGENTS: AgentName[] = [
  "harvey",
  "louis",
  "jessica",
  "mike",
  "rachel",
];

export default function AgentSelector({
  selectedAgent,
  onSelect,
}: AgentSelectorProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/50">
      {/* Section header */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-gray-800/50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        aria-expanded={isExpanded}
        aria-controls="agent-selector-list"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          Agent Routing
        </span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 text-gray-600 transition-transform duration-200 ${
            isExpanded ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isExpanded && (
        <div
          id="agent-selector-list"
          className="px-2 pb-3"
          role="radiogroup"
          aria-label="Select agent for routing"
        >
          {/* Auto (Donna) — default option */}
          <AgentOption
            agent="donna"
            label="Auto (Donna)"
            description={AGENTS.donna.description}
            isSelected={selectedAgent === null}
            onSelect={() => onSelect(null)}
          />

          {/* Separator */}
          <div className="mx-2 my-1 border-t border-gray-800" />

          {/* Specialist agents */}
          {SELECTABLE_AGENTS.map((agentName) => (
            <AgentOption
              key={agentName}
              agent={agentName}
              label={AGENTS[agentName].displayName}
              description={AGENTS[agentName].description}
              isSelected={selectedAgent === agentName}
              onSelect={() => onSelect(agentName)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: single agent option
// ---------------------------------------------------------------------------

interface AgentOptionProps {
  agent: AgentName;
  label: string;
  description: string;
  isSelected: boolean;
  onSelect: () => void;
}

function AgentOption({
  agent,
  label,
  description,
  isSelected,
  onSelect,
}: AgentOptionProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={isSelected}
      onClick={onSelect}
      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
        isSelected
          ? "bg-gray-800 ring-1 ring-brand-500/50"
          : "hover:bg-gray-800/50"
      }`}
    >
      <AgentAvatar agent={agent} size="h-7 w-7" showTooltip={false} />
      <div className="min-w-0 flex-1">
        <p
          className={`truncate text-sm font-medium ${
            isSelected ? "text-white" : "text-gray-300"
          }`}
        >
          {label}
        </p>
        <p className="truncate text-xs text-gray-500">{description}</p>
      </div>
      {isSelected && (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4 shrink-0 text-brand-400"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
            clipRule="evenodd"
          />
        </svg>
      )}
    </button>
  );
}
