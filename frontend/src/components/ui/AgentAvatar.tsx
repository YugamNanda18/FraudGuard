import type { AgentName } from "@/lib/types";
import { AGENTS } from "@/lib/types";

// ---------------------------------------------------------------------------
// Agent Avatar — colored circle with initial, per-agent theming
// ---------------------------------------------------------------------------

interface AgentAvatarProps {
  agent: AgentName;
  /** Tailwind size class. Defaults to "h-8 w-8". */
  size?: string;
  /** Show full name tooltip. Defaults to true. */
  showTooltip?: boolean;
}

/**
 * Maps each agent to an explicit Tailwind background class.
 * Using the custom agent-* colors defined in tailwind.config.ts.
 */
const AGENT_STYLES: Record<AgentName, { bg: string; initial: string }> = {
  donna:   { bg: "bg-agent-donna",   initial: "D" },
  harvey:  { bg: "bg-agent-harvey",   initial: "H" },
  louis:   { bg: "bg-agent-louis",   initial: "L" },
  jessica: { bg: "bg-agent-jessica", initial: "J" },
  mike:    { bg: "bg-agent-mike",    initial: "M" },
  rachel:  { bg: "bg-agent-rachel",  initial: "R" },
};

export default function AgentAvatar({
  agent,
  size = "h-8 w-8",
  showTooltip = true,
}: AgentAvatarProps) {
  const style = AGENT_STYLES[agent];
  const info = AGENTS[agent];

  return (
    <div
      className={`inline-flex shrink-0 items-center justify-center rounded-full ${style.bg} ${size} text-sm font-bold text-white select-none`}
      role="img"
      aria-label={info.displayName}
      title={showTooltip ? info.displayName : undefined}
    >
      {style.initial}
    </div>
  );
}
