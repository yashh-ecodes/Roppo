const BASE = import.meta.env.VITE_API_URL || "/api";
const TOKEN_KEY = "roppo_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(status, detail) {
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message ||
          (Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : "Something went wrong");
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, { method = "GET", body, form, raw } = {}) {
  const headers = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });
  if (res.status === 401 && token) {
    tokenStore.clear();
    window.dispatchEvent(new Event("roppo:logout"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (raw) return res;
  if (res.status === 204) return null;
  return res.json();
}

function qs(params) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "" || v === false) return;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, x));
    else sp.append(k, v);
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  register: (body) => request("/auth/register", { method: "POST", body }),
  login: (body) => request("/auth/login", { method: "POST", body }),
  me: () => request("/auth/me"),
  meta: () => request("/meta"),

  dashboard: () => request("/dashboard"),

  uploadResume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/resumes", { method: "POST", form });
  },
  resumes: () => request("/resumes"),
  deleteResume: (id) => request(`/resumes/${id}`, { method: "DELETE" }),
  version: (rid, vid) => request(`/resumes/${rid}/versions/${vid}`),
  restoreVersion: (rid, vid) => request(`/resumes/${rid}/versions/${vid}/restore`, { method: "POST" }),
  exportVersion: (rid, vid, format) => request(`/resumes/${rid}/versions/${vid}/export?format=${format}`, { raw: true }),

  profile: () => request("/profile"),
  saveProfile: (data, confirmed = true) => request("/profile", { method: "PUT", body: { data, confirmed } }),

  runAnalysis: (body) => request("/analysis", { method: "POST", body }),
  latestAnalysis: () => request("/analysis/latest"),
  analyses: () => request("/analysis"),
  analysis: (id) => request(`/analysis/${id}`),
  updateSuggestion: (id, body) => request(`/suggestions/${id}`, { method: "PATCH", body }),
  applyChanges: (id, label) => request(`/analysis/${id}/apply`, { method: "POST", body: { label } }),
  keywords: (body) => request("/analysis/keywords", { method: "POST", body }),

  jobsMeta: () => request("/jobs/meta"),
  jobs: (params) => request(`/jobs${qs(params)}`),
  job: (id, explain = false) => request(`/jobs/${id}${explain ? "?explain=true" : ""}`),
  addJob: (body) => request("/jobs", { method: "POST", body }),
  syncJobs: () => request("/jobs/sync", { method: "POST" }),
  savedJobs: () => request("/saved-jobs"),
  saveJob: (job_id) => request("/saved-jobs", { method: "POST", body: { job_id } }),
  updateSaved: (id, body) => request(`/saved-jobs/${id}`, { method: "PATCH", body }),
  deleteSaved: (id) => request(`/saved-jobs/${id}`, { method: "DELETE" }),

  opportunities: (interests) => request(`/opportunities${qs({ interests })}`),
  opportunityJob: (id, skill) => request(`/opportunities/jobs/${id}${qs({ skill })}`),

  roadmapRoles: () => request("/roadmaps/roles"),
  roadmaps: () => request("/roadmaps"),
  createRoadmap: (target_role) => request("/roadmaps", { method: "POST", body: { target_role } }),
  updateStep: (id, body) => request(`/roadmaps/steps/${id}`, { method: "PATCH", body }),
  stepToProfile: (id) => request(`/roadmaps/steps/${id}/add-to-profile`, { method: "POST" }),
  deleteRoadmap: (id) => request(`/roadmaps/${id}`, { method: "DELETE" }),

  settings: () => request("/settings"),
  saveSettings: (body) => request("/settings", { method: "PUT", body }),
  exportData: () => request("/settings/export"),
  deleteHistory: () => request("/settings/analysis-history", { method: "DELETE" }),
  deleteAccount: (password) => request("/settings/delete-account", { method: "POST", body: { password } }),
};

export async function downloadResponse(res, fallbackName) {
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") || "";
  const name = /filename="([^"]+)"/.exec(cd)?.[1] || fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadJson(data, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
