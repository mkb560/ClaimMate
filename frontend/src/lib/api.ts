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

export type DemoPolicy = {
  policy_key: string;
  default_case_id: string;
  label: string;
  filename: string;
  sample_questions: string[];
};

export type DemoPolicyCatalogResponse = {
  policies: DemoPolicy[];
};

export type SeedDemoPolicyResponse = {
  case_id: string;
  policy_key: string;
  default_case_id: string;
  label: string;
  filename: string;
  chunk_count: number;
  status: string;
  sample_questions: string[];
};

export type CasePolicyStatusResponse = {
  case_id: string;
  has_policy: boolean;
  chunk_count: number;
  source_label: string | null;
  filename: string | null;
  demo_policy?: DemoPolicy | null;
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

export type SeedAccidentDemoResponse = {
  case_id: string;
  kb_b_status: string;
  stage_a: Record<string, unknown>;
  stage_b: Record<string, unknown>;
  claim_dates: {
    claim_notice_at: string | null;
    proof_of_claim_at: string | null;
  };
  report_payload: AccidentReportPayload;
  chat_context: AccidentChatContext;
  sample_chat_requests: Record<string, unknown>;
  sample_chat_responses: Record<string, AIResponsePayload | null>;
  sample_chat_errors: Record<string, string>;
  case_snapshot: CaseSnapshotResponse | null;
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

export async function getDemoPolicies() {
  const response = await fetch(`${API_BASE_URL}/demo/policies`, {
    method: "GET",
    cache: "no-store",
    headers: {
      ...NGROK_HEADERS,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Load demo policies failed");
  }

  return (await response.json()) as DemoPolicyCatalogResponse;
}

export async function getCasePolicyStatus(caseId: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/policy`, {
    method: "GET",
    cache: "no-store",
    headers: {
      ...NGROK_HEADERS,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Load case policy status failed");
  }

  return (await response.json()) as CasePolicyStatusResponse;
}

export async function seedDemoPolicy(caseId: string, policyKey?: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/demo/seed-policy`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...NGROK_HEADERS,
    },
    body: JSON.stringify(policyKey ? { policy_key: policyKey } : {}),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Seed demo policy failed");
  }

  return (await response.json()) as SeedDemoPolicyResponse;
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

export async function seedAccidentDemoCase(caseId: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/demo/seed-accident`, {
    method: "POST",
    headers: {
      ...NGROK_HEADERS,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Seed accident demo failed");
  }

  return (await response.json()) as SeedAccidentDemoResponse;
}
