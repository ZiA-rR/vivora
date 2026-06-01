import { Card, SectionTitle, Button, DownloadLink } from "./ui.jsx";

export default function SlidesPanel({ onGenerate, loading, slides, error, downloadHref }) {
  return (
    <Card>
      <SectionTitle hint="A polished PowerPoint deck generated from your repo.">
        Presentation Slides
      </SectionTitle>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={onGenerate} loading={loading}>
          {loading ? "Generating..." : "Generate Slides"}
        </Button>
        {slides && slides.length > 0 && downloadHref && (
          <DownloadLink href={downloadHref}>Download .pptx</DownloadLink>
        )}
      </div>
      {error && (
        <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      )}
      {slides && slides.length > 0 && (
        <div className="mt-5 grid gap-3 border-t border-white/5 pt-5 sm:grid-cols-2">
          {slides.map((s, i) => (
            <div key={i} className="rounded-xl border border-white/5 bg-surface2 p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-teal">
                Slide {i + 1}
              </div>
              <div className="mb-2 font-semibold text-ink">{s.title}</div>
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink/80">
                {(s.bullets || []).map((b, j) => (
                  <li key={j}>{b}</li>
                ))}
              </ul>
              {s.notes && (
                <p className="mt-3 border-t border-white/5 pt-2 text-xs italic text-muted">
                  Notes: {s.notes}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}