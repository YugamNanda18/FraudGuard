"use client";

import type { AgentName } from "@/lib/types";
import { AGENTS } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";

interface AgentIndicatorProps {
  agent: AgentName | null;
  isStreaming: boolean;
}

export function AgentIndicator({ agent, isStreaming }: AgentIndicatorProps) {
  if (!agent || !isStreaming) return null;

  const info = AGENTS[agent];
  if (!info) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-sm text-zinc-400">
      <Spinner size="sm" className={info.textColor} />
      <Badge color={`${info.color} text-white`}>
        {info.icon} {info.displayName}
      </Badge>
      <span>is responding...</span>
    </div>
  );
}
