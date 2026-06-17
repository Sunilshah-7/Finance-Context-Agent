'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, Radio, TrendingUp } from 'lucide-react';
import { RiskChart } from '../risk-chart';
import { AppShell } from '../../components/shell';
import { Panel, Badge } from '../../components/panel';
import { PortfolioTable } from '../../components/portfolio-table';
import { api } from '../../lib/api';
import type { Metrics, Portfolio, PortfolioItem, RiskScore } from '../../lib/types';
import { buildPortfolioItems, riskTone } from '../../lib/view-models';

export default function DashboardPage() {
  const router = useRouter();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [scores, setScores] = useState<RiskScore[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    void Promise.all([api.portfolio(), api.riskScores(), api.metrics()]).then(([portfolioResponse, riskResponse, metricsResponse]) => {
      setPortfolio(portfolioResponse);
      setScores(riskResponse.risk_scores);
      setMetrics(metricsResponse);
    });
  }, []);

  const items: PortfolioItem[] = useMemo(() => buildPortfolioItems(portfolio?.holdings ?? [], scores), [portfolio, scores]);
  const selectTicker = (ticker: string) => router.push(`/analytics/${ticker}`);

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-6 py-6">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-cobalt">Executive Overview</p>
            <h1 className="mt-1 text-3xl font-semibold">Portfolio & Risk Center</h1>
          </div>
          <div className="flex gap-2">
            <Badge tone="good">Go backend online</Badge>
            <Badge tone="warn">fixture evidence</Badge>
          </div>
        </header>

        <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <Panel title="Portfolio" icon={<BarChart3 size={18} />}>
            {portfolio ? <PortfolioTable items={items} onSelect={selectTicker} /> : <Skeleton />}
          </Panel>
          <Panel title="Interactive Risk Scores" icon={<TrendingUp size={18} />}>
            <RiskChart scores={scores} onSelect={selectTicker} />
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              {scores.slice(0, 4).map((score) => (
                <button key={score.ticker} onClick={() => selectTicker(score.ticker)} className="rounded border border-line bg-white p-3 text-left transition hover:border-cobalt">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold">{score.ticker}</span>
                    <Badge tone={riskTone(score.score)}>{score.score}/100</Badge>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-600">{score.top_driver}</p>
                </button>
              ))}
            </div>
          </Panel>
        </section>

        <section className="mt-5 grid gap-5 lg:grid-cols-[1fr_0.8fr]">
          <Panel title="Drift Activity Feed" icon={<Radio size={18} />}>
            <div className="space-y-3">
              {[
                'AMD: 10-K detected 89% materiality shift in supply chain language - 2 hours ago',
                'AMD: New export-control disclosure added to Item 1A - 2 hours ago',
                'NVDA: Customer concentration evidence queued for comparison - 3 hours ago',
                'MSFT: Cloud capacity language marked medium exposure - 5 hours ago'
              ].map((item) => (
                <div key={item} className="rounded border border-line bg-white p-3 text-sm text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Run Snapshot" icon={<Activity size={18} />}>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Metric label="Provider" value={metrics?.provider ?? '-'} />
              <Metric label="Citation pass" value={metrics ? `${Math.round(metrics.citation_pass_rate * 100)}%` : '-'} />
              <Metric label="TTFT" value={metrics ? `${metrics.time_to_first_token_ms}ms` : '-'} />
              <Metric label="Tokens/sec" value={metrics ? `${metrics.tokens_per_second}` : '-'} />
            </dl>
          </Panel>
        </section>
      </div>
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-line bg-white p-3">
      <dt className="text-xs uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 font-semibold tabular">{value}</dd>
    </div>
  );
}

function Skeleton() {
  return <div className="h-48 animate-pulse rounded bg-panel" />;
}
