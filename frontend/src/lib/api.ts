const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

console.log("API_BASE_URL =", JSON.stringify(API_BASE_URL));

const NGROK_HEADERS = {
  "ngrok-skip-browser-warning": "true",
};

export type UploadPolicyResponse = {
  case_id: string;
  filename: string;
  chunk_count: number;
  status: string;
};

export type Citation = {
  source_type: "kb_a" | "kb_b";
  source_label: string;
  document_id: string;
  page_num: number | null;
  section: string | null;
  excerpt: string;
};

export type AskResponse = {
  case_id: string;
  question: string;
  answer: string;
  disclaimer: string;
  citations: Citation[];
};

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    cache: "no-store",
    headers: {
      ...NGROK_HEADERS,
    },
  });

  if (!response.ok) {
    throw new Error("Backend health check failed");
  }

  return response.json();
}

export async function uploadPolicy(caseId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/policy`, {
    method: "POST",
    body: formData,
    headers: {
      ...NGROK_HEADERS,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Upload failed");
  }

  return (await response.json()) as UploadPolicyResponse;
}

export async function askPolicyQuestion(caseId: string, question: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...NGROK_HEADERS,
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Ask request failed");
  }

  return (await response.json()) as AskResponse;
}