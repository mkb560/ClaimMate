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

export type PartyComparisonRow = {
  field_label: string;
  owner_value: string;
  other_party_value: string;
};

export type AccidentChatContext = {
  case_id: string;
  pinned_document_title: string;
  summary: string;
  key_facts: string[];
  party_comparison_rows: PartyComparisonRow[];
  follow_up_items: string[];
  generated_at: string;
};

export type AccidentReportPayload = {
  case_id: string;
  report_title: string;
  accident_summary: string;
  location_summary: string;
  detailed_narrative: string;
  damage_summary: string | null;
  police_report_number: string | null;
  timeline_entries: Array<{
    label: string;
    timestamp: string;
    note: string | null;
  }>;
  party_comparison_rows: PartyComparisonRow[];
  missing_items: string[];
};

export type GenerateReportResponse = {
  case_id: string;
  report_payload: AccidentReportPayload;
  chat_context: AccidentChatContext;
};

export type CaseSnapshotResponse = {
  case_id: string;
  claim_notice_at: string | null;
  proof_of_claim_at: string | null;
  last_deadline_alert_at: string | null;
  stage_a: Record<string, unknown>;
  stage_b: Record<string, unknown> | null;
  report_payload: AccidentReportPayload | null;
  chat_context: AccidentChatContext | null;
  created_at: string;
  updated_at: string;
};

export type ChatEventTrigger = "MESSAGE" | "PARTICIPANT_JOINED" | "POLICY_INDEXED";

export type ChatEventRequest = {
  sender_role: string;
  message_text: string;
  participants: Array<{ user_id: string; role: string }>;
  invite_sent: boolean;
  trigger: ChatEventTrigger;
  metadata?: Record<string, unknown>;
  occurred_at?: string | null;
};

export type AIResponsePayload = {
  text: string;
  citations: Citation[];
  trigger: string;
  metadata: Record<string, unknown>;
};

export type ChatEventResponse = {
  case_id: string;
  response: AIResponsePayload | null;
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

export async function getCaseSnapshot(caseId: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}`, {
    method: "GET",
    cache: "no-store",
    headers: {
      ...NGROK_HEADERS,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Load case snapshot failed");
  }

  return (await response.json()) as CaseSnapshotResponse;
}

export async function generateAccidentReport(caseId: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/report`, {
    method: "POST",
    headers: {
      ...NGROK_HEADERS,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Generate report failed");
  }

  return (await response.json()) as GenerateReportResponse;
}

export async function sendChatEvent(caseId: string, payload: ChatEventRequest) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/chat/event`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...NGROK_HEADERS,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Chat event failed");
  }

  return (await response.json()) as ChatEventResponse;
}
