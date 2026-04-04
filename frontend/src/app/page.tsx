"use client";

import { useMemo, useState } from "react";
import {
  askPolicyQuestion,
  checkHealth,
  Citation,
  UploadPolicyResponse,
  AskResponse,
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

export default function HomePage() {
  const [caseId, setCaseId] = useState("demo-case");
  const [file, setFile] = useState<File | null>(null);
  const [question, setQuestion] = useState(
    "What is the policy number, policy period, and insurer?"
  );

  const [healthResult, setHealthResult] = useState<string>("");
  const [uploadResult, setUploadResult] =
    useState<UploadPolicyResponse | null>(null);
  const [askResult, setAskResult] = useState<AskResponse | null>(null);

  const [loadingHealth, setLoadingHealth] = useState(false);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingAsk, setLoadingAsk] = useState(false);

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

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl space-y-8">
        <div>
          <h1 className="text-3xl font-bold">ClaimMate Demo UI</h1>
          <p className="mt-2 text-gray-600">
            Minimal happy path: health check, policy upload, question answering,
            and citations.
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

        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded">
            {error}
          </div>
        )}
      </div>
    </main>
  );
}