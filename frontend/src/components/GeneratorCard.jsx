import { Card, SectionTitle, Button, DownloadLink } from "./ui.jsx";
import Markdown from "./Markdown.jsx";

export default function GeneratorCard({
  title,
  hint,
  buttonLabel,
  onGenerate,
  loading,
  result,
  error,
  downloadHref,
  downloadLabel,
}) {
  return (
    <Card>
      <SectionTitle hint={hint}>{title}</SectionTitle>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={onGenerate} loading={loading}>
          {loading ? "Generating..." : buttonLabel}
        </Button>
        {result && downloadHref && downloadLabel && (
          <DownloadLink href={downloadHref}>{downloadLabel}</DownloadLink>
        )}
      </div>
      {error && (
        <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      )}
      {result && (
        <div className="mt-5 border-t border-white/5 pt-5">
          <Markdown>{result}</Markdown>
        </div>
      )}
    </Card>
  );
}