import { Card } from "./ui.jsx";
import Markdown from "./Markdown.jsx";

export default function ProfilePanel({ profile }) {
  return (
    <Card>
      <details>
        <summary className="cursor-pointer text-lg font-semibold tracking-tight text-ink">
          AI Project Profile
          <span className="ml-2 text-sm font-normal text-muted">
            (used as context for every feature below)
          </span>
        </summary>
        <div className="mt-4">
          <Markdown>{profile}</Markdown>
        </div>
      </details>
    </Card>
  );
}