"use client";

import { useCallback, useRef, useState } from "react";
import { uploadFile } from "@/lib/api";
import type { FileUploadResponse } from "@/lib/types";

// ---------------------------------------------------------------------------
// File Upload Zone — drag & drop + click to browse (SR-008, UR-012)
// ---------------------------------------------------------------------------

interface FileUploadZoneProps {
  sessionId: string;
  onUploadComplete: (response: FileUploadResponse) => void;
  onError: (error: string) => void;
}

const ACCEPTED_TYPES = [
  "text/csv",
  "application/json",
  "application/pdf",
  "text/plain",
];
const ACCEPTED_EXTENSIONS = [".csv", ".json", ".pdf", ".txt"];
const MAX_SIZE_BYTES = 100 * 1024 * 1024; // 100 MB

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export default function FileUploadZone({
  sessionId,
  onUploadComplete,
  onError,
}: FileUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<FileUploadResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function validateFile(file: File): string | null {
    const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
    if (
      !ACCEPTED_TYPES.includes(file.type) &&
      !ACCEPTED_EXTENSIONS.includes(ext)
    ) {
      return `Unsupported file type: ${ext}. Accepted: ${ACCEPTED_EXTENSIONS.join(", ")}`;
    }
    if (file.size > MAX_SIZE_BYTES) {
      return `File too large (${formatBytes(file.size)}). Max: 100 MB`;
    }
    return null;
  }

  const handleFile = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        onError(validationError);
        return;
      }

      setIsUploading(true);
      setProgress(0);
      setResult(null);

      // Simulate progress (real XHR progress would need XMLHttpRequest)
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      try {
        const response = await uploadFile(sessionId, file);
        clearInterval(progressInterval);
        setProgress(100);
        setResult(response);
        onUploadComplete(response);
      } catch (err) {
        clearInterval(progressInterval);
        setProgress(0);
        onError(
          err instanceof Error ? err.message : "Upload failed",
        );
      } finally {
        setIsUploading(false);
      }
    },
    [sessionId, onUploadComplete, onError],
  );

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) void handleFile(file);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragOver(false);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void handleFile(file);
    // Reset input so the same file can be re-selected
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      inputRef.current?.click();
    }
  }

  // -- Result display ----------------------------------------------------
  if (result) {
    return (
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/20">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5 text-green-400"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-gray-200">
              {result.filename}
            </p>
            <p className="text-xs text-gray-500">
              {formatBytes(result.size_bytes)} &middot;{" "}
              {result.chunks_generated} chunks
            </p>
          </div>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              result.indexed
                ? "bg-green-500/20 text-green-300"
                : "bg-yellow-500/20 text-yellow-300"
            }`}
          >
            {result.indexed ? "Indexed" : "Pending"}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setResult(null)}
          className="mt-3 text-xs text-gray-500 transition-colors hover:text-gray-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          aria-label="Upload another file"
        >
          Upload another file
        </button>
      </div>
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => inputRef.current?.click()}
      onKeyDown={handleKeyDown}
      aria-label="Upload a file. Drag and drop or click to browse."
      className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-6 transition-colors ${
        isDragOver
          ? "border-brand-500 bg-brand-500/10"
          : "border-gray-700 bg-gray-800/30 hover:border-gray-600 hover:bg-gray-800/50"
      } ${isUploading ? "pointer-events-none" : "cursor-pointer"}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        onChange={handleInputChange}
        className="hidden"
        aria-hidden="true"
      />

      {/* Upload icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        className={`mb-3 h-8 w-8 ${isDragOver ? "text-brand-400" : "text-gray-500"}`}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
        />
      </svg>

      {isUploading ? (
        <div className="w-full max-w-xs">
          <p className="mb-2 text-center text-sm text-gray-400">
            Uploading...
          </p>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-700">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Upload progress: ${progress}%`}
            />
          </div>
        </div>
      ) : (
        <>
          <p className="text-sm font-medium text-gray-300">
            {isDragOver ? "Drop file here" : "Drag & drop or click to upload"}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            CSV, JSON, PDF, TXT &middot; Max 100 MB
          </p>
        </>
      )}
    </div>
  );
}
