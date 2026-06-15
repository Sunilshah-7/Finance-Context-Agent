'use client';

import { useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, CheckCircle2, FileDiff, MessageSquare, Play, ShieldCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../lib/api';
import type { AgentRun, AgentStage, ChatAnswer, DisclosureChange, EvidenceCitation, Metrics, Portfolio, RiskScore } from '../lib/types';

const question = 'What changed in supply-chain or customer concentration risk for my semiconductor holdings?';

export default function Page() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [diff, setDiff] = useState<DisclosureChange[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [chat, setChat] = useState<ChatAnswer | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void Promise.all([api.portfolio(), api.diff(), api.metrics()]).then(([p, d, m]) => {
      setPortfolio(p);
      setDiff(d.changes);
      setMetrics(m);
    });
  }, []);

  useEffect(() => {
    if (!run || run.status === 'completed' || run.status === 'failed') return;
    const timer = setInterval(() => {
      void api.getRun(run.id).then(setRun);
    }, 350);
    return () => clearInterval(timer);
  }, [run]);

  const evidenceByID = useMemo(() => {
    const map = new Map<string, EvidenceCitation>();
    run?.retrieved_evidence.forEach((ev) => map.set(ev.id, ev));
    chat?.citations.forEach((ev) => map.set(ev.id, ev));
    return map;
  }, [run, chat]);

  async function start() {
    setLoading(true);
    try {
      const created = await api.startRun(question);
      setRun(created);
    } finally {
      setLoading(false);
    }
  }

  async function ask() {
    const answer = await api.chat('Why is AMD supply-chain risk higher this year, and does customer concentration matter?');
    setChat(answer);
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-line bg-[#f9faf7]">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-cobalt">FinContext Agent V2</p>
            <h1 className="mt-1 text-3xl font-semibold text-ink">Disclosure drift console</h1>
          </div>
          <div className="flex items-center gap-2 rounded border border-line bg-white px-3 py-2 text-sm text-ink shadow-soft">
            <ShieldCheck size={18} className="text-moss" />
            Go backend · Fixture-validated citations
          </div>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-5 px-6 py-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Portfolio" icon={<BarChart3 size={18} />}>
          {portfolio ? <PortfolioTable portfolio={portfolio} /> : <Skeleton />}
        </Panel>
        <Panel title="Agent run" icon={<Activity size={18} />}>
          <div className="flex items-start justify-between gap-4">
            <p className="max-w-xl text-sm text-slate-600">{question}</p>
            <button onClick={start} disabled={loading} className="flex items-center gap-2 rounded bg-ink px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              <Play size={16} />
              Analyze
            </button>
          </div>
          <div className="mt-5 space-y-3">
            {(run?.stages || defaultStages).map((stage) => (
              <div key={stage.id} className="grid grid-cols-[24px_1fr_auto] items-center gap-3 rounded border border-line bg-panel px-3 py-2">
                <CheckCircle2 size={18} className={stage.status === 'completed' ? 'text-moss' : stage.status === 'running' ? 'text-signal' : 'text-slate-300'} />
                <div>
                  <p className="text-sm font-medium">{stage.label}</p>
                  {stage.summary && <p className="text-xs text-slate-600">{stage.summary}</p>}
                </div>
                <span className="rounded border border-line bg-white px-2 py-1 text-xs tabular">{stage.status}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-6 pb-6 lg:grid-cols-2">
        <Panel title="Disclosure diff" icon={<FileDiff size={18} />}>
          {diff.map((change) => (
            <div key={change.id} className="mb-4 rounded border border-line bg-white p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold">{change.ticker} {change.section}</p>
                  <p className="text-xs text-slate-600">{change.change_type} · {change.materiality} materiality · {(change.confidence * 100).toFixed(0)}% confidence</p>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <TextBox label={`${change.from_year}`} text={change.old_text || 'No matching prior language found.'} tone="old" />
                <TextBox label={`${change.to_year}`} text={change.new_text} tone="new" />
              </div>
              <p className="mt-3 text-sm text-slate-700">{change.summary}</p>
            </div>
          ))}
        </Panel>

        <Panel title="Risk scores" icon={<BarChart3 size={18} />}>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={run?.risk_scores || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#d8ded7" />
                <XAxis dataKey="ticker" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Bar dataKey="score" fill="#315f72" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <RiskList scores={run?.risk_scores || []} />
        </Panel>
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-6 pb-6 lg:grid-cols-[1fr_0.85fr]">
        <Panel title="Analyst memo" icon={<FileDiff size={18} />}>
          {run?.memo ? (
            <div className="space-y-4 text-sm">
              <p className="text-lg font-medium leading-7">{run.memo.executive_summary}</p>
              <div className="grid gap-3 md:grid-cols-2">
                {run.memo.top_changes.map((change) => (
                  <div key={`${change.ticker}-${change.summary}`} className="rounded border border-line bg-panel p-3">
                    <p className="font-semibold">{change.ticker} · {change.section}</p>
                    <p className="mt-1 text-slate-700">{change.summary}</p>
                    <CitationList ids={change.citation_ids} evidenceByID={evidenceByID} />
                  </div>
                ))}
              </div>
              <div>
                <p className="font-semibold">Watchlist questions</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
                  {run.memo.watchlist.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </div>
              <p className="rounded border border-line bg-white p-3 text-xs text-slate-600">{run.memo.disclaimer}</p>
            </div>
          ) : (
            <p className="text-sm text-slate-600">Run the analysis to generate the citation-backed memo.</p>
          )}
        </Panel>

        <Panel title="Chat and metrics" icon={<MessageSquare size={18} />}>
          <button onClick={ask} className="mb-4 rounded bg-cobalt px-4 py-2 text-sm font-medium text-white">Ask AMD risk question</button>
          {chat && (
            <div className="rounded border border-line bg-white p-4 text-sm">
              <p>{chat.answer}</p>
              <CitationList ids={chat.citations.map((c) => c.id)} evidenceByID={evidenceByID} />
              <p className="mt-3 text-xs text-slate-500">{chat.disclaimer}</p>
            </div>
          )}
          {metrics && (
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Metric label="Provider" value={metrics.provider} />
              <Metric label="Citation pass" value={`${(metrics.citation_pass_rate * 100).toFixed(0)}%`} />
              <Metric label="TTFT" value={`${metrics.time_to_first_token_ms}ms`} />
              <Metric label="Tokens/sec" value={`${metrics.tokens_per_second}`} />
            </div>
          )}
        </Panel>
      </section>
    </main>
  );
}

const defaultStages: AgentStage[] = [
  { id: 'portfolio_context', label: 'Portfolio context', status: 'queued' },
  { id: 'evidence_retrieval', label: 'Evidence retrieval', status: 'queued' },
  { id: 'disclosure_diff', label: 'Disclosure diff', status: 'queued' },
  { id: 'risk_scoring', label: 'Risk scoring', status: 'queued' },
  { id: 'memo_generation', label: 'Memo generation', status: 'queued' }
];

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded border border-line bg-[#fdfefa] p-5 shadow-soft">
      <div className="mb-4 flex items-center gap-2 text-ink">
        {icon}
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function PortfolioTable({ portfolio }: { portfolio: Portfolio }) {
  return (
    <div className="overflow-hidden rounded border border-line">
      <table className="w-full text-left text-sm">
        <thead className="bg-panel text-xs uppercase text-slate-600">
          <tr>
            <th className="px-3 py-2">Ticker</th>
            <th className="px-3 py-2">Sector</th>
            <th className="px-3 py-2 text-right">Value</th>
            <th className="px-3 py-2 text-right">Weight</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line bg-white">
          {portfolio.holdings.map((holding) => (
            <tr key={holding.ticker}>
              <td className="px-3 py-2 font-semibold">{holding.ticker}</td>
              <td className="px-3 py-2 text-slate-600">{holding.sector}</td>
              <td className="px-3 py-2 text-right tabular">${holding.market_value.toLocaleString()}</td>
              <td className="px-3 py-2 text-right tabular">{(holding.weight * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TextBox({ label, text, tone }: { label: string; text: string; tone: 'old' | 'new' }) {
  return (
    <div className={`rounded border p-3 text-sm ${tone === 'old' ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}`}>
      <p className="mb-2 text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="leading-6">{text}</p>
    </div>
  );
}

function RiskList({ scores }: { scores: RiskScore[] }) {
  return (
    <div className="mt-4 space-y-2">
      {scores.map((score) => (
        <div key={score.ticker} className="rounded border border-line bg-white p-3 text-sm">
          <div className="flex items-center justify-between">
            <p className="font-semibold">{score.ticker}</p>
            <p className="tabular">{score.score}/100 · {score.delta >= 0 ? '+' : ''}{score.delta}</p>
          </div>
          <p className="mt-1 text-xs text-slate-600">{score.top_driver}</p>
        </div>
      ))}
    </div>
  );
}

function CitationList({ ids, evidenceByID }: { ids: string[]; evidenceByID: Map<string, EvidenceCitation> }) {
  return (
    <div className="mt-3 space-y-2">
      {ids.map((id) => {
        const ev = evidenceByID.get(id);
        return (
          <a key={id} href={ev?.source_url || '#'} target="_blank" className="block rounded border border-line bg-white p-2 text-xs text-slate-700">
            <span className="font-semibold text-cobalt">{ev?.anchor || id}</span>
            {ev?.excerpt && <span className="mt-1 block">{ev.excerpt}</span>}
          </a>
        );
      })}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-line bg-white p-3">
      <p className="text-xs uppercase text-slate-500">{label}</p>
      <p className="mt-1 font-semibold tabular">{value}</p>
    </div>
  );
}

function Skeleton() {
  return <div className="h-48 animate-pulse rounded bg-panel" />;
}
