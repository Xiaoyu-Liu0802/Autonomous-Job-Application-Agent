"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { jobpilot, type ApplicationPlan, type DraftedAnswer, type TailoredResume } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Card, ErrorBox, FitBadge, Spinner, StatusBadge } from "@/components/ui";

const DEFAULT_QUESTIONS = [
  "Will you now or in the future require sponsorship?",
  "What is your expected salary?",
  "Why do you want to work here?",
];

export default function ApplicationDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { data, error, loading, reload } = useAsync(async () => {
    const app = await jobpilot.application(id);
    const job = await jobpilot.job(app.job_id).catch(() => null);
    return { app, job };
  }, [id]);

  const [plan, setPlan] = useState<ApplicationPlan | null>(null);
  const [questions, setQuestions] = useState(DEFAULT_QUESTIONS.join("\n"));
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<Record<string, DraftedAnswer>>({});
  const [drafting, setDrafting] = useState<string | null>(null);
  const [resume, setResume] = useState<TailoredResume | null>(null);
  const [busy, setBusy] = useState(false);

  async function draft(question: string) {
    setDrafting(question);
    try {
      const d = await jobpilot.draftAnswer(id, question);
      setDrafts((m) => ({ ...m, [question]: d }));
      if (d.answer) setAnswers((a) => ({ ...a, [question]: d.answer }));
    } finally {
      setDrafting(null);
    }
  }

  async function tailorResume(jobId: number) {
    setBusy(true);
    try {
      setResume(await jobpilot.tailorResume(data!.app.profile_id, jobId));
    } finally {
      setBusy(false);
    }
  }

  async function runPrepare() {
    setBusy(true);
    try {
      const qs = questions.split("\n").map((q) => q.trim()).filter(Boolean);
      setPlan(await jobpilot.prepare(id, qs));
      reload();
    } finally {
      setBusy(false);
    }
  }

  async function saveAnswer(q: string) {
    if (!answers[q]) return;
    setBusy(true);
    try {
      await jobpilot.answer(id, q, answers[q], true);
      setPlan((p) => p && { ...p, open_questions: p.open_questions.filter((oq) => oq.question !== q) });
      reload();
    } finally {
      setBusy(false);
    }
  }

  async function advance() {
    setBusy(true);
    try {
      await jobpilot.advance(id);
      reload();
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;
  const { app, job } = data;

  return (
    <div className="flex flex-col gap-6">
      <Link href="/applications" className="text-sm text-blue-600 hover:underline">
        ← All applications
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{job?.company ?? `Job #${app.job_id}`}</h1>
            <StatusBadge status={app.status} />
            {app.fit_score != null && <FitBadge value={app.fit_score} />}
          </div>
          <p className="mt-1 text-gray-600">{job?.title}</p>
          {job?.url && (
            <a href={job.url} target="_blank" rel="noopener" className="text-sm text-blue-600 hover:underline">
              View posting ↗
            </a>
          )}
        </div>
        <button
          onClick={advance}
          disabled={busy}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Advance pipeline →
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Prepare / human-in-the-loop */}
        <Card>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
            Prepare application
          </h2>
          <label className="text-xs text-gray-500">Application questions (one per line)</label>
          <textarea
            value={questions}
            onChange={(e) => setQuestions(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded-md border border-gray-200 p-2 text-sm"
          />
          <button
            onClick={runPrepare}
            disabled={busy}
            className="mt-2 rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            Build fill plan
          </button>

          {plan && (
            <div className="mt-4 flex flex-col gap-4">
              <div>
                <p className="text-xs font-medium text-green-700">
                  ✓ {plan.known_fields.length} fields the agent can fill
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {plan.known_fields.map((f) => (
                    <span key={f.field} className="rounded bg-green-50 px-2 py-0.5 text-xs text-green-800">
                      {f.field}
                    </span>
                  ))}
                </div>
              </div>

              {plan.open_questions.length > 0 ? (
                <div>
                  <p className="text-xs font-medium text-amber-700">
                    ⚠️ {plan.open_questions.length} need you
                  </p>
                  <div className="mt-2 flex flex-col gap-3">
                    {plan.open_questions.map((q) => {
                      const d = drafts[q.question];
                      return (
                      <div key={q.question} className="rounded-md border border-amber-200 bg-amber-50 p-3">
                        <p className="text-sm font-medium">{q.question}</p>
                        <p className="text-xs text-amber-700">{q.reason}</p>
                        {q.suggestion && !d && (
                          <p className="mt-1 text-xs text-gray-500">💡 Suggested: {q.suggestion}</p>
                        )}
                        {d && (
                          <div className="mt-2 rounded border border-gray-200 bg-white p-2 text-xs">
                            <span
                              className={`font-medium ${d.grounded ? "text-green-700" : "text-red-600"}`}
                            >
                              {d.grounded ? "✓ Grounded" : "⚠ Unverified"}
                            </span>{" "}
                            <span className="text-gray-400">
                              · {d.provider} · confidence {d.confidence.toFixed(0)}%
                            </span>
                            <p className="mt-1 text-gray-600">{d.reason}</p>
                            {d.violations.length > 0 && (
                              <ul className="mt-1 text-red-600">
                                {d.violations.map((v, i) => <li key={i}>• {v}</li>)}
                              </ul>
                            )}
                          </div>
                        )}
                        <div className="mt-2 flex gap-2">
                          <input
                            value={answers[q.question] ?? q.suggestion ?? ""}
                            onChange={(e) => setAnswers((a) => ({ ...a, [q.question]: e.target.value }))}
                            placeholder="Your answer…"
                            className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm"
                          />
                          <button
                            onClick={() => draft(q.question)}
                            disabled={drafting === q.question}
                            className="rounded border border-blue-300 px-2 py-1 text-sm text-blue-700 hover:bg-blue-50 disabled:opacity-50"
                            title="Draft a grounded answer from your profile"
                          >
                            {drafting === q.question ? "…" : "✨ Draft"}
                          </button>
                          <button
                            onClick={() => saveAnswer(q.question)}
                            disabled={busy}
                            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                          >
                            Save
                          </button>
                        </div>
                      </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-green-700">
                  ✓ Ready — no open questions. (Browser runner would fill &amp; pause for your submit.)
                </p>
              )}
            </div>
          )}
        </Card>

        {/* Timeline */}
        <Card>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
            Timeline
          </h2>
          <ol className="flex flex-col gap-3">
            {app.actions.map((a, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="w-5 text-center">{a.icon}</span>
                <div>
                  <p className="text-gray-800">{a.event}</p>
                  <p className="text-xs text-gray-400">{a.at.replace("T", " ").replace("+00:00", " UTC")}</p>
                </div>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      {/* Resume tailoring (LLM layer, grounded) */}
      <Card>
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Tailor resume
          </h2>
          <button
            onClick={() => job && tailorResume(job.id)}
            disabled={busy || !job}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
          >
            ✨ Tailor to this role
          </button>
        </div>

        {resume ? (
          <div className="mt-4 flex flex-col gap-3 text-sm">
            <div>
              <span className={`text-xs font-medium ${resume.grounded ? "text-green-700" : "text-red-600"}`}>
                {resume.grounded ? "✓ Grounded — no invented claims" : "⚠ Contains unverified claims"}
              </span>
              <span className="ml-2 text-xs text-gray-400">via {resume.provider}</span>
              <p className="mt-1 rounded-md bg-gray-50 p-3 text-gray-800">{resume.summary}</p>
            </div>

            {resume.highlighted_skills.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500">Skills to lead with</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {resume.highlighted_skills.map((s) => (
                    <span key={s} className="rounded bg-green-50 px-2 py-0.5 text-xs text-green-800">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {resume.missing_skills.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500">Gaps to be honest about</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {resume.missing_skills.map((s) => (
                    <span key={s} className="rounded bg-amber-50 px-2 py-0.5 text-xs text-amber-800">{s}</span>
                  ))}
                </div>
              </div>
            )}

            {resume.emphasis.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500">Experience, reordered by relevance</p>
                <ol className="mt-1 flex flex-col gap-1">
                  {resume.emphasis.map((b, i) => (
                    <li key={i} className="text-gray-700">• {b.text}</li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        ) : (
          <p className="mt-3 text-sm text-gray-500">
            Reorders and summarizes your real experience for this role — emphasize only, never
            embellish. Every line is checked against your profile before it&apos;s shown.
          </p>
        )}
      </Card>
    </div>
  );
}
