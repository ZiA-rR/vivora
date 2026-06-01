import { useState } from "react";
import { Button } from "./ui.jsx";

export default function RepoForm({ onAnalyze, loading }) {
  const [url, setUrl] = useState("");

  function submit(e) {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onAnalyze(trimmed);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <label htmlFor="repo-url" className="text-sm font-medium text-muted">
        GitHub Repository URL
      </label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input
          id="repo-url"
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/username/project-name"
          disabled={loading}
          className="flex-1 rounded-xl border border-line bg-surface2 px-4 py-2.5 text-ink placeholder:text-muted/60 focus:border-teal focus:outline-none focus-visible:ring-2 focus-visible:ring-teal/40 disabled:opacity-60"
        />
        <Button type="submit" loading={loading} className="sm:w-auto">
          {loading ? "Analyzing..." : "Analyze Repo"}
        </Button>
      </div>
    </form>
  );
}