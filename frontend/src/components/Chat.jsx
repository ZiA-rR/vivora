import { useState } from "react";
import { Card, SectionTitle, Button } from "./ui.jsx";
import Markdown from "./Markdown.jsx";

export default function Chat({ messages, onSend, loading }) {
  const [q, setQ] = useState("");

  function submit(e) {
    e.preventDefault();
    const t = q.trim();
    if (t && !loading) {
      onSend(t);
      setQ("");
    }
  }

  return (
    <Card>
      <SectionTitle hint="Ask anything about the repo. Answers cite the files used.">
        Ask Anything About This Repo
      </SectionTitle>
      <div className="space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-muted">No messages yet. Try "What does this project do?"</p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-xl p-4 ${
              m.role === "user" ? "bg-surface2" : "border border-white/5 bg-surface2/50"
            }`}
          >
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-teal">
              {m.role === "user" ? "You" : "Vivora"}
            </div>
            {m.role === "user" ? (
              <p className="text-ink/90">{m.content}</p>
            ) : (
              <>
                <Markdown>{m.content}</Markdown>
                {m.sources && m.sources.length > 0 && (
                  <p className="mt-2 text-xs text-muted">Sources: {m.sources.join(", ")}</p>
                )}
              </>
            )}
          </div>
        ))}
        {loading && <p className="text-sm text-muted">Vivora is thinking...</p>}
      </div>
      <form onSubmit={submit} className="mt-4 flex flex-col gap-3 sm:flex-row">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask something about the repo..."
          disabled={loading}
          className="flex-1 rounded-xl border border-line bg-surface2 px-4 py-2.5 text-ink placeholder:text-muted/60 focus:border-teal focus:outline-none disabled:opacity-60"
        />
        <Button type="submit" loading={loading}>Send</Button>
      </form>
    </Card>
  );
}