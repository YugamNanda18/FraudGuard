"use client";

import { useState } from "react";
import { confirmAction } from "@/lib/api";

// ---------------------------------------------------------------------------
// HITL Confirmation Dialog — Mike Ross red-teaming actions (SEC-006)
// ---------------------------------------------------------------------------

interface ConfirmationDialogProps {
  sessionId: string;
  actionId: string;
  description: string;
  onConfirm: (approved: boolean) => void;
  onClose: () => void;
}

export default function ConfirmationDialog({
  sessionId,
  actionId,
  description,
  onConfirm,
  onClose,
}: ConfirmationDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAction(approved: boolean) {
    setIsSubmitting(true);
    setError(null);

    try {
      await confirmAction(sessionId, actionId, approved);
      onConfirm(approved);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to submit confirmation",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="hitl-dialog-title"
      aria-describedby="hitl-dialog-desc"
    >
      <div className="mx-4 w-full max-w-md rounded-xl border border-orange-500/40 bg-gray-900 p-6 shadow-2xl">
        {/* Warning header */}
        <div className="mb-4 flex items-start gap-3">
          <span
            className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-orange-500/20 text-xl"
            aria-hidden="true"
          >
            {/* Shield exclamation SVG */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="h-6 w-6 text-orange-400"
            >
              <path
                fillRule="evenodd"
                d="M11.484 2.17a.75.75 0 0 1 1.032 0 11.209 11.209 0 0 0 7.877 3.08.75.75 0 0 1 .722.515 12.74 12.74 0 0 1 .635 3.985c0 5.369-3.525 9.921-8.392 11.473a.75.75 0 0 1-.468 0C7.907 19.671 4.38 15.12 4.38 9.75c0-1.394.224-2.735.635-3.985a.75.75 0 0 1 .722-.516 11.21 11.21 0 0 0 7.877-3.08ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
                clipRule="evenodd"
              />
            </svg>
          </span>
          <div>
            <h2
              id="hitl-dialog-title"
              className="text-lg font-semibold text-orange-300"
            >
              Offensive Action Confirmation
            </h2>
            <p className="mt-1 text-xs text-orange-400/80">
              Mike Ross requires explicit approval before executing red-teaming
              tools.
            </p>
          </div>
        </div>

        {/* Action description */}
        <div
          id="hitl-dialog-desc"
          className="mb-5 rounded-lg border border-gray-700 bg-gray-800 p-4 text-sm leading-relaxed text-gray-300"
        >
          {description}
        </div>

        {/* Error banner */}
        {error && (
          <div
            className="mb-4 rounded-lg border border-red-500/40 bg-red-900/30 px-4 py-2 text-sm text-red-300"
            role="alert"
          >
            {error}
          </div>
        )}

        {/* Action ID badge */}
        <p className="mb-4 text-xs text-gray-500">
          Action ID:{" "}
          <code className="rounded bg-gray-800 px-1.5 py-0.5 font-mono text-gray-400">
            {actionId}
          </code>
        </p>

        {/* Buttons */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="rounded-lg px-4 py-2 text-sm font-medium text-gray-400 transition-colors hover:bg-gray-800 hover:text-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500 disabled:opacity-50"
            aria-label="Cancel and close dialog"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => handleAction(false)}
            disabled={isSubmitting}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 disabled:opacity-50"
            aria-label="Reject the proposed offensive action"
          >
            {isSubmitting ? "..." : "Reject"}
          </button>
          <button
            type="button"
            onClick={() => handleAction(true)}
            disabled={isSubmitting}
            className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-green-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-green-500 disabled:opacity-50"
            aria-label="Approve the proposed offensive action"
          >
            {isSubmitting ? "..." : "Approve"}
          </button>
        </div>
      </div>
    </div>
  );
}
