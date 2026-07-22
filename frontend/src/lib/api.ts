const API_URL = typeof window === "undefined"
  ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  : ""; // browser: same-origin via Next.js rewrite → cookies work

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return res.json() as Promise<T>;
}

export type HealthResponse = {
  status: string;
  app: string;
  llm_provider: string;
  storage_backend: string;
  disclaimer: string;
};

export type ResumeUploadResponse = {
  id: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  extracted_text_preview: string;
  created_at: string;
};

export type JobDescriptionResponse = {
  id: string;
  title?: string | null;
  raw_text: string;
  created_at: string;
};

export type Recommendation = {
  id: string;
  priority: "critical" | "important" | "optional";
  section: string;
  message: string;
};

export type CategoryScores = {
  content_quality: number;
  job_relevance: number;
  achievements: number;
  skills_match: number;
  readability: number;
  ats_compatibility: number;
  overall_score: number;
  job_match_score: number;
  ats_score: number;
};

export type AnalysisResponse = {
  id: string;
  status: string;
  resume_id: string;
  job_description_id?: string | null;
  target_role?: string | null;
  experience_level?: string | null;
  model_name?: string | null;
  scores?: CategoryScores | null;
  strengths: string[];
  weaknesses: string[];
  missing_keywords: string[];
  matched_skills: string[];
  recommendations: Recommendation[];
  disclaimer: string;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
};

export type AnalysisSummary = {
  id: string;
  status: string;
  target_role?: string | null;
  overall_score?: number | null;
  job_match_score?: number | null;
  ats_score?: number | null;
  created_at: string;
};

export type RewriteResponse = {
  id: string;
  analysis_run_id: string;
  section_type: string;
  original_text: string;
  rewritten_text: string;
  instruction?: string | null;
  created_at: string;
};

export type ExportResponse = {
  analysis_id: string;
  markdown: string;
  disclaimer: string;
};

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ResumeUploadResponse>("/api/resumes/upload", { method: "POST", body: form });
  },
  deleteResume: (id: string) =>
    request<{ message: string }>(`/api/resumes/${id}`, { method: "DELETE" }),
  createJobDescription: (raw_text: string, title?: string) =>
    request<JobDescriptionResponse>("/api/job-descriptions", {
      method: "POST",
      body: JSON.stringify({ raw_text, title }),
    }),
  createAnalysis: (payload: {
    resume_id: string;
    job_description_id?: string;
    target_role?: string;
    experience_level?: string;
  }) =>
    request<AnalysisResponse>("/api/analyses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getAnalysis: (id: string) => request<AnalysisResponse>(`/api/analyses/${id}`),
  listAnalyses: () => request<AnalysisSummary[]>("/api/analyses"),
  exportAnalysis: (id: string) => request<ExportResponse>(`/api/analyses/${id}/export`),
  rewrite: (payload: {
    analysis_id: string;
    section_type: string;
    original_text: string;
    instruction?: string;
  }) =>
    request<RewriteResponse>("/api/rewrites", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export { API_URL };
