// Typed client for the JobPilot FastAPI backend.
// Override the backend URL with NEXT_PUBLIC_API_URL (defaults to localhost:8000).

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Job {
  id: number;
  external_id: string;
  company: string;
  title: string;
  location: string;
  remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  url: string;
  description: string;
  skills: string[];
  min_years_experience: number;
  education_required: string;
  date_posted: string;
  source: string;
  application_method: string;
}

export interface MatchScore {
  overall: number;
  skills: number;
  experience: number;
  education: number;
  role: number;
  location: number;
  preferences: number;
  matched_skills: string[];
  missing_skills: string[];
  gaps: string[];
  explanation: string[];
}

export type DecisionCategory = "AUTO_APPLY" | "REVIEW" | "REJECT";

export interface Decision {
  category: DecisionCategory;
  confidence: number;
  requires_human: boolean;
  reasons: string[];
}

export interface ScoredJob {
  job_id: number;
  company: string;
  title: string;
  score: MatchScore;
  decision: Decision;
}

export type ApplicationStatus =
  | "discovered" | "matched" | "preparing" | "needs_review" | "applied"
  | "recruiter_screen" | "technical_interview" | "onsite" | "offer"
  | "rejected" | "withdrawn" | "ghosted" | "expired";

export interface ActionEvent {
  at: string;
  icon: string;
  event: string;
}

export interface Application {
  id: number;
  job_id: number;
  profile_id: number;
  status: ApplicationStatus;
  fit_score: number | null;
  decision: string;
  resume_version: string;
  applied_at: string;
  answers: Record<string, string>;
  actions: ActionEvent[];
  created_at: string;
}

export interface PlannedField {
  field: string;
  value: string;
  confidence: number;
}

export interface OpenQuestion {
  question: string;
  reason: string;
  suggestion: string;
}

export interface ApplicationPlan {
  known_fields: PlannedField[];
  open_questions: OpenQuestion[];
}

export interface Profile {
  id: number;
  name: string;
  email: string;
  skills: string[];
  target_roles: string[];
  preferred_locations: string[];
  min_salary: number;
}

export interface DiscoveryResult {
  added: number;
  skipped_duplicates: number;
  per_source: Record<string, number>;
  errors: string[];
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch { /* ignore */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const jobpilot = {
  health: () => api<{ status: string }>("/health"),
  profiles: () => api<Profile[]>("/profiles"),
  jobs: () => api<Job[]>("/jobs"),
  job: (id: number) => api<Job>(`/jobs/${id}`),
  matches: (profileId: number, minScore = 0, category?: DecisionCategory) =>
    api<ScoredJob[]>(
      `/matches/${profileId}?min_score=${minScore}` +
        (category ? `&category=${category}` : "")
    ),
  applications: () => api<Application[]>("/applications"),
  application: (id: number) => api<Application>(`/applications/${id}`),
  funnel: () => api<Record<string, number>>("/applications/funnel"),
  createApplication: (profile_id: number, job_id: number) =>
    api<Application>("/applications", {
      method: "POST",
      body: JSON.stringify({ profile_id, job_id }),
    }),
  advance: (id: number) =>
    api<Application>(`/applications/${id}/advance`, { method: "POST" }),
  prepare: (id: number, questions: string[]) =>
    api<ApplicationPlan>(`/applications/${id}/prepare`, {
      method: "POST",
      body: JSON.stringify({ questions }),
    }),
  answer: (id: number, question: string, answer: string, remember = false) =>
    api<Application>(`/applications/${id}/answer`, {
      method: "POST",
      body: JSON.stringify({ question, answer, remember }),
    }),
  runDiscovery: (sources?: { type: string; token: string }[]) =>
    api<DiscoveryResult>("/discovery/run", {
      method: "POST",
      body: JSON.stringify(sources ? { sources } : {}),
    }),
  importUrl: (url: string) =>
    api<Job>("/discovery/import-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
};
