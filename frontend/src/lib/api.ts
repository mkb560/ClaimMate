import { getToken } from './auth'

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'https://claimmate-backend-production.up.railway.app'

function getAuthHeaders(): Record<string, string> {
  const token = getToken()
  return {
    'ngrok-skip-browser-warning': 'true',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

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
  prefill?: {
    policyholders: string | null;
    insurer: string | null;
    policy_number: string | null;
  };
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

export type PartyRecord = {
  role: string;
  name: string;
  phone: string | null;
  email: string | null;
  insurer: string | null;
  policy_number: string | null;
  claim_number: string | null;
};

export type PhotoAttachment = {
  photo_id: string;
  category: string;
  storage_key: string;
  caption: string | null;
  taken_at: string | null;
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
  generated_at: string;
  accident_summary: string;
  occurrence_time: string | null;
  location_summary: string | null;
  owner_party: PartyRecord | null;
  other_party: PartyRecord | null;
  detailed_narrative: string;
  damage_summary: string | null;
  injuries_reported: boolean | null;
  police_called: boolean | null;
  drivable: boolean | null;
  tow_requested: boolean | null;
  weather_conditions: string | null;
  road_conditions: string | null;
  police_report_number: string | null;
  adjuster_name: string | null;
  repair_shop_name: string | null;
  photo_attachments: PhotoAttachment[];
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

export type PatchStageAResponse = {
  case_id: string;
  stage_a: Record<string, unknown>;
};

export type PatchStageBResponse = {
  case_id: string;
  stage_b: Record<string, unknown>;
};

export async function patchAccidentStageB(
  caseId: string,
  payload: Record<string, unknown>
) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/stage-b`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Save Stage B failed");
  }

  return (await response.json()) as PatchStageBResponse;
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    cache: "no-store",
    headers: {
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Load case snapshot failed");
  }

  return (await response.json()) as CaseSnapshotResponse;
}

export async function patchAccidentStageA(
  caseId: string,
  payload: Record<string, unknown>
) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/stage-a`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Save Stage A failed");
  }

  return (await response.json()) as PatchStageAResponse;
}

export async function generateAccidentReport(caseId: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/report`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
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
      ...getAuthHeaders(),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Chat event failed");
  }

  return (await response.json()) as ChatEventResponse;
}

export type ChatMessageRow = {
  id: string;
  case_id: string;
  message_type: "user" | "ai";
  sender_role: string | null;
  sender_display_name: string | null;
  body_text: string;
  ai_payload: AIResponsePayload | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export type ChatMessagesResponse = {
  case_id: string;
  messages: ChatMessageRow[];
  limit: number;
  offset: number;
};

export type PostChatMessageResponse = {
  case_id: string;
  response: AIResponsePayload | null;
};

export async function getChatMessages(
  caseId: string,
  limit = 100,
  offset = 0
) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/chat/messages?${params}`,
    {
      method: "GET",
      cache: "no-store",
      headers: { ...getAuthHeaders() },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Load chat messages failed");
  }

  return (await response.json()) as ChatMessagesResponse;
}

export async function sendChatMessage(
  caseId: string,
  messageText: string,
  options?: {
    sender_role?: string;
    invite_sent?: boolean;
    participants?: Array<{ user_id: string; role: string }>;
  }
) {
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/chat/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        message_text: messageText,
        sender_role: options?.sender_role ?? "owner",
        invite_sent: options?.invite_sent ?? false,
        participants: options?.participants ?? null,
      }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Send chat message failed");
  }

  return (await response.json()) as PostChatMessageResponse;
}

export type UserCaseEntry = {
  case_id: string
  role: string
  created_at: string
}

export type CaseMemberEntry = {
  user_id: string
  role: string
}

export type IncidentPhotoAttachment = {
  photo_id: string
  category: string
  storage_key: string
  caption: string | null
  taken_at: string | null
}

export type UploadIncidentPhotoResponse = {
  case_id: string
  photo_attachment: IncidentPhotoAttachment
  stage_a: Record<string, unknown>
}

export async function uploadIncidentPhoto(
  caseId: string,
  file: File,
  category: string
): Promise<UploadIncidentPhotoResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', category)
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/incident-photos`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
    body: formData,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Upload failed')
  }
  return response.json() as Promise<UploadIncidentPhotoResponse>
}

export async function fetchIncidentPhotoBlobUrl(caseId: string, photoId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/incident-photos/${photoId}`, {
    headers: { ...getAuthHeaders() },
    cache: 'no-store',
  })
  if (!response.ok) throw new Error('Photo fetch failed')
  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

export async function getUserCases(): Promise<UserCaseEntry[]> {
  const response = await fetch(`${API_BASE_URL}/cases`, {
    method: 'GET',
    cache: 'no-store',
    headers: { ...getAuthHeaders() },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Failed to load cases')
  }
  const data = await response.json() as { cases: UserCaseEntry[] }
  return data.cases
}

export async function getCaseMembers(caseId: string): Promise<CaseMemberEntry[]> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/members`, {
    method: 'GET',
    cache: 'no-store',
    headers: { ...getAuthHeaders() },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Failed to load case members')
  }
  const data = await response.json() as { members: CaseMemberEntry[] }
  return data.members
}

export async function createCase(caseId?: string) {
  const response = await fetch(`${API_BASE_URL}/cases`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(caseId ? { case_id: caseId } : {}),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Create case failed");
  }

  return (await response.json()) as { case_id: string };
}

export async function deleteCase(caseId: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}`, {
    method: "DELETE",
    headers: { ...getAuthHeaders() },
  });

  if (!response.ok && response.status !== 404) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Delete case failed");
  }
}

export async function patchClaimDates(
  caseId: string,
  dates: { claim_notice_at?: string | null; proof_of_claim_at?: string | null }
) {
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/claim-dates`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(dates),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Update claim dates failed");
  }

  return response.json();
}

export async function getAccidentReport(caseId: string) {
  const response = await fetch(
    `${API_BASE_URL}/cases/${caseId}/accident/report`,
    {
      method: "GET",
      cache: "no-store",
      headers: { ...getAuthHeaders() },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Load accident report failed");
  }

  return (await response.json()) as GenerateReportResponse;
}

export async function seedAccidentDemoCase(caseId: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/demo/seed-accident`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(error?.detail || "Seed accident demo failed");
  }

  return (await response.json()) as SeedAccidentDemoResponse;
}

export type AuthUser = {
  user_id: string
  email: string
  display_name: string | null
  created_at?: string
}

export type AuthResponse = {
  access_token: string
  token_type: string
  user: AuthUser
}

export async function loginUser(
  email: string,
  password: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ email, password }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Login failed')
  }
  return response.json() as Promise<AuthResponse>
}

export async function registerUser(
  email: string,
  password: string,
  display_name?: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ email, password, display_name }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Registration failed')
  }
  return response.json() as Promise<AuthResponse>
}

export async function getMe(): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: getAuthHeaders(),
    cache: 'no-store',
  })
  if (!response.ok) throw new Error('Not authenticated')
  return response.json() as Promise<AuthUser>
}

export type CreateInviteResponse = {
  case_id: string
  token: string
  invite_id: string
  role: string
  expires_at: string
}

export type InviteLookupResponse = {
  case_id: string
  role: string
  expires_at: string
}

export async function createInvite(caseId: string, role = 'member'): Promise<CreateInviteResponse> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/invites`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ role }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Create invite failed')
  }
  return response.json() as Promise<CreateInviteResponse>
}

export async function lookupInvite(token: string): Promise<InviteLookupResponse> {
  const response = await fetch(
    `${API_BASE_URL}/invites/lookup?token=${encodeURIComponent(token)}`,
    { headers: { ...getAuthHeaders() }, cache: 'no-store' }
  )
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Invite not found')
  }
  return response.json() as Promise<InviteLookupResponse>
}

export async function acceptInvite(token: string): Promise<{ case_id: string; accepted: boolean }> {
  const response = await fetch(`${API_BASE_URL}/auth/accept-invite`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify({ token }),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail || 'Accept invite failed')
  }
  return response.json() as Promise<{ case_id: string; accepted: boolean }>
}
