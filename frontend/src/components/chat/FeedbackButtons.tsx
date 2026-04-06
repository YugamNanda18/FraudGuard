"use client";

import { useState } from "react";

// ---------------------------------------------------------------------------
// Feedback Buttons — thumbs up / down per agent message (UR-014)
// ---------------------------------------------------------------------------

interface FeedbackButtonsProps {
  sessionId: string;
  messageId: string;
  onSubmit: (rating: number, comment?: string) => void;
}

type FeedbackState = "idle" | "input" | "submitted";

export default function FeedbackButtons({
  sessionId,
  messageId,
  onSubmit,
}: FeedbackButtonsProps) {
  const [state, setState] = useState<FeedbackState>("idle");
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState("");

  // Prevent unused-var lint — sessionId and messageId are passed through onSubmit
  void sessionId;
  void messageId;

  function handleThumb(value: number) {
    setRating(value);
    setState("input");
  }

  function handleSubmit() {
    if (rating === null) return;
    onSubmit(rating, comment.trim() || undefined);
    setState("submitted");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  // -- Submitted state ---------------------------------------------------
  if (state === "submitted") {
    return (
      <div className="flex items-center gap-1.5 text-xs text-gray-500">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          className="h-4 w-4 text-green-500"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
            clipRule="evenodd"
          />
        </svg>
        Feedback sent
      </div>
    );
  }

  // -- Comment input state -----------------------------------------------
  if (state === "input") {
    return (
      <div className="mt-2 flex flex-col gap-2">
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          {rating === 5 ? (
            <ThumbUpIcon className="h-3.5 w-3.5 text-green-400" />
          ) : (
            <ThumbDownIcon className="h-3.5 w-3.5 text-red-400" />
          )}
          <span>Add a comment (optional)</span>
        </div>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={2000}
          rows={2}
          placeholder="What could be improved?"
          className="w-full resize-none rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          aria-label="Optional feedback comment"
        />
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => setState("idle")}
            className="rounded px-3 py-1 text-xs text-gray-500 transition-colors hover:text-gray-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-500"
            aria-label="Cancel feedback"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            className="rounded bg-brand-600 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-brand-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label="Submit feedback"
          >
            Send
          </button>
        </div>
      </div>
    );
  }

  // -- Idle state — thumb buttons ----------------------------------------
  return (
    <div className="flex items-center gap-1" role="group" aria-label="Rate this response">
      <button
        type="button"
        onClick={() => handleThumb(5)}
        className="rounded p-1 text-gray-600 transition-colors hover:bg-gray-800 hover:text-green-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-green-500"
        aria-label="Thumbs up"
      >
        <ThumbUpIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={() => handleThumb(1)}
        className="rounded p-1 text-gray-600 transition-colors hover:bg-gray-800 hover:text-red-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
        aria-label="Thumbs down"
      >
        <ThumbDownIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline SVG icons — no external dependencies
// ---------------------------------------------------------------------------

function ThumbUpIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M1 8.25a1.25 1.25 0 1 1 2.5 0v7.5a1.25 1.25 0 1 1-2.5 0v-7.5ZM5.5 6v9.25a.75.75 0 0 0 .478.698l5.404 2.084a2.5 2.5 0 0 0 2.676-.543l2.893-2.893a1.25 1.25 0 0 0 0-1.768L13.5 9.375V4.25a2.25 2.25 0 0 0-4.154-1.207L5.5 6Z" />
    </svg>
  );
}

function ThumbDownIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M19 11.75a1.25 1.25 0 1 1-2.5 0v-7.5a1.25 1.25 0 1 1 2.5 0v7.5ZM14.5 14V4.75a.75.75 0 0 0-.478-.698L8.618 1.968a2.5 2.5 0 0 0-2.676.543L3.05 5.404a1.25 1.25 0 0 0 0 1.768L6.5 10.625v5.125a2.25 2.25 0 0 0 4.154 1.207L14.5 14Z" />
    </svg>
  );
}
