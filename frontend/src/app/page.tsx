"use client";

import { useEffect, useMemo, useState } from "react";
import {
  askPolicyQuestion,
  CaseSnapshotResponse,
  checkHealth,
  Citation,
  ChatEventResponse,
  generateAccidentReport,
  getCaseSnapshot,
  UploadPolicyResponse,
  AskResponse,
  AccidentReportPayload,
  AccidentChatContext,
  sendChatEvent,
  seedAccidentDemoCase,
  uploadPolicy,
  getDemoPolicies,
  getCasePolicyStatus,
  seedDemoPolicy,
  DemoPolicy,
  CasePolicyStatusResponse,
  SeedDemoPolicyResponse,
  patchAccidentStageA,
  patchAccidentStageB,
} from "@/lib/api";

function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;

  return (
    <div className="mt-6 space-y-3">
      <h2 className="text-lg font-semibold">Sources</h2>
      {citations.map((citation, index) => (
        <div
          key={`${citation.document_id}-${index}`}
          className="rounded-xl border p-4"
        >
          <div className="font-medium">{citation.source_label}</div>
          <div className="mt-1 text-sm text-gray-600">
            {citation.source_type === "kb_a" ? "Your Policy" : "Regulation"}
            {citation.page_num ? ` | Page ${citation.page_num}` : ""}
            {citation.section ? ` | ${citation.section}` : ""}
          </div>
          <p className="mt-2 text-sm text-gray-800">{citation.excerpt}</p>
        </div>
      ))}
    </div>
  );
}

function ComparisonTable({
  rows,
}: {
  rows: Array<{
    field_label: string;
    owner_value: string;
    other_party_value: string;
  }>;
}) {
  if (!rows.length) return null;

  return (
    <div className="mt-4 overflow-x-auto rounded-xl border">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 text-left">
          <tr>
            <th className="px-3 py-2 font-medium">Field</th>
            <th className="px-3 py-2 font-medium">Owner</th>
            <th className="px-3 py-2 font-medium">Other Party</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field_label} className="border-t">
              <td className="px-3 py-2 font-medium">{row.field_label}</td>
              <td className="px-3 py-2">{row.owner_value}</td>
              <td className="px-3 py-2">{row.other_party_value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailList({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  if (!items.length) return null;

  return (
    <div className="rounded-xl border bg-gray-50 p-4">
      <h3 className="font-semibold">{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-700">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

const DEFAULT_POLICY_CASE_ID = "demo-case";
const DEFAULT_ACCIDENT_CASE_ID = "demo-accident-2026-04";

const STAGE_3_RULE_EVENT = {
  sender_role: "owner",
  message_text: "@AI What is the 15-day acknowledgment rule for a California claim?",
  participants: [
    { user_id: "owner-1", role: "owner" },
    { user_id: "adjuster-1", role: "adjuster" },
  ],
  invite_sent: true,
  trigger: "MESSAGE" as const,
  metadata: { demo_label: "claim_rule_stage_3" },
};

type TriState = "unknown" | "true" | "false";

type StageAFormState = {
  occurred_at: string;
  address: string;
  quick_summary: string;

  owner_name: string;
  owner_phone: string;
  owner_insurer: string;
  owner_policy_number: string;

  other_name: string;
  other_phone: string;
  other_insurer: string;
  other_policy_number: string;

  injuries_reported: TriState;
  police_called: TriState;
  drivable: TriState;
  tow_requested: TriState;
};

type StageBFormState = {
  detailed_narrative: string;
  damage_summary: string;
  weather_conditions: string;
  road_conditions: string;
  police_report_number: string;
  adjuster_name: string;
  repair_shop_name: string;
  follow_up_notes: string;
};

const EMPTY_STAGE_A_FORM: StageAFormState = {
  occurred_at: "",
  address: "",
  quick_summary: "",

  owner_name: "",
  owner_phone: "",
  owner_insurer: "",
  owner_policy_number: "",

  other_name: "",
  other_phone: "",
  other_insurer: "",
  other_policy_number: "",

  injuries_reported: "unknown",
  police_called: "unknown",
  drivable: "unknown",
  tow_requested: "unknown",
};

const EMPTY_STAGE_B_FORM: StageBFormState = {
  detailed_narrative: "",
  damage_summary: "",
  weather_conditions: "",
  road_conditions: "",
  police_report_number: "",
  adjuster_name: "",
  repair_shop_name: "",
  follow_up_notes: "",
};

function booleanToTriState(value: unknown): TriState {
  if (value === true) return "true";
  if (value === false) return "false";
  return "unknown";
}

function triStateToBoolean(value: TriState): boolean | null {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

function toDateTimeLocalInput(value: unknown): string {
  if (!value || typeof value !== "string") return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const pad = (n: number) => String(n).padStart(2, "0");

  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function fromDateTimeLocalInput(value: string): string | null {
  if (!value.trim()) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

export default function HomePage() {
  const [caseId, setCaseId] = useState(DEFAULT_POLICY_CASE_ID);
  const [accidentCaseId, setAccidentCaseId] = useState(
    DEFAULT_ACCIDENT_CASE_ID
  );
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState(
    "What is the policy number, policy period, and insurer?"
  );
  const [chatMessage, setChatMessage] = useState(
    STAGE_3_RULE_EVENT.message_text
  );

  const [healthResult, setHealthResult] = useState<string>("");
  const [uploadResult, setUploadResult] =
    useState<UploadPolicyResponse | null>(null);
  const [askResult, setAskResult] = useState<AskResponse | null>(null);
  const [caseSnapshot, setCaseSnapshot] =
    useState<CaseSnapshotResponse | null>(null);
  const [reportResult, setReportResult] = useState<{
    report_payload: AccidentReportPayload;
    chat_context: AccidentChatContext;
  } | null>(null);
  const [chatResult, setChatResult] = useState<ChatEventResponse | null>(null);

  const [demoPolicies, setDemoPolicies] = useState<DemoPolicy[]>([]);
  const [policyStatus, setPolicyStatus] =
    useState<CasePolicyStatusResponse | null>(null);
  const [seedPolicyResult, setSeedPolicyResult] =
    useState<SeedDemoPolicyResponse | null>(null);

  const [stageAForm, setStageAForm] =
    useState<StageAFormState>(EMPTY_STAGE_A_FORM);
  const [stageBForm, setStageBForm] =
    useState<StageBFormState>(EMPTY_STAGE_B_FORM);

  const [stageAResultMessage, setStageAResultMessage] = useState("");
  const [stageBResultMessage, setStageBResultMessage] = useState("");

  const [loadingSaveStageA, setLoadingSaveStageA] = useState(false);
  const [loadingSaveStageB, setLoadingSaveStageB] = useState(false);

  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingAsk, setLoadingAsk] = useState(false);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [loadingSeed, setLoadingSeed] = useState(false);

  const [loadingDemoPolicies, setLoadingDemoPolicies] = useState(false);
  const [loadingPolicyStatus, setLoadingPolicyStatus] = useState(false);
  const [loadingSeedPolicy, setLoadingSeedPolicy] = useState(false);

  const [error, setError] = useState("");

  const canAsk = useMemo(() => {
    return !!uploadResult || !!policyStatus?.has_policy || !!seedPolicyResult;
  }, [uploadResult, policyStatus, seedPolicyResult]);

  useEffect(() => {
    loadDemoPolicies();
  }, []);

  useEffect(() => {
    if (!caseId.trim()) return;
    loadPolicyStatus(caseId);
  }, [caseId]);

  useEffect(() => {
    if (!caseSnapshot?.stage_a) return;

    const stageA = caseSnapshot.stage_a as Record<string, unknown>;
    const location =
      (stageA.location as Record<string, unknown> | undefined) || {};
    const ownerParty =
      (stageA.owner_party as Record<string, unknown> | undefined) || {};
    const otherParty =
      (stageA.other_party as Record<string, unknown> | undefined) || {};

    setStageAForm({
      occurred_at: toDateTimeLocalInput(stageA.occurred_at),
      address: String(location.address || ""),
      quick_summary: String(stageA.quick_summary || ""),

      owner_name: String(ownerParty.name || ""),
      owner_phone: String(ownerParty.phone || ""),
      owner_insurer: String(ownerParty.insurer || ""),
      owner_policy_number: String(ownerParty.policy_number || ""),

      other_name: String(otherParty.name || ""),
      other_phone: String(otherParty.phone || ""),
      other_insurer: String(otherParty.insurer || ""),
      other_policy_number: String(otherParty.policy_number || ""),

      injuries_reported: booleanToTriState(stageA.injuries_reported),
      police_called: booleanToTriState(stageA.police_called),
      drivable: booleanToTriState(stageA.drivable),
      tow_requested: booleanToTriState(stageA.tow_requested),
    });
  }, [caseSnapshot]);

  useEffect(() => {
    const stageB =
      (caseSnapshot?.stage_b as Record<string, unknown> | null) || null;

    if (!stageB) {
      setStageBForm(EMPTY_STAGE_B_FORM);
      return;
    }

    setStageBForm({
      detailed_narrative: String(stageB.detailed_narrative || ""),
      damage_summary: String(stageB.damage_summary || ""),
      weather_conditions: String(stageB.weather_conditions || ""),
      road_conditions: String(stageB.road_conditions || ""),
      police_report_number: String(stageB.police_report_number || ""),
      adjuster_name: String(stageB.adjuster_name || ""),
      repair_shop_name: String(stageB.repair_shop_name || ""),
      follow_up_notes: String(stageB.follow_up_notes || ""),
    });
  }, [caseSnapshot]);

  async function loadDemoPolicies() {
    setLoadingDemoPolicies(true);
    setError("");
    try {
      const result = await getDemoPolicies();
      setDemoPolicies(result.policies);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load demo policies failed");
    } finally {
      setLoadingDemoPolicies(false);
    }
  }

  async function loadPolicyStatus(targetCaseId: string) {
    if (!targetCaseId.trim()) return;

    setLoadingPolicyStatus(true);
    setError("");
    try {
      const result = await getCasePolicyStatus(targetCaseId.trim());
      setPolicyStatus(result);
    } catch (err) {
      setPolicyStatus(null);
      setError(
        err instanceof Error ? err.message : "Load policy status failed"
      );
    } finally {
      setLoadingPolicyStatus(false);
    }
  }

  async function handleHealthCheck() {
    setLoadingHealth(true);
    setError("");
    try {
      const result = await checkHealth();
      setHealthResult(JSON.stringify(result, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Health check failed");
    } finally {
      setLoadingHealth(false);
    }
  }

  async function handleSeedPolicy(selected: DemoPolicy) {
    setLoadingSeedPolicy(true);
    setError("");
    setAskResult(null);
    setUploadResult(null);
    setSeedPolicyResult(null);

    try {
      setCaseId(selected.default_case_id);
      const result = await seedDemoPolicy(selected.default_case_id);
      setSeedPolicyResult(result);
      setQuestion(
        selected.sample_questions[0] || "What is the policy number?"
      );
      await loadPolicyStatus(selected.default_case_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed demo policy failed");
    } finally {
      setLoadingSeedPolicy(false);
    }
  }

  async function handleUpload() {
    if (!file) return;

    setLoadingUpload(true);
    setError("");
    setUploadResult(null);
    setAskResult(null);

    try {
      const result = await uploadPolicy(caseId.trim(), file);
      setUploadResult(result);
      setSeedPolicyResult(null);
      await loadPolicyStatus(caseId.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoadingUpload(false);
    }
  }

  async function handleAsk() {
    if (!question.trim()) return;

    setLoadingAsk(true);
    setError("");
    setAskResult(null);

    try {
      const result = await askPolicyQuestion(caseId.trim(), question.trim());
      setAskResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask failed");
    } finally {
      setLoadingAsk(false);
    }
  }

  async function handleLoadSnapshot() {
    setLoadingSnapshot(true);
    setError("");
    try {
      const result = await getCaseSnapshot(accidentCaseId.trim());
      setCaseSnapshot(result);
      setReportResult(
        result.report_payload && result.chat_context
          ? {
              report_payload: result.report_payload,
              chat_context: result.chat_context,
            }
          : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load snapshot failed");
    } finally {
      setLoadingSnapshot(false);
    }
  }

  async function handleSeedAccidentDemo() {
    setLoadingSeed(true);
    setError("");
    setStageAResultMessage("");
    setStageBResultMessage("");
    try {
      const result = await seedAccidentDemoCase(accidentCaseId.trim());
      setCaseSnapshot(result.case_snapshot);
      setReportResult({
        report_payload: result.report_payload,
        chat_context: result.chat_context,
      });
      const seededStage3Response =
        result.sample_chat_responses.claim_rule_stage_3;
      setChatResult(
        seededStage3Response
          ? {
              case_id: result.case_id,
              response: seededStage3Response,
            }
          : null
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Seed accident demo failed"
      );
    } finally {
      setLoadingSeed(false);
    }
  }

  async function handleSaveStageA() {
    setLoadingSaveStageA(true);
    setError("");
    setStageAResultMessage("");

    try {
      const payload = {
        occurred_at: fromDateTimeLocalInput(stageAForm.occurred_at),
        location: {
          address: stageAForm.address || null,
        },
        owner_party: {
          role: "owner",
          name: stageAForm.owner_name,
          phone: stageAForm.owner_phone || null,
          insurer: stageAForm.owner_insurer || null,
          policy_number: stageAForm.owner_policy_number || null,
        },
        other_party: {
          role: "other_driver",
          name: stageAForm.other_name,
          phone: stageAForm.other_phone || null,
          insurer: stageAForm.other_insurer || null,
          policy_number: stageAForm.other_policy_number || null,
        },
        injuries_reported: triStateToBoolean(stageAForm.injuries_reported),
        police_called: triStateToBoolean(stageAForm.police_called),
        drivable: triStateToBoolean(stageAForm.drivable),
        tow_requested: triStateToBoolean(stageAForm.tow_requested),
        quick_summary: stageAForm.quick_summary,
        stage_completed_at: new Date().toISOString(),
      };

      await patchAccidentStageA(accidentCaseId.trim(), payload);
      setStageAResultMessage("Stage A saved successfully.");

      const refreshed = await getCaseSnapshot(accidentCaseId.trim());
      setCaseSnapshot(refreshed);
      setReportResult(
        refreshed.report_payload && refreshed.chat_context
          ? {
              report_payload: refreshed.report_payload,
              chat_context: refreshed.chat_context,
            }
          : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save Stage A failed");
    } finally {
      setLoadingSaveStageA(false);
    }
  }

  async function handleSaveStageB() {
    setLoadingSaveStageB(true);
    setError("");
    setStageBResultMessage("");

    try {
      const payload = {
        detailed_narrative: stageBForm.detailed_narrative,
        damage_summary: stageBForm.damage_summary || null,
        weather_conditions: stageBForm.weather_conditions || null,
        road_conditions: stageBForm.road_conditions || null,
        police_report_number: stageBForm.police_report_number || null,
        adjuster_name: stageBForm.adjuster_name || null,
        repair_shop_name: stageBForm.repair_shop_name || null,
        follow_up_notes: stageBForm.follow_up_notes || null,
        stage_completed_at: new Date().toISOString(),
      };

      await patchAccidentStageB(accidentCaseId.trim(), payload);
      setStageBResultMessage("Stage B saved successfully.");

      const refreshed = await getCaseSnapshot(accidentCaseId.trim());
      setCaseSnapshot(refreshed);
      setReportResult(
        refreshed.report_payload && refreshed.chat_context
          ? {
              report_payload: refreshed.report_payload,
              chat_context: refreshed.chat_context,
            }
          : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save Stage B failed");
    } finally {
      setLoadingSaveStageB(false);
    }
  }

  async function handleGenerateReport() {
    setLoadingReport(true);
    setError("");
    try {
      const result = await generateAccidentReport(accidentCaseId.trim());
      setReportResult(result);
      const refreshedSnapshot = await getCaseSnapshot(accidentCaseId.trim());
      setCaseSnapshot(refreshedSnapshot);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generate report failed");
    } finally {
      setLoadingReport(false);
    }
  }

  async function handleRunChatDemo() {
    setLoadingChat(true);
    setError("");
    setChatResult(null);
    try {
      const result = await sendChatEvent(accidentCaseId.trim(), {
        ...STAGE_3_RULE_EVENT,
        message_text: chatMessage.trim(),
      });
      setChatResult(result);
      const refreshedSnapshot = await getCaseSnapshot(accidentCaseId.trim());
      setCaseSnapshot(refreshedSnapshot);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat demo failed");
    } finally {
      setLoadingChat(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-5xl space-y-8">
        <div>
          <h1 className="text-3xl font-bold">ClaimMate Demo UI</h1>
          <p className="mt-2 text-gray-600">
            Shared backend demo for policy Q&amp;A, accident snapshot preview,
            and chat AI output.
          </p>
        </div>

        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">1. Backend Health Check</h2>
          <button
            onClick={handleHealthCheck}
            disabled={loadingHealth}
            className="mt-4 rounded-xl border px-4 py-2"
          >
            {loadingHealth ? "Checking..." : "Check /health"}
          </button>

          {healthResult && (
            <pre className="mt-4 overflow-x-auto rounded-xl bg-gray-100 p-4 text-sm">
              {healthResult}
            </pre>
          )}
        </section>

        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">2. Upload Policy PDF</h2>

          <div className="mt-4">
            <div className="flex items-center gap-3">
              <h3 className="font-medium">Built-in Demo Policies</h3>
              <button
                onClick={loadDemoPolicies}
                disabled={loadingDemoPolicies}
                className="rounded-xl border px-3 py-1 text-sm"
              >
                {loadingDemoPolicies ? "Loading..." : "Refresh demo policies"}
              </button>
            </div>

            {demoPolicies.length > 0 && (
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {demoPolicies.map((policy) => (
                  <button
                    key={policy.policy_key}
                    type="button"
                    onClick={() => handleSeedPolicy(policy)}
                    disabled={loadingSeedPolicy}
                    className="rounded-xl border bg-gray-50 p-4 text-left hover:bg-gray-100"
                  >
                    <div className="font-medium">{policy.label}</div>
                    <div className="mt-1 text-sm text-gray-600">
                      {policy.filename}
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      case_id: {policy.default_case_id}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="mt-4 space-y-4">
            <input
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              className="w-full rounded-xl border px-3 py-2"
              placeholder="case-id"
            />

            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />

            <button
              onClick={handleUpload}
              disabled={!file || loadingUpload}
              className="rounded-xl border px-4 py-2"
            >
              {loadingUpload ? "Uploading..." : "Upload"}
            </button>
          </div>

          {loadingPolicyStatus && (
            <div className="mt-4 text-sm text-gray-500">
              Loading policy status...
            </div>
          )}

          {policyStatus && (
            <div className="mt-4 rounded-xl border bg-gray-50 p-4 text-sm text-gray-700">
              <div className="font-medium">Current Policy Status</div>
              <div className="mt-2">
                has_policy: {policyStatus.has_policy ? "true" : "false"}
              </div>
              <div>filename: {policyStatus.filename || "None"}</div>
              <div>chunk_count: {policyStatus.chunk_count}</div>
              <div>source_label: {policyStatus.source_label || "None"}</div>
            </div>
          )}

          {seedPolicyResult && (
            <div className="mt-4 rounded bg-blue-50 p-3">
              Demo policy seeded: {seedPolicyResult.label} (
              {seedPolicyResult.filename})
            </div>
          )}

          {uploadResult && (
            <div className="mt-4 rounded bg-green-50 p-3">
              Upload success: {uploadResult.filename}
            </div>
          )}
        </section>

        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">3. Ask Question</h2>

          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="w-full rounded border p-2"
          />

          <button
            onClick={handleAsk}
            disabled={!canAsk || loadingAsk}
            className="mt-2 rounded-xl border px-4 py-2"
          >
            {loadingAsk ? "Asking..." : "Ask"}
          </button>

          {askResult && (
            <div className="mt-4">
              <h3 className="font-semibold">Answer</h3>
              <p className="mt-2">{askResult.answer}</p>

              <p className="mt-2 text-sm text-gray-500">
                {askResult.disclaimer}
              </p>

              <CitationList citations={askResult.citations} />
            </div>
          )}
        </section>

        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">4. Accident Case Snapshot</h2>
          <p className="mt-2 text-sm text-gray-600">
            Use the seeded accident demo case to preview Stage A/B data, report
            JSON, and chat-ready context.
          </p>

          <div className="mt-4 space-y-4">
            <input
              value={accidentCaseId}
              onChange={(e) => setAccidentCaseId(e.target.value)}
              className="w-full rounded-xl border px-3 py-2"
              placeholder="accident case id"
            />

            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleSeedAccidentDemo}
                disabled={loadingSeed}
                className="rounded-xl border px-4 py-2"
              >
                {loadingSeed ? "Seeding..." : "Seed accident demo case"}
              </button>
              <button
                onClick={handleLoadSnapshot}
                disabled={loadingSnapshot}
                className="rounded-xl border px-4 py-2"
              >
                {loadingSnapshot ? "Loading..." : "Load /cases/{case_id}"}
              </button>
              <button
                onClick={handleGenerateReport}
                disabled={loadingReport}
                className="rounded-xl border px-4 py-2"
              >
                {loadingReport ? "Generating..." : "Generate report JSON"}
              </button>
            </div>
          </div>

          <div className="mt-6 rounded-xl border p-4">
            <h3 className="text-lg font-semibold">Stage A Form</h3>
            <p className="mt-1 text-sm text-gray-600">
              This is the first real accident intake form for Lou’s workflow.
            </p>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Occurred At
                </label>
                <input
                  type="datetime-local"
                  value={stageAForm.occurred_at}
                  onChange={(e) =>
                    setStageAForm((prev) => ({
                      ...prev,
                      occurred_at: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Location Address
                </label>
                <input
                  value={stageAForm.address}
                  onChange={(e) =>
                    setStageAForm((prev) => ({
                      ...prev,
                      address: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                  placeholder="123 Main St, Los Angeles, CA"
                />
              </div>
            </div>

            <div className="mt-4">
              <label className="mb-1 block text-sm font-medium">
                Quick Summary
              </label>
              <textarea
                value={stageAForm.quick_summary}
                onChange={(e) =>
                  setStageAForm((prev) => ({
                    ...prev,
                    quick_summary: e.target.value,
                  }))
                }
                className="w-full rounded-xl border px-3 py-2"
                placeholder="Rear-end collision at a red light..."
              />
            </div>

            <div className="mt-6 grid gap-6 md:grid-cols-2">
              <div className="rounded-xl border bg-gray-50 p-4">
                <h4 className="font-semibold">Owner Party</h4>
                <div className="mt-3 space-y-3">
                  <input
                    value={stageAForm.owner_name}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        owner_name: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Owner name"
                  />
                  <input
                    value={stageAForm.owner_phone}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        owner_phone: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Owner phone"
                  />
                  <input
                    value={stageAForm.owner_insurer}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        owner_insurer: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Owner insurer"
                  />
                  <input
                    value={stageAForm.owner_policy_number}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        owner_policy_number: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Owner policy number"
                  />
                </div>
              </div>

              <div className="rounded-xl border bg-gray-50 p-4">
                <h4 className="font-semibold">Other Party</h4>
                <div className="mt-3 space-y-3">
                  <input
                    value={stageAForm.other_name}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        other_name: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Other driver name"
                  />
                  <input
                    value={stageAForm.other_phone}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        other_phone: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Other driver phone"
                  />
                  <input
                    value={stageAForm.other_insurer}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        other_insurer: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Other driver insurer"
                  />
                  <input
                    value={stageAForm.other_policy_number}
                    onChange={(e) =>
                      setStageAForm((prev) => ({
                        ...prev,
                        other_policy_number: e.target.value,
                      }))
                    }
                    className="w-full rounded-xl border px-3 py-2"
                    placeholder="Other driver policy number"
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-4">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Injuries Reported
                </label>
                <select
                  value={stageAForm.injuries_reported}
                  onChange={(e) =>
                    setStageAForm((prev) => ({
                      ...prev,
                      injuries_reported: e.target.value as TriState,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                >
                  <option value="unknown">Unknown</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Police Called
                </label>
                <select
                  value={stageAForm.police_called}
                  onChange={(e) =>
                    setStageAForm((prev) => ({
                      ...prev,
                      police_called: e.target.value as TriState,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                >
                  <option value="unknown">Unknown</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Vehicle Drivable
                </label>
                <select
                  value={stageAForm.drivable}
                  onChange={(e) =>
                    setStageAForm((prev) => ({
                      ...prev,
                      drivable: e.target.value as TriState,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                >
                  <option value="unknown">Unknown</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Tow Requested
                </label>
                <select
                  value={stageAForm.tow_requested}
                  onChange={(e) =>
                    setStageAForm((prev) => ({
                      ...prev,
                      tow_requested: e.target.value as TriState,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                >
                  <option value="unknown">Unknown</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={handleSaveStageA}
                disabled={loadingSaveStageA}
                className="rounded-xl border px-4 py-2"
              >
                {loadingSaveStageA ? "Saving..." : "Save Stage A"}
              </button>

              <button
                type="button"
                onClick={() => setStageAForm(EMPTY_STAGE_A_FORM)}
                className="rounded-xl border px-4 py-2"
              >
                Clear Form
              </button>
            </div>

            {stageAResultMessage && (
              <div className="mt-4 rounded bg-green-50 p-3 text-sm">
                {stageAResultMessage}
              </div>
            )}
          </div>

          <div className="mt-6 rounded-xl border p-4">
            <h3 className="text-lg font-semibold">Stage B Form</h3>
            <p className="mt-1 text-sm text-gray-600">
              This is the at-home follow-up form for detailed accident notes.
            </p>

            <div className="mt-4">
              <label className="mb-1 block text-sm font-medium">
                Detailed Narrative
              </label>
              <textarea
                value={stageBForm.detailed_narrative}
                onChange={(e) =>
                  setStageBForm((prev) => ({
                    ...prev,
                    detailed_narrative: e.target.value,
                  }))
                }
                className="w-full rounded-xl border px-3 py-2"
                placeholder="Describe what happened in more detail..."
                rows={5}
              />
            </div>

            <div className="mt-4">
              <label className="mb-1 block text-sm font-medium">
                Damage Summary
              </label>
              <textarea
                value={stageBForm.damage_summary}
                onChange={(e) =>
                  setStageBForm((prev) => ({
                    ...prev,
                    damage_summary: e.target.value,
                  }))
                }
                className="w-full rounded-xl border px-3 py-2"
                placeholder="Rear bumper damage, trunk misalignment..."
                rows={3}
              />
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Weather Conditions
                </label>
                <input
                  value={stageBForm.weather_conditions}
                  onChange={(e) =>
                    setStageBForm((prev) => ({
                      ...prev,
                      weather_conditions: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                  placeholder="Clear, rainy, foggy..."
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Road Conditions
                </label>
                <input
                  value={stageBForm.road_conditions}
                  onChange={(e) =>
                    setStageBForm((prev) => ({
                      ...prev,
                      road_conditions: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                  placeholder="Dry road, wet road..."
                />
              </div>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Police Report Number
                </label>
                <input
                  value={stageBForm.police_report_number}
                  onChange={(e) =>
                    setStageBForm((prev) => ({
                      ...prev,
                      police_report_number: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                  placeholder="Report number"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Adjuster Name
                </label>
                <input
                  value={stageBForm.adjuster_name}
                  onChange={(e) =>
                    setStageBForm((prev) => ({
                      ...prev,
                      adjuster_name: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                  placeholder="Adjuster name"
                />
              </div>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Repair Shop Name
                </label>
                <input
                  value={stageBForm.repair_shop_name}
                  onChange={(e) =>
                    setStageBForm((prev) => ({
                      ...prev,
                      repair_shop_name: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                  placeholder="Repair shop"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">
                  Follow-up Notes
                </label>
                <input
                  value={stageBForm.follow_up_notes}
                  onChange={(e) =>
                    setStageBForm((prev) => ({
                      ...prev,
                      follow_up_notes: e.target.value,
                    }))
                  }
                  className="w-full rounded-xl border px-3 py-2"
                  placeholder="Any extra notes"
                />
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={handleSaveStageB}
                disabled={loadingSaveStageB}
                className="rounded-xl border px-4 py-2"
              >
                {loadingSaveStageB ? "Saving..." : "Save Stage B"}
              </button>

              <button
                type="button"
                onClick={() => setStageBForm(EMPTY_STAGE_B_FORM)}
                className="rounded-xl border px-4 py-2"
              >
                Clear Form
              </button>
            </div>

            {stageBResultMessage && (
              <div className="mt-4 rounded bg-green-50 p-3 text-sm">
                {stageBResultMessage}
              </div>
            )}
          </div>

          {caseSnapshot && (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border bg-gray-50 p-4">
                <h3 className="font-semibold">Case Snapshot</h3>
                <div className="mt-2 text-sm text-gray-700">
                  <div>case_id: {caseSnapshot.case_id}</div>
                  <div>
                    claim_notice_at: {caseSnapshot.claim_notice_at || "Not set"}
                  </div>
                  <div>
                    proof_of_claim_at:{" "}
                    {caseSnapshot.proof_of_claim_at || "Not set"}
                  </div>
                  <div>updated_at: {caseSnapshot.updated_at}</div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border p-4">
                  <h3 className="font-semibold">Stage A</h3>
                  <p className="mt-2 text-sm text-gray-700">
                    {(caseSnapshot.stage_a.quick_summary as string) ||
                      "No quick summary yet."}
                  </p>
                </div>
                <div className="rounded-xl border p-4">
                  <h3 className="font-semibold">Stage B</h3>
                  <p className="mt-2 text-sm text-gray-700">
                    {(caseSnapshot.stage_b?.damage_summary as string) ||
                      "No damage summary yet."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {reportResult && (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border p-4">
                <h3 className="font-semibold">Report Preview</h3>
                <p className="mt-2 text-sm text-gray-700">
                  {reportResult.report_payload.accident_summary}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <DetailList
                  title="Chat Context Facts"
                  items={reportResult.chat_context.key_facts}
                />
                <DetailList
                  title="Missing / Follow-up Items"
                  items={
                    reportResult.chat_context.follow_up_items.length
                      ? reportResult.chat_context.follow_up_items
                      : ["No outstanding follow-up items in this seeded case."]
                  }
                />
              </div>

              <ComparisonTable
                rows={reportResult.report_payload.party_comparison_rows}
              />
            </div>
          )}
        </section>

        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">5. Chat Event Demo</h2>
          <p className="mt-2 text-sm text-gray-600">
            Runs a stage 3 chat event against the shared backend so you can see
            the neutral, citation-backed response shape that the frontend should
            render.
          </p>

          <textarea
            value={chatMessage}
            onChange={(e) => setChatMessage(e.target.value)}
            className="mt-4 w-full rounded-xl border p-3"
          />

          <button
            onClick={handleRunChatDemo}
            disabled={!chatMessage.trim() || loadingChat}
            className="mt-3 rounded-xl border px-4 py-2"
          >
            {loadingChat ? "Running..." : "Run stage 3 chat demo"}
          </button>

          {chatResult?.response && (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border p-4">
                <div className="text-sm text-gray-500">
                  Trigger: {chatResult.response.trigger}
                </div>
                <p className="mt-2">{chatResult.response.text}</p>
              </div>
              <CitationList citations={chatResult.response.citations} />
            </div>
          )}
        </section>

        {error && (
          <div className="rounded bg-red-100 p-3 text-red-700">{error}</div>
        )}
      </div>
    </main>
  );
}
