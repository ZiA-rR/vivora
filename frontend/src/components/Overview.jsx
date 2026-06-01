import { Card, SectionTitle } from "./ui.jsx";

function Metric({ label, value }) {
  return (
    <div className="rounded-xl border border-white/5 bg-surface2 px-4 py-3">
      <div className="text-2xl font-bold text-ink">{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
    </div>
  );
}

function Chips({ items }) {
  if (!items || items.length === 0) {
    return <span className="text-sm text-muted">None detected</span>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((x) => (
        <span
          key={x}
          className="rounded-full border border-teal/30 bg-teal/10 px-3 py-1 text-sm text-teal-soft"
        >
          {x}
        </span>
      ))}
    </div>
  );
}

function Health({ ok, warn, label }) {
  const color = ok ? "text-emerald-400" : warn ? "text-amber-400" : "text-red-400";
  const mark = ok ? "OK" : warn ? "!" : "X";

  return (
    <div className={`flex items-center gap-2 text-sm ${color}`}>
      <span className="font-bold">{mark}</span>
      {label}
    </div>
  );
}

export default function Overview({ analysis }) {
  const tech = analysis.tech_stack;

  return (
    <Card>
      <SectionTitle hint="Detected automatically from the repository contents.">
        Repo Overview
      </SectionTitle>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Metric label="Files" value={analysis.file_count} />
        <Metric label="Languages" value={tech.languages.length} />
        <Metric label="Frameworks" value={tech.frameworks.length} />
      </div>
      <div className="mt-5 space-y-4">
        <div>
          <div className="mb-2 text-sm font-medium text-muted">Languages</div>
          <Chips items={tech.languages} />
        </div>
        <div>
          <div className="mb-2 text-sm font-medium text-muted">Frameworks / Libraries</div>
          <Chips items={tech.frameworks} />
        </div>
        {tech.databases && tech.databases.length > 0 && (
          <div>
            <div className="mb-2 text-sm font-medium text-muted">Databases</div>
            <Chips items={tech.databases} />
          </div>
        )}
        <div>
          <div className="mb-2 text-sm font-medium text-muted">Health Check</div>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <Health ok={tech.has_readme} label="README" />
            <Health ok={tech.has_requirements} label="Dependencies" />
            <Health ok={tech.has_tests} warn label="Tests" />
          </div>
        </div>
      </div>
      <details className="mt-5">
        <summary className="cursor-pointer text-sm text-teal hover:underline">
          Show {analysis.files.length} analyzed files
        </summary>
        <ul className="mt-3 max-h-60 overflow-auto rounded-xl border border-white/5 bg-surface2 p-3">
          {analysis.files.map((f) => (
            <li key={f} className="py-0.5 font-mono text-xs text-muted">
              {f}
            </li>
          ))}
        </ul>
      </details>
    </Card>
  );
}