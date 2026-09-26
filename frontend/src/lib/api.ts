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

const rawApiBase =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const API_BASE = rawApiBase.replace(/\/$/, "");

export function getApiDocsUrl(): string {
  const root = API_BASE.replace(/\/api\/v1$/, "").replace(/\/$/, "");
  return `${root}/docs`;
}

export function getAuthToken(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("fraudai_jwt_token");
    if (stored) return stored;
  }
  return "dev-token";
}

export async function loginUser(
  username = "qa_analyst",
  password = "password123",
): Promise<string> {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const res = await fetch(`${API_BASE}/auth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Login failed");
    throw new Error(`Login failed (${res.status}): ${text}`);
  }

  const data = (await res.json()) as { access_token: string };
  if (typeof window !== "undefined" && data.access_token) {
    localStorage.setItem("fraudai_jwt_token", data.access_token);
    localStorage.setItem("fraudai_username", username);
  }
  return data.access_token;
}

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
  const token = getAuthToken();

  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("fraudai_jwt_token");
    }
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
