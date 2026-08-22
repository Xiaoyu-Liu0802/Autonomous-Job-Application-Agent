import type { DecisionCategory, ApplicationStatus } from "@/lib/api";

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white p-5 ${className}`}>
      {children}
    </div>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</span>
      <span className="text-3xl font-semibold tabular-nums">{value}</span>
      {hint && <span className="text-xs text-gray-400">{hint}</span>}
    </Card>
  );
}

const DECISION_STYLES: Record<DecisionCategory, string> = {
  AUTO_APPLY: "bg-green-100 text-green-800",
  REVIEW: "bg-amber-100 text-amber-800",
  REJECT: "bg-gray-100 text-gray-600",
};

export function DecisionBadge({ category }: { category: DecisionCategory }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${DECISION_STYLES[category]}`}>
      {category.replace("_", " ")}
    </span>
  );
}

const STATUS_STYLES: Partial<Record<ApplicationStatus, string>> = {
  preparing: "bg-blue-100 text-blue-700",
  needs_review: "bg-amber-100 text-amber-800",
  applied: "bg-indigo-100 text-indigo-700",
  recruiter_screen: "bg-purple-100 text-purple-700",
  technical_interview: "bg-purple-100 text-purple-700",
  onsite: "bg-purple-100 text-purple-700",
  offer: "bg-green-100 text-green-800",
  skipped: "bg-slate-100 text-slate-500",
  rejected: "bg-red-100 text-red-700",
  withdrawn: "bg-gray-100 text-gray-500",
  ghosted: "bg-gray-100 text-gray-500",
  expired: "bg-gray-100 text-gray-500",
};

// A few statuses read poorly as a raw enum value.
const STATUS_LABEL: Partial<Record<ApplicationStatus, string>> = {
  skipped: "skipped by agent",
  needs_review: "needs review",
};

export function StatusBadge({ status }: { status: ApplicationStatus }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${style}`}>
      {STATUS_LABEL[status] ?? status.replace(/_/g, " ")}
    </span>
  );
}

export function ScoreBar({ label, value }: { label: string; value: number }) {
  const color = value >= 85 ? "bg-green-500" : value >= 70 ? "bg-amber-500" : "bg-gray-400";
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-24 shrink-0 text-gray-500">{label}</span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-12 shrink-0 text-right tabular-nums text-gray-600">{value}%</span>
    </div>
  );
}

export function FitBadge({ value }: { value: number }) {
  const color =
    value >= 85 ? "text-green-700 bg-green-50" : value >= 70 ? "text-amber-700 bg-amber-50" : "text-gray-500 bg-gray-50";
  return (
    <span className={`rounded-md px-2 py-0.5 text-sm font-semibold tabular-nums ${color}`}>
      {value}%
    </span>
  );
}

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <p className="py-12 text-center text-sm text-gray-400">{label}</p>;
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <p className="font-medium">Couldn&apos;t reach the backend.</p>
      <p className="mt-1 text-red-600">{message}</p>
      <p className="mt-2 text-xs text-red-500">
        Start it with{" "}
        <code className="rounded bg-red-100 px-1">cd backend &amp;&amp; uv run uvicorn app.main:app --reload</code>
      </p>
    </div>
  );
}
