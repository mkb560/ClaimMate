import Constants from 'expo-constants';
import { getToken } from '@/auth/tokenStore';

const DEFAULT_API_BASE_URL = 'https://claimmate-backend-production.up.railway.app';

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
  DEFAULT_API_BASE_URL;

export type MobileUploadFile = {
  uri: string;
  name: string;
  type: string;
};

async function getAuthHeaders(extra?: Record<string, string>): Promise<Record<string, string>> {
  const token = await getToken();
  return {
    'ngrok-skip-browser-warning': 'true',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function readJsonError(response: Response, fallback: string): Promise<Error> {
  const error = await response.json().catch(() => null);
  const detail = error?.detail;
  if (Array.isArray(detail)) return new Error(detail.map((item) => item.msg).join(', ') || fallback);
  return new Error(typeof detail === 'string' ? detail : fallback);
}

export type Citation = {
  source_type: 'kb_a' | 'kb_b';
  source_label: string;
  document_id: string;
  page_num: number | null;
  section: string | null;
  excerpt: string;
};

export type DemoPolicy = {
  policy_key: string;
  default_case_id: string;
  label: string;
  filename: string;
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
  vehicle: {
    license_plate: string | null;
    vin: string | null;
  } | null;
};

export type PhotoAttachment = {
  photo_id: string;
  category: string;
  storage_key: string;
  caption: string | null;
  taken_at: string | null;
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
  timeline_entries: { label: string; timestamp: string; note: string | null }[];
  party_comparison_rows: PartyComparisonRow[];
  missing_items: string[];
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

export type AIResponsePayload = {
  text: string;
  citations: Citation[];
  trigger: string;
  metadata: Record<string, unknown>;
};

export type ChatMessageRow = {
  id: string;
  case_id: string;
  message_type: 'user' | 'ai';
  sender_role: string | null;
  sender_display_name: string | null;
  body_text: string;
  ai_payload: AIResponsePayload | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export type UserCaseEntry = {
  case_id: string;
  role: string;
  created_at: string;
};

export type CaseMemberEntry = {
  user_id: string;
  role: string;
};

export type AuthUser = {
  user_id: string;
  email: string;
  display_name: string | null;
  created_at?: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type UploadIncidentPhotoResponse = {
  case_id: string;
  photo_attachment: PhotoAttachment;
  stage_a: Record<string, unknown>;
};

export async function checkHealth(): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Backend health check failed');
  return response.json();
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw await readJsonError(response, 'Login failed');
  return response.json();
}

export async function registerUser(
  email: string,
  password: string,
  display_name?: string
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ email, password, display_name }),
  });
  if (!response.ok) throw await readJsonError(response, 'Registration failed');
  return response.json();
}

export async function getMe(): Promise<AuthUser> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Not authenticated');
  return response.json();
}

export async function getUserCases(): Promise<UserCaseEntry[]> {
  const response = await fetch(`${API_BASE_URL}/cases`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Failed to load cases');
  const data = (await response.json()) as { cases: UserCaseEntry[] };
  return data.cases;
}

export async function createCase(caseId?: string): Promise<{ case_id: string }> {
  const response = await fetch(`${API_BASE_URL}/cases`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(caseId ? { case_id: caseId } : {}),
  });
  if (!response.ok) throw await readJsonError(response, 'Create case failed');
  return response.json();
}

export async function deleteCase(caseId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}`, {
    method: 'DELETE',
    headers: await getAuthHeaders(),
  });
  if (!response.ok && response.status !== 404) {
    throw await readJsonError(response, 'Delete case failed');
  }
}

export async function getCaseSnapshot(caseId: string): Promise<CaseSnapshotResponse> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Load case snapshot failed');
  return response.json();
}

export async function getCaseMembers(caseId: string): Promise<CaseMemberEntry[]> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/members`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Failed to load case members');
  const data = (await response.json()) as { members: CaseMemberEntry[] };
  return data.members;
}

export async function patchAccidentStageA(
  caseId: string,
  payload: Record<string, unknown>
): Promise<{ case_id: string; stage_a: Record<string, unknown> }> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/stage-a`, {
    method: 'PATCH',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await readJsonError(response, 'Save Accident Basics failed');
  return response.json();
}

export async function patchAccidentStageB(
  caseId: string,
  payload: Record<string, unknown>
): Promise<{ case_id: string; stage_b: Record<string, unknown> }> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/stage-b`, {
    method: 'PATCH',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await readJsonError(response, 'Save Accident Details failed');
  return response.json();
}

export async function getDemoPolicies(): Promise<{ policies: DemoPolicy[] }> {
  const response = await fetch(`${API_BASE_URL}/demo/policies`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Load existing policies failed');
  return response.json();
}

export async function getCasePolicyStatus(caseId: string): Promise<CasePolicyStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/policy`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Load policy status failed');
  return response.json();
}

export async function seedDemoPolicy(caseId: string, policyKey?: string) {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/demo/seed-policy`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(policyKey ? { policy_key: policyKey } : {}),
  });
  if (!response.ok) throw await readJsonError(response, 'Load existing policy failed');
  return response.json();
}

export async function uploadPolicy(caseId: string, file: MobileUploadFile) {
  const formData = new FormData();
  formData.append('file', file as unknown as Blob);
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/policy`, {
    method: 'POST',
    headers: await getAuthHeaders(),
    body: formData,
  });
  if (!response.ok) throw await readJsonError(response, 'Upload policy failed');
  return response.json();
}

export async function askPolicyQuestion(caseId: string, question: string): Promise<AskResponse> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/ask`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw await readJsonError(response, 'Ask request failed');
  return response.json();
}

export async function uploadIncidentPhoto(
  caseId: string,
  file: MobileUploadFile,
  category: string
): Promise<UploadIncidentPhotoResponse> {
  const formData = new FormData();
  formData.append('file', file as unknown as Blob);
  formData.append('category', category);
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/incident-photos`, {
    method: 'POST',
    headers: await getAuthHeaders(),
    body: formData,
  });
  if (!response.ok) throw await readJsonError(response, 'Upload photo failed');
  return response.json();
}

export async function generateAccidentReport(caseId: string): Promise<GenerateReportResponse> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/report`, {
    method: 'POST',
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Generate report failed');
  return response.json();
}

export async function getAccidentReport(caseId: string): Promise<GenerateReportResponse> {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/accident/report`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Load report failed');
  return response.json();
}

export async function getChatMessages(caseId: string, limit = 100, offset = 0) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/chat/messages?${params}`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Load chat messages failed');
  return response.json() as Promise<{ case_id: string; messages: ChatMessageRow[] }>;
}

export async function createInvite(caseId: string, role = 'adjuster') {
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/invites`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ role }),
  });
  if (!response.ok) throw await readJsonError(response, 'Create invite failed');
  return response.json() as Promise<{
    case_id: string;
    token: string;
    invite_id: string;
    role: string;
    expires_at: string;
  }>;
}

export async function lookupInvite(token: string) {
  const response = await fetch(`${API_BASE_URL}/invites/lookup?token=${encodeURIComponent(token)}`, {
    headers: await getAuthHeaders(),
  });
  if (!response.ok) throw await readJsonError(response, 'Invite not found');
  return response.json() as Promise<{ case_id: string; role: string; expires_at: string }>;
}

export async function acceptInvite(token: string) {
  const response = await fetch(`${API_BASE_URL}/auth/accept-invite`, {
    method: 'POST',
    headers: await getAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ token }),
  });
  if (!response.ok) throw await readJsonError(response, 'Accept invite failed');
  return response.json() as Promise<{ case_id: string; accepted: boolean }>;
}
