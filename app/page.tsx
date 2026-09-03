"use client";

import { useEffect, useState } from "react";
import type { AnalysisResult, BusinessIdea } from "@/lib/schema";

const HISTORY_KEY = "site-analysis-history";
const HISTORY_LIMIT = 20;

interface HistoryEntry {
  id: string;
  savedAt: number;
  result: AnalysisResult;
}

function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(entries: HistoryEntry[]) {
  try {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch {
    // 저장 공간이 부족하거나 접근 불가한 경우 무시
  }
}

const difficultyLabel: Record<BusinessIdea["difficulty"], string> = {
  low: "낮음",
  medium: "보통",
  high: "높음",
};

const difficultyColor: Record<BusinessIdea["difficulty"], string> = {
  low: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  high: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
};

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
      {children}
    </span>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {title}
      </h3>
      {children}
    </div>
  );
}

function IdeaCard({ idea }: { idea: BusinessIdea }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          {idea.title}
        </h4>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${difficultyColor[idea.difficulty]}`}
        >
          난이도 {difficultyLabel[idea.difficulty]}
        </span>
      </div>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{idea.summary}</p>

      <div className="space-y-2 rounded-lg bg-zinc-50 p-3 text-sm dark:bg-zinc-800/50">
        <p>
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            역설계 인사이트:{" "}
          </span>
          <span className="text-zinc-600 dark:text-zinc-400">
            {idea.reverseEngineeringInsight}
          </span>
        </p>
        <p>
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            타겟 시장:{" "}
          </span>
          <span className="text-zinc-600 dark:text-zinc-400">{idea.targetMarket}</span>
        </p>
        <p>
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            차별화:{" "}
          </span>
          <span className="text-zinc-600 dark:text-zinc-400">
            {idea.differentiation}
          </span>
        </p>
        <p>
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            수익 모델:{" "}
          </span>
          <span className="text-zinc-600 dark:text-zinc-400">
            {idea.monetizationModel}
          </span>
        </p>
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
          첫 실행 단계
        </p>
        <ol className="list-inside list-decimal space-y-1 text-sm text-zinc-600 dark:text-zinc-400">
          {idea.firstSteps.map((step, i) => (
            <li key={i}>{step}</li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function ResultView({ result }: { result: AnalysisResult }) {
  const { analysis, businessIdeas, url, fetchedTitle } = result;
  return (
    <div className="space-y-8">
      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
              {analysis.siteName}
            </h2>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-zinc-500 hover:underline dark:text-zinc-400"
            >
              {fetchedTitle ?? url}
            </a>
          </div>
          <Chip>{analysis.category}</Chip>
        </div>

        <p className="mb-6 text-base text-zinc-700 dark:text-zinc-300">
          {analysis.oneLineSummary}
        </p>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Section title="핵심 기능">
            <ul className="list-inside list-disc space-y-1 text-sm text-zinc-600 dark:text-zinc-400">
              {analysis.coreFeatures.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </Section>

          <Section title="타겟 사용자">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {analysis.targetAudience}
            </p>
          </Section>

          <Section title="핵심 가치 제안">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {analysis.valueProposition}
            </p>
          </Section>

          <Section title="비즈니스 모델">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {analysis.businessModel}
            </p>
          </Section>

          <Section title="수익화 방식">
            <div className="flex flex-wrap gap-2">
              {analysis.monetizationMethods.map((m, i) => (
                <Chip key={i}>{m}</Chip>
              ))}
            </div>
          </Section>

          {analysis.techSignals.length > 0 && (
            <Section title="기술 신호">
              <div className="flex flex-wrap gap-2">
                {analysis.techSignals.map((t, i) => (
                  <Chip key={i}>{t}</Chip>
                ))}
              </div>
            </Section>
          )}

          <Section title="강점">
            <ul className="list-inside list-disc space-y-1 text-sm text-emerald-700 dark:text-emerald-400">
              {analysis.strengths.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </Section>

          <Section title="약점 / 개선 여지">
            <ul className="list-inside list-disc space-y-1 text-sm text-rose-700 dark:text-rose-400">
              {analysis.weaknesses.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </Section>
        </div>
      </div>

      <div>
        <h3 className="mb-4 text-lg font-bold text-zinc-900 dark:text-zinc-50">
          역설계 기반 신사업 아이디어
        </h3>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {businessIdeas.map((idea, i) => (
            <IdeaCard key={i} idea={idea} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reading localStorage, unavailable during SSR
    setHistory(loadHistory());
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();

      if (!res.ok) {
        setError(data.error ?? "알 수 없는 오류가 발생했습니다.");
        return;
      }

      const analysisResult = data as AnalysisResult;
      setResult(analysisResult);

      const entry: HistoryEntry = {
        id: `${Date.now()}`,
        savedAt: Date.now(),
        result: analysisResult,
      };
      const next = [entry, ...history].slice(0, HISTORY_LIMIT);
      setHistory(next);
      saveHistory(next);
    } catch {
      setError("네트워크 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function handleHistoryClick(entry: HistoryEntry) {
    setResult(entry.result);
    setUrl(entry.result.url);
    setError(null);
  }

  function handleClearHistory() {
    setHistory([]);
    saveHistory([]);
  }

  return (
    <div className="min-h-full bg-zinc-50 dark:bg-black">
      <div className="mx-auto flex max-w-6xl gap-8 px-6 py-12">
        <main className="flex-1 space-y-8">
          <header className="space-y-2">
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              웹사이트 분석 & 역설계
            </h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              분석하고 싶은 웹사이트 주소를 입력하면, 핵심 기능과 특징을
              분석하고 이를 역설계하여 새로운 사업 아이디어를 제안합니다.
            </p>
          </header>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="예: https://example.com"
              className="flex-1 rounded-lg border border-zinc-300 bg-white px-4 py-2.5 text-sm text-zinc-900 outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="shrink-0 rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-50 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              {loading ? "분석 중..." : "분석하기"}
            </button>
          </form>

          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
              {error}
            </div>
          )}

          {loading && (
            <div className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-white px-4 py-4 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-600 dark:border-zinc-700 dark:border-t-zinc-300" />
              사이트를 수집하고 Claude로 분석하는 중입니다. 잠시만 기다려주세요...
            </div>
          )}

          {result && !loading && <ResultView result={result} />}

          {!result && !loading && !error && (
            <div className="rounded-lg border border-dashed border-zinc-300 px-4 py-10 text-center text-sm text-zinc-400 dark:border-zinc-700">
              분석할 웹사이트 주소를 입력해보세요.
            </div>
          )}
        </main>

        <aside className="hidden w-64 shrink-0 space-y-3 lg:block">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
              최근 분석
            </h2>
            {history.length > 0 && (
              <button
                onClick={handleClearHistory}
                className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                초기화
              </button>
            )}
          </div>
          {history.length === 0 && (
            <p className="text-xs text-zinc-400">아직 분석 기록이 없습니다.</p>
          )}
          <ul className="space-y-2">
            {history.map((entry) => (
              <li key={entry.id}>
                <button
                  onClick={() => handleHistoryClick(entry)}
                  className="w-full rounded-lg border border-zinc-200 bg-white p-3 text-left text-xs hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-600"
                >
                  <p className="truncate font-medium text-zinc-800 dark:text-zinc-200">
                    {entry.result.analysis.siteName}
                  </p>
                  <p className="truncate text-zinc-400">{entry.result.url}</p>
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );
}
