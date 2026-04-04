"use client";

import { useMemo, useState } from "react";
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
  rows: Array<{ field_label: string; owner_value: string; other_party_value: string }>;
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

export default function HomePage() {
  const [caseId, setCaseId] = useState(DEFAULT_POLICY_CASE_ID);
  const [accidentCaseId, setAccidentCaseId] = useState(DEFAULT_ACCIDENT_CASE_ID);
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState(
    "What is the policy number, policy period, and insurer?"
  );
  const [chatMessage, setChatMessage] = useState(STAGE_3_RULE_EVENT.message_text);

  const [healthResult, setHealthResult] = useState<string>("");
  const [uploadResult, setUploadResult] =
    useState<UploadPolicyResponse | null>(null);
  const [askResult, setAskResult] = useState<AskResponse | null>(null);
  const [caseSnapshot, setCaseSnapshot] = useState<CaseSnapshotResponse | null>(null);
  const [reportResult, setReportResult] = useState<{
    report_payload: AccidentReportPayload;
    chat_context: AccidentChatContext;
  } | null>(null);
  const [chatResult, setChatResult] = useState<ChatEventResponse | null>(null);

  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingAsk, setLoadingAsk] = useState(false);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [loadingSeed, setLoadingSeed] = useState(false);

  const [error, setError] = useState("");

  const canAsk = useMemo(() => !!uploadResult, [uploadResult]);

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

  async function handleUpload() {
    if (!file) return;

    setLoadingUpload(true);
    setError("");
    setUploadResult(null);
    setAskResult(null);

    try {
      const result = await uploadPolicy(caseId.trim(), file);
      setUploadResult(result);
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
      const result = await askPolicyQuestion(
        caseId.trim(),
        question.trim()
      );
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
    try {
      const result = await seedAccidentDemoCase(accidentCaseId.trim());
      setCaseSnapshot(result.case_snapshot);
      setReportResult({
        report_payload: result.report_payload,
        chat_context: result.chat_context,
      });
      const seededStage3Response = result.sample_chat_responses.claim_rule_stage_3;
      setChatResult(
        seededStage3Response
          ? {
              case_id: result.case_id,
              response: seededStage3Response,
            }
          : null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed accident demo failed");
    } finally {
      setLoadingSeed(false);
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
      <div className="mx-auto max-w-4xl space-y-8">
        <div>
          <h1 className="text-3xl font-bold">ClaimMate Demo UI</h1>
          <p className="mt-2 text-gray-600">
            Shared backend demo for policy Q&A, accident snapshot preview, and
            chat AI output.
          </p>
        </div>

        {/* Health */}
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

        {/* Upload */}
        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">2. Upload Policy PDF</h2>

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

          {uploadResult && (
            <div className="mt-4 bg-green-50 p-3 rounded">
              Upload success: {uploadResult.filename}
            </div>
          )}
        </section>

        {/* Ask */}
        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">3. Ask Question</h2>

          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="w-full border rounded p-2"
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

          {caseSnapshot && (
            <div className="mt-6 space-y-4">
              <div className="rounded-xl border bg-gray-50 p-4">
                <h3 className="font-semibold">Case Snapshot</h3>
                <div className="mt-2 text-sm text-gray-700">
                  <div>case_id: {caseSnapshot.case_id}</div>
                  <div>claim_notice_at: {caseSnapshot.claim_notice_at || "Not set"}</div>
                  <div>proof_of_claim_at: {caseSnapshot.proof_of_claim_at || "Not set"}</div>
                  <div>updated_at: {caseSnapshot.updated_at}</div>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-xl border p-4">
                  <h3 className="font-semibold">Stage A</h3>
                  <p className="mt-2 text-sm text-gray-700">
                    {(caseSnapshot.stage_a.quick_summary as string) || "No quick summary yet."}
                  </p>
                </div>
                <div className="rounded-xl border p-4">
                  <h3 className="font-semibold">Stage B</h3>
                  <p className="mt-2 text-sm text-gray-700">
                    {(caseSnapshot.stage_b?.damage_summary as string) || "No damage summary yet."}
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

              <ComparisonTable rows={reportResult.report_payload.party_comparison_rows} />
            </div>
          )}
        </section>

        <section className="rounded-2xl border bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">5. Chat Event Demo</h2>
          <p className="mt-2 text-sm text-gray-600">
            Runs a stage 3 chat event against the shared backend so you can see
            the neutral, citation-backed response shape that the frontend should render.
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
          <div className="bg-red-100 text-red-700 p-3 rounded">
            {error}
          </div>
        )}
      </div>
    </main>
  );
}
