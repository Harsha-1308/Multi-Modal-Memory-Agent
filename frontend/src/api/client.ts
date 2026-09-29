export interface Project {
  project_id: string;
  name: string;
  project_type: string;
  description: string;
  hindsight_bank_id: string;
  created_at: string;
  updated_at: string;
}

export interface Chat {
  chat_id: string;
  project_id: string;
  name: string;
  memory_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  message_id: string;
  chat_id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  message_type?: string;
  canonical_memory_id?: number | null;
  metadata?: any;
  created_at: string;
}

export interface EvidenceItem {
  evidence_id: string;
  project_id: string;
  chat_id: string;
  message_id?: string | null;
  kind: "image" | "document" | "text" | "code" | "file";
  original_filename: string;
  mime_type: string;
  storage_key: string;
  sha256: string;
  size_bytes: number;
  user_description?: string | null;
  semantic_description?: string | null;
  combined_understanding?: string | null;
  created_at: string;
}

export interface SendMessageResponse {
  message: {
    message_id: string;
    role: "assistant";
    content: string;
    created_at: string;
  };
  memory: {
    enabled: boolean;
    mode: string;
    status: string;
  };
  evidence: {
    source_evidence?: any[];
    learning_evidence?: Record<string, any>;
    learning_state?: Record<string, any> | null;
    understanding?: Record<string, any>;
    metrics?: Record<string, any>;
    [key: string]: any;
  };
  attachments?: EvidenceItem[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, options);

  if (!res.ok) {
    let errMessage = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.error?.message) {
        errMessage = data.error.message;
      } else if (typeof data?.detail === "string") {
        errMessage = data.detail;
      } else if (data?.detail?.message) {
        errMessage = data.detail.message;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errMessage);
  }

  return res.json();
}

export async function getProjects(): Promise<Project[]> {
  return request<Project[]>("/projects");
}

export async function createProject(data: {
  name: string;
  project_type: string;
  description?: string;
  seed_memories?: { text: string }[];
}): Promise<Project> {
  return request<Project>("/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getProject(projectId: string): Promise<Project> {
  return request<Project>(`/projects/${projectId}`);
}

export async function getChats(projectId: string): Promise<Chat[]> {
  return request<Chat[]>(`/projects/${projectId}/chats`);
}

export async function createChat(projectId: string, data: { name: string }): Promise<Chat> {
  return request<Chat>(`/projects/${projectId}/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getChat(chatId: string): Promise<Chat> {
  return request<Chat>(`/chats/${chatId}`);
}

export async function updateChatSettings(
  chatId: string,
  data: { memory_enabled: boolean }
): Promise<Chat> {
  return request<Chat>(`/chats/${chatId}/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getMessages(chatId: string): Promise<Message[]> {
  return request<Message[]>(`/chats/${chatId}/messages`);
}

export async function sendMessage(
  chatId: string,
  content: string,
  files?: File[],
  attachmentDescriptions?: { index: number; description: string }[]
): Promise<SendMessageResponse> {
  const formData = new FormData();
  formData.append("content", content);

  if (files && files.length > 0) {
    files.forEach((file) => {
      formData.append("files", file);
    });
  }

  if (attachmentDescriptions && attachmentDescriptions.length > 0) {
    formData.append("attachment_descriptions", JSON.stringify(attachmentDescriptions));
  }

  return request<SendMessageResponse>(`/chats/${chatId}/messages`, {
    method: "POST",
    body: formData,
  });
}

export async function uploadEvidence(
  chatId: string,
  file: File,
  description?: string
): Promise<EvidenceItem> {
  const formData = new FormData();
  formData.append("file", file);
  if (description) {
    formData.append("description", description);
  }

  return request<EvidenceItem>(`/chats/${chatId}/evidence`, {
    method: "POST",
    body: formData,
  });
}

export async function getEvidence(evidenceId: string): Promise<EvidenceItem> {
  return request<EvidenceItem>(`/evidence/${evidenceId}`);
}

export function getEvidenceContentUrl(evidenceId: string): string {
  return `${API_BASE}/evidence/${evidenceId}/content`;
}

export async function getProjectMemories(projectId: string): Promise<any[]> {
  return request<any[]>(`/projects/${projectId}/memories`);
}

export async function getProjectHistory(projectId: string): Promise<Message[]> {
  return request<Message[]>(`/projects/${projectId}/history`);
}
