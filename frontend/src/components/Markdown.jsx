import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders LLM markdown (viva questions, weak-area report, full report).
// `prose-invert` from @tailwindcss/typography gives readable dark-mode
// styling; the overrides tune colors to the brand palette.
export default function Markdown({ children }) {
  return (
    <div
      className="prose prose-invert max-w-none
        prose-headings:text-ink prose-h2:text-teal-soft prose-h3:text-teal
        prose-strong:text-ink prose-a:text-teal prose-code:text-teal-soft
        prose-blockquote:border-l-teal prose-blockquote:text-muted
        prose-li:marker:text-teal text-ink/90"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
