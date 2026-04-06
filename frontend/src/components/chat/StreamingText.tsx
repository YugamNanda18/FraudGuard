"use client";

interface StreamingTextProps {
  content: string;
  isStreaming: boolean;
}

export function StreamingText({ content, isStreaming }: StreamingTextProps) {
  return (
    <span className="whitespace-pre-wrap">
      {content}
      {isStreaming && (
        <span className="inline-flex items-center ml-1 gap-0.5" aria-label="Streaming">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-400 animate-pulse-dot" />
          <span
            className="h-1.5 w-1.5 rounded-full bg-brand-400 animate-pulse-dot"
            style={{ animationDelay: "0.16s" }}
          />
          <span
            className="h-1.5 w-1.5 rounded-full bg-brand-400 animate-pulse-dot"
            style={{ animationDelay: "0.32s" }}
          />
        </span>
      )}
    </span>
  );
}
