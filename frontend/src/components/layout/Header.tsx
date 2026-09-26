"use client";

import type { AgentName } from "@/lib/types";
import { AGENTS } from "@/lib/types";
import { Badge } from "@/components/ui/Badge";
import { getApiDocsUrl, loginUser } from "@/lib/api";
import { useState } from "react";

interface HeaderProps {
  sessionId: string | null;
  currentAgent: AgentName | null;
  selectedAgent: AgentName | null;
  onUploadClick?: () => void;
}

export function Header({
  sessionId,
  currentAgent,
  selectedAgent,
  onUploadClick,
}: HeaderProps) {
  const displayAgent = selectedAgent ?? currentAgent;
  const agentInfo = displayAgent ? AGENTS[displayAgent] : null;
  const docsUrl = getApiDocsUrl();
  const [authStatus, setAuthStatus] = useState<string>("Authorized");

  const handleQuickLogin = async () => {
    try {
      await loginUser("qa_analyst", "password123");
      setAuthStatus("Logged In (QA Analyst)");
      alert("Successfully authenticated as QA Analyst! JWT token refreshed.");
    } catch (err) {
      alert(`Login failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/80 px-4 py-2.5 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        {agentInfo ? (
          <Badge color={`${agentInfo.color} text-white`}>
            {agentInfo.icon} {agentInfo.displayName}
          </Badge>
        ) : (
          <span className="text-sm font-medium text-zinc-300">
            🤖 Auto-routing (Donna)
          </span>
        )}
        {selectedAgent && (
          <span className="text-[10px] text-zinc-500">
            (Agent override active)
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Upload file trigger */}
        <button
          type="button"
          onClick={() => {
            if (onUploadClick) {
              onUploadClick();
            } else {
              const fileInput = document.getElementById("file-upload") as HTMLInputElement;
              if (fileInput) fileInput.click();
              else alert("Click the paperclip icon (📎) next to the chat box to select your CSV, JSON, PDF or TXT report!");
            }
          }}
          className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-2.5 py-1 text-xs text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors"
          title="Upload CSV transaction spreadsheet, JSON, or PDF legal report"
        >

            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 04.5 4.5M12 3v13.5" />

          <span>Upload Report</span>
        </button>

        {/* API Docs link */}
        <a
          href={docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 rounded-lg border border-brand-500/40 bg-brand-500/10 px-2.5 py-1 text-xs font-medium text-brand-400 hover:bg-brand-500/20 transition-colors"
          title="Open live OpenAPI / Swagger UI documentation"
        >

            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18c-2.305 0-4.408.867-6 2.292m0-14.25v14.25" />

          <span>Swagger UI</span>
        </a>

        {/* Auth / Login button */}
        <button
          type="button"
          onClick={handleQuickLogin}
          className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800 px-2.5 py-1 text-xs text-zinc-300 hover:bg-zinc-700 hover:text-white transition-colors"
          title="Click to refresh OAuth2 / JWT session token"
        >

            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />

          <span>{authStatus}</span>
        </button>
      </div>
    </header>
  );
}

