"use client";

import { useState } from "react";
import Link from "next/link";
import { jobpilot, type DiscoveryResult, type Job } from "@/lib/api";
import { Card } from "@/components/ui";

const DEFAULT_SOURCES = [
  { type: "greenhouse", token: "anthropic" },
  { type: "ashby", token: "openai" },
  { type: "greenhouse", token: "stripe" },
  { type: "greenhouse", token: "databricks" },
];

export default function DiscoveryPage() {
  const [sources, setSources] = useState(DEFAULT_SOURCES);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<DiscoveryResult | null>(null);
  const [runErr, setRunErr] = useState<string | null>(null);

  const [url, setUrl] = useState("");
  const [imported, setImported] = useState<Job | null>(null);
  const [importErr, setImportErr] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  function update(i: number, key: "type" | "token", val: string) {
    setSources((s) => s.map((row, idx) => (idx === i ? { ...row, [key]: val } : row)));
  }

  async function run() {
    setRunning(true);
    setRunErr(null);
    setResult(null);
    try {
      setResult(await jobpilot.runDiscovery(sources));
    } catch (e) {
      setRunErr((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  async function doImport() {
    if (!url.trim()) return;
    setImporting(true);
    setImportErr(null);
    setImported(null);
    try {
      setImported(await jobpilot.importUrl(url.trim()));
    } catch (e) {
      setImportErr((e as Error).message);
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Discovery</h1>
        <p className="mt-1 text-gray-500">
          Pull real listings from public ATS boards, or import a single job by URL.
        </p>
      </div>

      <Card>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          ATS boards
        </h2>
        <div className="flex flex-col gap-2">
          {sources.map((s, i) => (
            <div key={i} className="flex gap-2">
              <select
                value={s.type}
                onChange={(e) => update(i, "type", e.target.value)}
                className="rounded-md border border-gray-200 px-2 py-1.5 text-sm"
              >
                <option value="greenhouse">Greenhouse</option>
                <option value="lever">Lever</option>
                <option value="ashby">Ashby</option>
              </select>
              <input
                value={s.token}
                onChange={(e) => update(i, "token", e.target.value)}
                placeholder="board token (e.g. anthropic)"
                className="flex-1 rounded-md border border-gray-200 px-2 py-1.5 text-sm"
              />
              <button
                onClick={() => setSources((arr) => arr.filter((_, idx) => idx !== i))}
                className="rounded-md px-2 text-gray-400 hover:text-red-600"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            onClick={() => setSources((s) => [...s, { type: "greenhouse", token: "" }])}
            className="self-start text-sm text-blue-600 hover:underline"
          >
            + Add board
          </button>
        </div>
        <button
          onClick={run}
          disabled={running}
          className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {running ? "Discovering…" : "Run discovery"}
        </button>

        {runErr && <p className="mt-3 text-sm text-red-600">{runErr}</p>}
        {result && (
          <div className="mt-4 rounded-md bg-gray-50 p-4 text-sm">
            <p className="font-medium text-green-700">
              +{result.added} new jobs · {result.skipped_duplicates} duplicates skipped
            </p>
            <ul className="mt-2 text-gray-600">
              {Object.entries(result.per_source).map(([k, v]) => (
                <li key={k}>
                  {k}: +{v}
                </li>
              ))}
            </ul>
            {result.errors.length > 0 && (
              <ul className="mt-2 text-red-600">
                {result.errors.map((e, i) => (
                  <li key={i}>⚠ {e}</li>
                ))}
              </ul>
            )}
            <Link href="/matches" className="mt-2 inline-block text-blue-600 hover:underline">
              See matches →
            </Link>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Import by URL
        </h2>
        <p className="mb-3 text-xs text-gray-400">
          ATS links (Greenhouse/Lever/Ashby) use their API. LinkedIn/Indeed/Jobright links are
          fetched best-effort and often blocked — paste details manually if so.
        </p>
        <div className="flex gap-2">
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://job-boards.greenhouse.io/…"
            className="flex-1 rounded-md border border-gray-200 px-2 py-1.5 text-sm"
          />
          <button
            onClick={doImport}
            disabled={importing}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            {importing ? "…" : "Import"}
          </button>
        </div>
        {importErr && <p className="mt-3 text-sm text-red-600">{importErr}</p>}
        {imported && (
          <div className="mt-3 rounded-md bg-gray-50 p-3 text-sm">
            <p className="font-medium">{imported.title}</p>
            <p className="text-gray-500">
              {imported.company} · {imported.location || "—"} · skills: {imported.skills.slice(0, 5).join(", ") || "—"}
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
