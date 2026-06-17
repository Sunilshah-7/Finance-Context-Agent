'use client';

import { useEffect, useState } from 'react';
import { Activity, CheckCircle2, Gauge, Server } from 'lucide-react';
import { AppShell } from '../../components/shell';
import { Badge, Panel } from '../../components/panel';
import { api } from '../../lib/api';
import type { Metrics } from '../../lib/types';

export default function SystemPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    void api.metrics().then(setMetrics);
  }, []);

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-6 py-6">
        <header className="mb-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-cobalt">Engineering Monitor</p>
          <h1 className="mt-1 text-3xl font-semibold">Go / Python Telemetry</h1>
        </header>
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <PerfCard label="TTFT" value={metrics ? `${metrics.time_to_first_token_ms}ms` : '-'} icon={<Gauge size={18} />} />
          <PerfCard label="Tokens/sec" value={metrics ? `${metrics.tokens_per_second}` : '-'} icon={<Activity size={18} />} />
          <PerfCard label="Provider" value={metrics?.provider ?? '-'} icon={<Server size={18} />} />
          <PerfCard label="Citation pass" value={metrics ? `${Math.round(metrics.citation_pass_rate * 100)}%` : '-'} icon={<CheckCircle2 size={18} />} />
        </section>
        <section className="mt-5 grid gap-5 lg:grid-cols-[1fr_0.9fr]">
          <Panel title="RAG Evaluation Feed" icon={<Activity size={18} />}>
            <div className="space-y-3">
              {[
                ['Context Faithfulness', 'pending Python eval engine', 'warn'],
                ['Answer Relevance', 'planned benchmark fixture', 'neutral'],
                ['Citation Precision', '100% fixture pass rate', 'good'],
                ['Retrieval Recall@20', 'waiting for live ingestion corpus', 'warn']
              ].map(([label, value, tone]) => (
                <div key={label} className="flex items-center justify-between rounded border border-line bg-white p-3 text-sm">
                  <span className="font-medium">{label}</span>
                  <Badge tone={tone as 'neutral' | 'good' | 'warn' | 'risk'}>{value}</Badge>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Service Boundary" icon={<Server size={18} />}>
            <div className="space-y-3 text-sm">
              <Boundary name="Go Agent API" detail="Fixture-backed orchestration, SQLite persistence, citation validation" />
              <Boundary name="Go Inference Gateway" detail="NIM chat proxy plus embedding/rerank passthrough contracts" />
              <Boundary name="Python Evaluation Engine" detail="Future offline RAG quality and citation scoring harness" />
              <Boundary name="Qdrant" detail="Collection initialized for 1024-dimensional retrieval vectors" />
            </div>
          </Panel>
        </section>
      </div>
    </AppShell>
  );
}

function PerfCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded border border-line bg-[#fdfefa] p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between text-cobalt">
        {icon}
        <Badge tone="neutral">live</Badge>
      </div>
      <p className="text-xs uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular">{value}</p>
    </div>
  );
}

function Boundary({ name, detail }: { name: string; detail: string }) {
  return (
    <div className="rounded border border-line bg-white p-3">
      <p className="font-semibold">{name}</p>
      <p className="mt-1 text-slate-600">{detail}</p>
    </div>
  );
}
