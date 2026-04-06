import type {
  ChatRequest,
  ChatResponse,
  FileUploadResponse,
  SessionInfo,
  HealthResponse,
  FeedbackRequest,
} from "./types";

// ---------------------------------------------------------------------------
// Base configuration
// ---------------------------------------------------------------------------

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${API_BASE}${path}`;

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer dev-token",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, body);
  }

  // Handle 204 No Content
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export async function sendMessage(
  chatRequest: ChatRequest,
): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(chatRequest),
  });
}

// ---------------------------------------------------------------------------
// File Upload
// ---------------------------------------------------------------------------

export async function uploadFile(
  sessionId: string,
  file: File,
): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", sessionId);

  const url = `${API_BASE}/files/upload`;

  const res = await fetch(url, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type — browser sets multipart boundary automatically
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "Upload failed");
    throw new ApiError(res.status, body);
  }

  return res.json() as Promise<FileUploadResponse>;
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

export async function getSession(sessionId: string): Promise<SessionInfo> {
  return request<SessionInfo>(`/sessions/${sessionId}`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  return request<void>(`/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// HITL Confirmation
// ---------------------------------------------------------------------------

export async function confirmAction(
  sessionId: string,
  actionId: string,
  approved: boolean,
): Promise<ChatResponse> {
  return request<ChatResponse>("/confirm", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      action_id: actionId,
      approved,
    }),
  });
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export async function sendFeedback(
  sessionId: string,
  messageId: string,
  rating: number,
  comment?: string,
): Promise<void> {
  const body: FeedbackRequest = {
    session_id: sessionId,
    message_id: messageId,
    rating,
    ...(comment ? { comment } : {}),
  };

  return request<void>("/feedback", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function healthCheck(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export { ApiError };
