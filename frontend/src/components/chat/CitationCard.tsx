"use client";

import { useState } from "react";
import type { Citation } from "@/lib/types";

// ---------------------------------------------------------------------------
// Citation Card — expandable BOE legal citation (Rachel Zane / RAG)
// ---------------------------------------------------------------------------

interface CitationCardProps {
  citation: Citation;
  /** Optional numeric index for numbered citation lists. */
  index?: number;
}

export function CitationCard({ citation }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const scorePercent = Math.round(citation.score * 100);

  return (
    <div
      className="overflow-hidden rounded-lg border border-amber-500/30 bg-amber-950/20"
      role="region"
      aria-label={`Legal citation: ${citation.norma_titulo}, ${citation.articulo}`}
    >
      {/* Collapsed header — always visible */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-amber-950/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        aria-expanded={expanded}
        aria-controls={`citation-${citation.boe_id}`}
      >
        {/* Scale/law icon */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4 shrink-0 text-amber-400"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M10 2a.75.75 0 0 1 .75.75v.258a33.186 33.186 0 0 1 6.668.83.75.75 0 0 1-.336 1.461 31.28 31.28 0 0 0-1.103-.232l1.702 7.545a.75.75 0 0 1-.387.832A4.981 4.981 0 0 1 15 14c-.825 0-1.606-.2-2.294-.556a.75.75 0 0 1-.387-.832l1.77-7.849a31.743 31.743 0 0 0-3.339-.254v11.505l5 .313a.75.75 0 0 1-.094 1.496l-5.812-.363a.75.75 0 0 1-.094 0l-5.812.363a.75.75 0 0 1-.094-1.496l5-.313V4.51a31.756 31.756 0 0 0-3.339.254l1.77 7.849a.75.75 0 0 1-.387.832A4.981 4.981 0 0 1 5 14c-.825 0-1.606-.2-2.294-.556a.75.75 0 0 1-.387-.832l1.702-7.545c-.37.07-.738.148-1.103.232a.75.75 0 0 1-.336-1.462 33.053 33.053 0 0 1 6.668-.829V2.75A.75.75 0 0 1 10 2ZM5 12.662l-1.395-6.185a31.582 31.582 0 0 0-1.12.232L3.88 12.662c.352.11.724.17 1.12.17s.768-.06 1.12-.17h-.12Zm10 0 1.395-5.953c-.37.07-.744.147-1.12.232L13.88 12.662c.352.11.724.17 1.12.17s.768-.06 1.12-.17h-.12Z"
            clipRule="evenodd"
          />
        </svg>

        {/* Title + article */}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-amber-200">
            {citation.norma_titulo}
          </p>
          <p className="text-xs text-amber-400/70">{citation.articulo}</p>
        </div>

        {/* BOE ID badge */}
        <span className="shrink-0 rounded bg-amber-500/20 px-2 py-0.5 font-mono text-xs text-amber-300">
          {citation.boe_id}
        </span>

        {/* Score badge */}
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${
            scorePercent >= 80
              ? "bg-green-500/20 text-green-300"
              : scorePercent >= 50
                ? "bg-yellow-500/20 text-yellow-300"
                : "bg-red-500/20 text-red-300"
          }`}
          title={`Relevance score: ${scorePercent}%`}
        >
          {scorePercent}%
        </span>

        {/* Chevron */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className={`h-4 w-4 shrink-0 text-amber-400/50 transition-transform duration-200 ${
            expanded ? "rotate-180" : ""
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

      {/* Expanded content */}
      {expanded && (
        <div
          id={`citation-${citation.boe_id}`}
          className="border-t border-amber-500/20 px-4 py-3"
        >
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-300">
            {citation.texto_relevante}
          </p>
        </div>
      )}
    </div>
  );
}
