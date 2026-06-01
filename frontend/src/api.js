// ─────────────────────────────────────────────
// API client — every call to the FastAPI backend goes through here.
// One place to change the base URL, one place that handles errors.
// ─────────────────────────────────────────────

// In dev the backend runs at http://localhost:8000. Override at build time
// with a VITE_API_BASE env var (e.g. for a deployed backend).
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Shared POST helper: sends JSON, parses JSON, and turns a non-2xx
// response into a thrown Error carrying the backend's `detail` message
// (the FastAPI HTTPException text) so the UI can show something useful.
async function post(path, body) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      "Could not reach the Vivora API. Is the backend running on " +
        `${API_BASE}? (start it with: uvicorn main:app --reload --port 8000)`
    );
  }

  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status}).`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* response had no JSON body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  base: API_BASE,

  analyze: (repoUrl) => post("/api/analyze", { repo_url: repoUrl }),

  chat: (sessionId, question, history) =>
    post("/api/chat", { session_id: sessionId, question, history }),

  viva: (sessionId) => post("/api/viva", { session_id: sessionId }),
  weakAreas: (sessionId) => post("/api/weak-areas", { session_id: sessionId }),
  report: (sessionId) => post("/api/report", { session_id: sessionId }),
  slides: (sessionId) => post("/api/slides", { session_id: sessionId }),

  // Downloads are plain GET URLs — the backend sets Content-Disposition:
  // attachment, so an <a href> triggers a file download directly.
  downloadVivaUrl: (id) => `${API_BASE}/api/download/viva/${id}`,
  downloadReportUrl: (id) => `${API_BASE}/api/download/report/${id}`,
  downloadSlidesUrl: (id) => `${API_BASE}/api/download/slides/${id}`,
};
