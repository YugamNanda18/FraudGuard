"use client";

import { useCallback, useEffect, useState } from "react";
import { healthCheck } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";

// ---------------------------------------------------------------------------
// Health Indicator — periodic system health dot with tooltip detail
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 30_000; // 30 seconds

const STATUS_STYLES: Record<
  HealthResponse["status"],
  { dot: string; text: string; label: string }
> = {
  healthy: {
    dot: "bg-green-400",
    text: "text-green-400",
    label: "All systems operational",
  },
  degraded: {
    dot: "bg-yellow-400",
    text: "text-yellow-400",
    label: "Degraded performance",
  },
  unhealthy: {
    dot: "bg-red-400",
    text: "text-red-400",
    label: "System unavailable",
  },
};

export default function HealthIndicator() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await healthCheck();
      setHealth(data);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  useEffect(() => {
    void fetchHealth();
    const interval = setInterval(() => void fetchHealth(), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // Before first response
  if (!health && !error) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-gray-500" />
        Connecting...
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-red-400">
        <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
        Offline
      </div>
    );
  }

  const status = health!.status;
  const style = STATUS_STYLES[status];

  return (
    <div
      className="relative inline-flex items-center gap-2"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
    >
      <button
        type="button"
        className={`flex items-center gap-2 rounded-md px-2 py-1 text-xs transition-colors hover:bg-gray-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${style.text}`}
        aria-label={`System status: ${style.label}`}
        aria-describedby="health-tooltip"
      >
        <span
          className={`inline-block h-2 w-2 rounded-full ${style.dot}`}
          aria-hidden="true"
        />
        {style.label}
      </button>

      {/* Tooltip with detailed status */}
      {showTooltip && health && (
        <div
          id="health-tooltip"
          role="tooltip"
          className="absolute bottom-full left-0 z-50 mb-2 w-56 rounded-lg border border-gray-700 bg-gray-900 p-3 shadow-xl"
        >
          <p className="mb-2 text-xs font-semibold text-gray-300">
            Infrastructure Status
          </p>
          <ul className="space-y-1.5">
            <ServiceRow label="Qdrant" ok={health.qdrant} />
            <ServiceRow label="Ollama (Donna)" ok={health.ollama} />
            <ServiceRow label="Claude API" ok={health.claude_api} />
          </ul>
          {health.corpus_version && (
            <p className="mt-2 border-t border-gray-800 pt-2 text-xs text-gray-500">
              Corpus: {health.corpus_version}
            </p>
          )}
          {/* Tooltip arrow */}
          <div className="absolute -bottom-1.5 left-4 h-3 w-3 rotate-45 border-b border-r border-gray-700 bg-gray-900" />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-component: single service row
// ---------------------------------------------------------------------------

function ServiceRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <li className="flex items-center justify-between text-xs">
      <span className="text-gray-400">{label}</span>
      <span
        className={`flex items-center gap-1 font-medium ${
          ok ? "text-green-400" : "text-red-400"
        }`}
      >
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            ok ? "bg-green-400" : "bg-red-400"
          }`}
          aria-hidden="true"
        />
        {ok ? "OK" : "Down"}
      </span>
    </li>
  );
}
