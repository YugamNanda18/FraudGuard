"use client";

import { useState, useCallback, useEffect } from "react";
import type { SessionInfo, HealthResponse } from "@/lib/types";
import { getSession, deleteSession, healthCheck } from "@/lib/api";

// ---------------------------------------------------------------------------
// Session list (persisted in localStorage)
// ---------------------------------------------------------------------------

const STORAGE_KEY = "fraudai_sessions";

interface StoredSession {
  id: string;
  createdAt: string;
  turnCount: number;
}

function loadSessions(): StoredSession[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredSession[]) : [];
  } catch {
    return [];
  }
}

function saveSessions(sessions: StoredSession[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSession() {
  const [sessions, setSessions] = useState<StoredSession[]>([]);
  const [activeSession, setActiveSession] = useState<SessionInfo | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState(false);

  // Load stored sessions on mount
  useEffect(() => {
    setSessions(loadSessions());
  }, []);

  // -----------------------------------------------------------------------
  // Health check
  // -----------------------------------------------------------------------

  const [failCount, setFailCount] = useState(0);

  const checkHealth = useCallback(async () => {
    setIsLoadingHealth(true);
    try {
      const result = await healthCheck();
      setHealth(result);
      setFailCount(0);
    } catch {
      setFailCount((prev) => {
        const next = prev + 1;
        // First few failures during initial load / cold start: show waking_up
        setHealth({
          status: next < 5 ? "waking_up" : "unhealthy",
          qdrant: false,
          ollama: false,
          claude_api: false,
          corpus_version: null,
        });
        return next;
      });
    } finally {
      setIsLoadingHealth(false);
    }
  }, []);

  // Poll health: fast polling (4s) during waking_up/unhealthy, regular (30s) when healthy
  useEffect(() => {
    checkHealth();
    const intervalMs = health?.status === "healthy" ? 30_000 : 4_000;
    const interval = setInterval(checkHealth, intervalMs);
    return () => clearInterval(interval);
  }, [checkHealth, health?.status]);

  // -----------------------------------------------------------------------
  // Track session
  // -----------------------------------------------------------------------

  const trackSession = useCallback(
    (sessionId: string) => {
      setSessions((prev) => {
        const exists = prev.find((s) => s.id === sessionId);
        if (exists) return prev;

        const updated = [
          { id: sessionId, createdAt: new Date().toISOString(), turnCount: 0 },
          ...prev,
        ];
        saveSessions(updated);
        return updated;
      });
    },
    [],
  );

  // -----------------------------------------------------------------------
  // Load session info
  // -----------------------------------------------------------------------

  const loadSession = useCallback(async (sessionId: string) => {
    try {
      const info = await getSession(sessionId);
      setActiveSession(info);
      return info;
    } catch {
      return null;
    }
  }, []);

  // -----------------------------------------------------------------------
  // Delete session
  // -----------------------------------------------------------------------

  const removeSession = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
    } catch {
      // Session may already be gone — continue cleanup
    }

    setSessions((prev) => {
      const updated = prev.filter((s) => s.id !== sessionId);
      saveSessions(updated);
      return updated;
    });

    setActiveSession((prev) =>
      prev?.session_id === sessionId ? null : prev,
    );
  }, []);

  return {
    sessions,
    activeSession,
    health,
    isLoadingHealth,
    trackSession,
    loadSession,
    removeSession,
    checkHealth,
  };
}
