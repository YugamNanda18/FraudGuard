"use client";

import { useState, useRef, useCallback, type FormEvent, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/Button";

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileUpload: (file: File) => void;
  disabled?: boolean;
  isStreaming?: boolean;
  onCancel?: () => void;
}

const ACCEPTED_TYPES = ".csv,.json,.pdf,.txt";
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB

export function ChatInput({
  onSend,
  onFileUpload,
  disabled = false,
  isStreaming = false,
  onCancel,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(
    (e?: FormEvent) => {
      e?.preventDefault();
      const trimmed = input.trim();
      if (!trimmed || disabled) return;

      onSend(trimmed);
      setInput("");

      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    },
    [input, disabled, onSend],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.size > MAX_FILE_SIZE) {
        alert("File exceeds 100 MB limit.");
        return;
      }

      onFileUpload(file);

      // Reset input so same file can be uploaded again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [onFileUpload],
  );

  // Auto-resize textarea
  const handleTextareaChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setInput(e.target.value);
      const el = e.target;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
    },
    [],
  );

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-zinc-700/50 bg-zinc-900/80 px-4 py-3 backdrop-blur-sm"
    >
      <div className="mx-auto flex max-w-4xl items-end gap-2">
        {/* File upload */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          onChange={handleFileChange}
          className="hidden"
          id="file-upload"
          aria-label="Upload file"
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isStreaming}
          aria-label="Attach file"
          className="shrink-0"
        >
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"
            />
          </svg>
        </Button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleTextareaChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask about fraud prevention, compliance, regulations..."
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
          aria-label="Message input"
        />

        {/* Send / Cancel button */}
        {isStreaming ? (
          <Button
            type="button"
            variant="danger"
            size="md"
            onClick={onCancel}
            aria-label="Stop streaming"
            className="shrink-0"
          >
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </Button>
        ) : (
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={disabled || !input.trim()}
            aria-label="Send message"
            className="shrink-0"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
              />
            </svg>
          </Button>
        )}
      </div>
    </form>
  );
}
