const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Partner = {
  id: number;
  name: string;
  email: string;
  role: string;
};

export type QueueCompany = {
  company_id: number;
  name: string;
  domain?: string | null;
  description?: string | null;
  base_score?: number | null;
  overlay_score?: number | null;
  rubric_base_version?: string | null;
  why_note?: string | null;
  matched_thesis_config_ids: number[];
  on_my_watchlist: boolean;
};

export type QueueResponse = {
  partner: Partner;
  items: QueueCompany[];
  total: number;
};

export type ThesisConfig = {
  id: number;
  partner_id: number | null;
  name: string;
  keywords: string[];
  exa_queries: string[];
  github_topics: string[];
  is_shared: boolean;
  is_active: boolean;
  created_at: string;
};

export type WatchlistEntry = {
  id: number;
  partner_id: number;
  company_id: number;
  note?: string | null;
  created_at: string;
  company_name?: string | null;
};

export type RubricOverlay = {
  id: number;
  partner_id: number;
  version: string;
  base_rubric_version: string;
  weight_adjustments: Record<string, number>;
  added_dimensions: Array<Record<string, unknown>>;
  is_active: boolean;
  created_at: string;
};

export type RubricBase = {
  id: number;
  version: string;
  yaml_content: string;
  is_active: boolean;
  changelog?: string | null;
  created_at: string;
};

export type Feedback = {
  id: number;
  partner_id: number;
  partner_name?: string | null;
  company_id: number;
  thumbs: number;
  comment?: string | null;
  created_at: string;
};

export type CompanyDetail = {
  id: number;
  name: string;
  domain?: string | null;
  description?: string | null;
  affinity_org_id?: number | null;
  base_score?: number | null;
  overlay_score?: number | null;
  rubric_base_version?: string | null;
  subscores: Record<string, unknown>;
  evidence: Record<string, unknown>;
  why_note?: string | null;
  partner_lines: string[];
  watchlisted_by: string[];
  signals: Array<{
    id: number;
    source: string;
    title?: string | null;
    summary?: string | null;
    url?: string | null;
    matched_thesis_config_ids: number[];
  }>;
  feedback: Feedback[];
  on_my_watchlist: boolean;
};

async function api<T>(
  path: string,
  token: string | null,
  init?: RequestInit
): Promise<T> {
  const headers: HeadersInit = {
    Accept: "application/json",
    ...(init?.headers || {}),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }
  if (init?.body && !(headers as Record<string, string>)["Content-Type"]) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${init?.method || "GET"} ${path} failed (${res.status}): ${body}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

export const fetchMyQueue = (token: string | null) =>
  api<QueueResponse>("/api/queue/mine", token);

export const fetchTeamQueue = (token: string | null) =>
  api<QueueResponse>("/api/queue/team", token);

export const fetchCompany = (token: string | null, id: number) =>
  api<CompanyDetail>(`/api/companies/${id}`, token);

export const createCompany = (
  token: string | null,
  body: { name: string; domain?: string; description?: string }
) => api<CompanyDetail>("/api/companies", token, { method: "POST", body: JSON.stringify(body) });

export const postFeedback = (
  token: string | null,
  companyId: number,
  body: { thumbs: number; comment?: string }
) =>
  api<Feedback>(`/api/companies/${companyId}/feedback`, token, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const fetchMyThesis = (token: string | null) =>
  api<ThesisConfig[]>("/api/me/thesis", token);

export const fetchSharedThesis = (token: string | null) =>
  api<ThesisConfig[]>("/api/thesis/shared", token);

export const createThesis = (
  token: string | null,
  body: Partial<ThesisConfig> & { name: string }
) =>
  api<ThesisConfig>("/api/me/thesis", token, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const updateThesis = (
  token: string | null,
  id: number,
  body: Partial<ThesisConfig>
) =>
  api<ThesisConfig>(`/api/me/thesis/${id}`, token, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteThesis = (token: string | null, id: number) =>
  api<void>(`/api/me/thesis/${id}`, token, { method: "DELETE" });

export const fetchWatchlist = (token: string | null) =>
  api<WatchlistEntry[]>("/api/me/watchlist", token);

export const addWatchlist = (
  token: string | null,
  body: { company_id: number; note?: string }
) =>
  api<WatchlistEntry>("/api/me/watchlist", token, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const removeWatchlist = (token: string | null, id: number) =>
  api<void>(`/api/me/watchlist/${id}`, token, { method: "DELETE" });

export const fetchOverlay = (token: string | null) =>
  api<RubricOverlay | null>("/api/me/rubric-overlay", token);

export const saveOverlay = (
  token: string | null,
  body: {
    version?: string;
    base_rubric_version?: string;
    weight_adjustments: Record<string, number>;
    added_dimensions?: Array<Record<string, unknown>>;
  }
) =>
  api<RubricOverlay>("/api/me/rubric-overlay", token, {
    method: "PUT",
    body: JSON.stringify(body),
  });

export const fetchBaseRubrics = (token: string | null) =>
  api<RubricBase[]>("/api/rubric/base", token);

export const createBaseRubric = (
  token: string | null,
  body: { version: string; yaml_content: string; changelog?: string; activate?: boolean }
) =>
  api<RubricBase>("/api/rubric/base", token, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const runPipeline = (token: string | null) =>
  api<{ report: Record<string, unknown> }>("/api/pipeline/run", token, { method: "POST" });
