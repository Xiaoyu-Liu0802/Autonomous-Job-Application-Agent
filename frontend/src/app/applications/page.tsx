"use client";

import Link from "next/link";
import { jobpilot, type Job } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { Card, ErrorBox, FitBadge, Spinner, StatusBadge } from "@/components/ui";

export default function ApplicationsPage() {
  const { data, error, loading } = useAsync(async () => {
    const [apps, jobs] = await Promise.all([jobpilot.applications(), jobpilot.jobs()]);
    const jobMap = new Map<number, Job>(jobs.map((j) => [j.id, j]));
    return { apps, jobMap };
  }, []);

  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data) return null;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Applications</h1>
        <p className="mt-1 text-gray-500">{data.apps.length} tracked</p>
      </div>

      {data.apps.length === 0 ? (
        <Card>
          <p className="text-sm text-gray-500">
            No applications yet.{" "}
            <Link href="/matches" className="text-blue-600 hover:underline">
              Track one from Matches →
            </Link>
          </p>
        </Card>
      ) : (
        <Card className="!p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left text-xs uppercase tracking-wide text-gray-400">
                <th className="px-4 py-3 font-medium">Company</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Fit</th>
                <th className="px-4 py-3 font-medium">Applied</th>
                <th className="px-4 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.apps.map((a) => {
                const job = data.jobMap.get(a.job_id);
                return (
                  <tr key={a.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link href={`/applications/${a.id}`} className="font-medium text-blue-600 hover:underline">
                        {job?.company ?? `Job #${a.job_id}`}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{job?.title ?? "—"}</td>
                    <td className="px-4 py-3">{a.fit_score != null ? <FitBadge value={a.fit_score} /> : "—"}</td>
                    <td className="px-4 py-3 text-gray-500">{a.applied_at ? a.applied_at.slice(0, 10) : "—"}</td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
