"use client";

import Link from "next/link";
import { jobpilot, type Application } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Card, ErrorBox, Spinner, StatTile } from "@/components/ui";

const INTERVIEW_STAGES = ["recruiter_screen", "technical_interview", "onsite"];

function funnelStats(apps: Application[], jobCount: number) {
  const applied = apps.filter((a) =>
    ["applied", ...INTERVIEW_STAGES, "offer"].includes(a.status)
  ).length;
  const interviews = apps.filter((a) => INTERVIEW_STAGES.includes(a.status)).length;
  const offers = apps.filter((a) => a.status === "offer").length;
  const responses = apps.filter((a) => [...INTERVIEW_STAGES, "offer"].includes(a.status)).length;
  const responseRate = applied ? Math.round((responses / applied) * 1000) / 10 : 0;
  return {
    rows: [
      { label: "Discovered", value: jobCount },
      { label: "Tracked", value: apps.length },
      { label: "Applied", value: applied },
      { label: "Interviews", value: interviews },
      { label: "Offers", value: offers },
    ],
    stats: { total: apps.length, applied, interviews, offers, responseRate },
  };
}

export default function OverviewPage() {
  const { data, error, loading } = useAsync(
    async () => {
      const [apps, jobs] = await Promise.all([jobpilot.applications(), jobpilot.jobs()]);
      return { apps, jobCount: jobs.length };
    },
    []
  );

  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;

  const { rows, stats } = funnelStats(data.apps, data.jobCount);
  const max = Math.max(...rows.map((r) => r.value), 1);

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold">Good day 👋</h1>
        <p className="mt-1 text-gray-500">
          {data.jobCount.toLocaleString()} jobs discovered · {stats.total} tracked ·{" "}
          <Link href="/matches" className="text-blue-600 hover:underline">
            browse matches →
          </Link>
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatTile label="Tracked" value={stats.total} />
        <StatTile label="Applied" value={stats.applied} />
        <StatTile label="Interviews" value={stats.interviews} />
        <StatTile label="Offers" value={stats.offers} />
        <StatTile label="Response Rate" value={`${stats.responseRate}%`} />
      </div>

      <Card>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Pipeline
        </h2>
        <div className="flex flex-col gap-3">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center gap-3 text-sm">
              <span className="w-24 shrink-0 text-gray-600">{r.label}</span>
              <div className="h-6 flex-1 overflow-hidden rounded bg-gray-100">
                <div
                  className="flex h-full items-center justify-end rounded bg-blue-500 pr-2 text-xs font-medium text-white"
                  style={{ width: `${Math.max((r.value / max) * 100, 6)}%` }}
                >
                  {r.value}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
