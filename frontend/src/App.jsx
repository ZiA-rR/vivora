import { useState } from "react";
import { api } from "./api.js";
import Hero from "./components/Hero.jsx";
import RepoForm from "./components/RepoForm.jsx";
import Overview from "./components/Overview.jsx";
import ProfilePanel from "./components/ProfilePanel.jsx";
import GeneratorCard from "./components/GeneratorCard.jsx";
import SlidesPanel from "./components/SlidesPanel.jsx";
import Chat from "./components/Chat.jsx";

const EMPTY = { loading: false, data: null, error: null };

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState(null);

  const [viva, setViva] = useState(EMPTY);
  const [weak, setWeak] = useState(EMPTY);
  const [report, setReport] = useState(EMPTY);
  const [slides, setSlides] = useState(EMPTY);

  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);

  async function handleAnalyze(url) {
    setAnalyzing(true);
    setAnalyzeError(null);
    setAnalysis(null);
    setSessionId(null);
    setViva(EMPTY);
    setWeak(EMPTY);
    setReport(EMPTY);
    setSlides(EMPTY);
    setChatMessages([]);

    try {
      const data = await api.analyze(url);
      setSessionId(data.session_id);
      setAnalysis(data);
    } catch (e) {
      setAnalyzeError(e.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function run(setter, fn) {
    setter((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fn();
      setter({ loading: false, data, error: null });
    } catch (e) {
      setter({ loading: false, data: null, error: e.message });
    }
  }

  async function handleChat(question) {
    const history = chatMessages.map((m) => ({ role: m.role, content: m.content }));
    setChatMessages((m) => [...m, { role: "user", content: question }]);
    setChatLoading(true);

    try {
      const res = await api.chat(sessionId, question, history);
      setChatMessages((m) => [
        ...m,
        { role: "assistant", content: res.answer, sources: res.sources },
      ]);
    } catch (e) {
      setChatMessages((m) => [...m, { role: "assistant", content: `Warning: ${e.message}` }]);
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <Hero />
      <div className="mt-6 space-y-6">
        <div className="rounded-2xl border border-white/5 bg-surface p-5 sm:p-6">
          <RepoForm onAnalyze={handleAnalyze} loading={analyzing} />
          {analyzeError && (
            <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {analyzeError}
            </p>
          )}
        </div>

        {analysis && (
          <>
            <Overview analysis={analysis} />
            <ProfilePanel profile={analysis.profile} />

            <GeneratorCard
              title="Viva Preparation"
              hint="12 likely viva questions with suggested answers, specific to your repo."
              buttonLabel="Generate Viva Q&A"
              onGenerate={() => run(setViva, () => api.viva(sessionId))}
              loading={viva.loading}
              result={viva.data?.markdown}
              error={viva.error}
              downloadHref={api.downloadVivaUrl(sessionId)}
              downloadLabel="Download PDF"
            />

            <GeneratorCard
              title="Weak Area Analysis"
              hint="What's missing or weak in the project, and how to defend it."
              buttonLabel="Analyze Weak Areas"
              onGenerate={() => run(setWeak, () => api.weakAreas(sessionId))}
              loading={weak.loading}
              result={weak.data?.markdown}
              error={weak.error}
            />

            <GeneratorCard
              title="Project Report"
              hint="A full academic report with 11 sections. Takes about a minute."
              buttonLabel="Generate Full Report"
              onGenerate={() => run(setReport, () => api.report(sessionId))}
              loading={report.loading}
              result={report.data?.markdown}
              error={report.error}
              downloadHref={api.downloadReportUrl(sessionId)}
              downloadLabel="Download Word (.docx)"
            />

            <SlidesPanel
              onGenerate={() => run(setSlides, () => api.slides(sessionId))}
              loading={slides.loading}
              slides={slides.data?.slides}
              error={slides.error}
              downloadHref={api.downloadSlidesUrl(sessionId)}
            />

            <Chat messages={chatMessages} onSend={handleChat} loading={chatLoading} />
          </>
        )}
      </div>
    </div>
  );
}