"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { jobpilot, type DecisionCategory, type ScoredJob } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Card, DecisionBadge, ErrorBox, FitBadge, ScoreBar, Spinner } from "@/components/ui";

const PROFILE_ID = 1;
const LIMIT = 50;
const CATEGORIES: (DecisionCategory | "ALL")[] = ["ALL", "AUTO_APPLY", "REVIEW", "REJECT"];

const LOCATIONS = [
  { label: "SF Bay Area", value: "San Francisco Bay Area" },
  { label: "Anywhere", value: "" },
];
const EMPLOYMENT = [
  { label: "Full-time", value: "full_time" },
  { label: "Internship", value: "internship" },
  { label: "Contract", value: "contract" },
  { label: "Part-time", value: "part_time" },
  { label: "Any", value: "" },
];

function prettyType(t: string): string {
  return t ? t.replace(/_/g, "-").replace(/\b\w/g, (c) => c.toUpperCase()) : "";
}

export default function MatchesPage() {
  const [minScore, setMinScore] = useState(70);
  const [category, setCategory] = useState<DecisionCategory | "ALL">("ALL");
  // Defaults encode the requested search: 2–5 yrs (mid-senior), Bay Area, full-time.
  const [minYears, setMinYears] = useState(2);
  const [maxYears, setMaxYears] = useState(5);
  const [location, setLocation] = useState(LOCATIONS[0].value);
  const [employmentType, setEmploymentType] = useState(EMPLOYMENT[0].value);
  const [includeRemote, setIncludeRemote] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [tracking, setTracking] = useState<Record<number, "loading" | "done" | "error">>({});
  const router = useRouter();

  const { data, error, loading } = useAsync(
    () =>
      jobpilot.matches(PROFILE_ID, {
        minScore,
        category: category === "ALL" ? undefined : category,
        minYears,
        maxYears,
        location: location || undefined,
        employmentType: employmentType || undefined,
        includeRemote,
      }),
    [minScore, category, minYears, maxYears, location, employmentType, includeRemote]
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
      <div>
        <h1 className="text-2xl font-semibold">Matches</h1>
        <p className="mt-1 text-gray-500">
          Real ATS jobs scored against your profile, ranked by fit.
        </p>
      </div>

      {/* Filter bar */}
      <Card className="flex flex-wrap items-end gap-x-6 gap-y-4">
        <label className="flex flex-col text-xs font-medium text-gray-500">
          Min fit: {minScore}%
          <input
            type="range" min={0} max={100} step={5} value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="mt-2 w-40"
          />
        </label>

        <div className="flex flex-col text-xs font-medium text-gray-500">
          Experience (years)
          <div className="mt-1 flex items-center gap-1">
            <input
              type="number" min={0} max={30} value={minYears}
              onChange={(e) => setMinYears(Number(e.target.value))}
              className="w-14 rounded-md border border-gray-200 px-2 py-1 text-sm"
            />
            <span className="text-gray-400">–</span>
            <input
              type="number" min={0} max={30} value={maxYears}
              onChange={(e) => setMaxYears(Number(e.target.value))}
              className="w-14 rounded-md border border-gray-200 px-2 py-1 text-sm"
            />
            <span className="ml-1 text-gray-400">mid-senior</span>
          </div>
        </div>

        <label className="flex flex-col text-xs font-medium text-gray-500">
          Location
          <select
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="mt-1 rounded-md border border-gray-200 px-2 py-1.5 text-sm"
          >
            {LOCATIONS.map((l) => (
              <option key={l.label} value={l.value}>{l.label}</option>
            ))}
          </select>
        </label>

        <label className="flex flex-col text-xs font-medium text-gray-500">
          Employment
          <select
            value={employmentType}
            onChange={(e) => setEmploymentType(e.target.value)}
            className="mt-1 rounded-md border border-gray-200 px-2 py-1.5 text-sm"
          >
            {EMPLOYMENT.map((t) => (
              <option key={t.label} value={t.value}>{t.label}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 text-xs font-medium text-gray-500">
          <input
            type="checkbox" checked={includeRemote}
            onChange={(e) => setIncludeRemote(e.target.checked)}
          />
          Include remote
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
      </Card>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}

      {data && (
        <>
          <p className="text-sm text-gray-500">
            {data.length.toLocaleString()} matches
            {data.length > LIMIT && ` · showing top ${LIMIT}`}
          </p>
          {data.length === 0 && (
            <Card>
              <p className="text-sm text-gray-500">
                No jobs match these filters. Loosen the experience range or location,
                or run <span className="font-medium">Discovery</span> to pull more real
                postings.
              </p>
            </Card>
          )}
          <div className="flex flex-col gap-2">
            {data.slice(0, LIMIT).map((m) => (
              <Card key={m.job_id} className="!p-0 overflow-hidden">
                <div className="flex items-center gap-4 p-4">
                  <FitBadge value={m.score.overall} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{m.title}</p>
                    <p className="truncate text-sm text-gray-500">
                      {m.company}
                      {m.location && <span className="text-gray-400"> · {m.location}</span>}
                      {m.remote && <span className="text-gray-400"> · Remote</span>}
                      {m.employment_type && m.employment_type !== "full_time" && (
                        <span className="text-amber-600"> · {prettyType(m.employment_type)}</span>
                      )}
                    </p>
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
                    <div className="mt-3 flex items-center justify-between">
                      <p className="text-xs text-gray-400">
                        Decision: {m.decision.reasons[0]} (confidence {m.decision.confidence}%)
                      </p>
                      {m.url && (
                        <a href={m.url} target="_blank" rel="noopener" className="text-xs text-blue-600 hover:underline">
                          View posting ↗
                        </a>
                      )}
                    </div>
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
