"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { jobpilot, type DecisionCategory, type ScoredJob } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Card, DecisionBadge, ErrorBox, FitBadge, ScoreBar, Spinner } from "@/components/ui";

const PROFILE_ID = 1;
const LIMIT = 50;
const CATEGORIES: (DecisionCategory | "ALL")[] = ["ALL", "AUTO_APPLY", "REVIEW", "REJECT"];

export default function MatchesPage() {
  const [minScore, setMinScore] = useState(70);
  const [category, setCategory] = useState<DecisionCategory | "ALL">("ALL");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [tracking, setTracking] = useState<Record<number, "loading" | "done" | "error">>({});
  const router = useRouter();

  const { data, error, loading } = useAsync(
    () => jobpilot.matches(PROFILE_ID, minScore, category === "ALL" ? undefined : category),
    [minScore, category]
  );

  async function track(job: ScoredJob) {
    setTracking((t) => ({ ...t, [job.job_id]: "loading" }));
    try {
      const app = await jobpilot.createApplication(PROFILE_ID, job.job_id);
      setTracking((t) => ({ ...t, [job.job_id]: "done" }));
      router.push(`/applications/${app.id}`);
    } catch {
      setTracking((t) => ({ ...t, [job.job_id]: "error" }));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Matches</h1>
          <p className="mt-1 text-gray-500">Jobs scored against your profile, ranked by fit.</p>
        </div>
        <div className="flex items-end gap-4">
          <label className="flex flex-col text-xs font-medium text-gray-500">
            Min fit: {minScore}%
            <input
              type="range" min={0} max={100} step={5} value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="mt-1 w-40"
            />
          </label>
          <div className="flex gap-1">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setCategory(c)}
                className={`rounded-md px-2.5 py-1.5 text-xs font-medium ${
                  category === c ? "bg-blue-600 text-white" : "bg-white text-gray-600 border border-gray-200"
                }`}
              >
                {c.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}

      {data && (
        <>
          <p className="text-sm text-gray-500">
            {data.length.toLocaleString()} matches
            {data.length > LIMIT && ` · showing top ${LIMIT}`}
          </p>
          <div className="flex flex-col gap-2">
            {data.slice(0, LIMIT).map((m) => (
              <Card key={m.job_id} className="!p-0 overflow-hidden">
                <div className="flex items-center gap-4 p-4">
                  <FitBadge value={m.score.overall} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{m.title}</p>
                    <p className="truncate text-sm text-gray-500">{m.company}</p>
                  </div>
                  <DecisionBadge category={m.decision.category} />
                  <button
                    onClick={() => setExpanded(expanded === m.job_id ? null : m.job_id)}
                    className="rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
                  >
                    {expanded === m.job_id ? "Hide" : "Details"}
                  </button>
                  <button
                    onClick={() => track(m)}
                    disabled={tracking[m.job_id] === "loading" || tracking[m.job_id] === "done"}
                    className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {tracking[m.job_id] === "done" ? "Tracked ✓" : tracking[m.job_id] === "loading" ? "…" : "Track"}
                  </button>
                </div>

                {expanded === m.job_id && (
                  <div className="border-t border-gray-100 bg-gray-50 p-4">
                    <div className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
                      <ScoreBar label="Skills" value={m.score.skills} />
                      <ScoreBar label="Experience" value={m.score.experience} />
                      <ScoreBar label="Education" value={m.score.education} />
                      <ScoreBar label="Role" value={m.score.role} />
                      <ScoreBar label="Location" value={m.score.location} />
                      <ScoreBar label="Preferences" value={m.score.preferences} />
                    </div>
                    {m.score.matched_skills.length > 0 && (
                      <p className="mt-3 text-sm text-gray-600">
                        <span className="font-medium text-green-700">Matched:</span>{" "}
                        {m.score.matched_skills.join(", ")}
                      </p>
                    )}
                    {m.score.gaps.length > 0 && (
                      <ul className="mt-2 text-sm text-amber-700">
                        {m.score.gaps.map((g, i) => (
                          <li key={i}>{g}</li>
                        ))}
                      </ul>
                    )}
                    <p className="mt-3 text-xs text-gray-400">
                      Decision: {m.decision.reasons[0]} (confidence {m.decision.confidence}%)
                    </p>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
