'use client';

import { useEffect, useMemo, useState } from 'react';
import { FileDiff, FileText } from 'lucide-react';
import { AgentStepper } from '../../../components/agent-stepper';
import { AnalystMemo } from '../../../components/analyst-memo';
import { AppShell } from '../../../components/shell';
import { AuditSheet } from '../../../components/audit-sheet';
import { ChatMetrics } from '../../../components/chat-metrics';
import { DisclosureDiffViewer } from '../../../components/disclosure-diff-viewer';
import { Panel, Badge } from '../../../components/panel';
import { api } from '../../../lib/api';
import type { AgentRun, AgentStage, AnalystMemo as Memo, ChatAnswer, DiffBlock, EvidenceCitation, Metrics } from '../../../lib/types';
import { buildDiffBlocks, evidenceMap } from '../../../lib/view-models';

const question = 'What changed in supply-chain or customer concentration risk for my semiconductor holdings?';

const defaultStages: AgentStage[] = [
  { id: 'portfolio_context', label: 'Portfolio context', status: 'queued' },
  { id: 'evidence_retrieval', label: 'Evidence retrieval', status: 'queued' },
  { id: 'disclosure_diff', label: 'Disclosure diff', status: 'queued' },
  { id: 'risk_scoring', label: 'Risk scoring', status: 'queued' },
  { id: 'memo_generation', label: 'Memo generation', status: 'queued' }
];

export function AnalyticsWorkspace({ ticker }: { ticker: string }) {
  const [run, setRun] = useState<AgentRun | null>(null);
  const [diffs, setDiffs] = useState<DiffBlock[]>([]);
  const [evidence, setEvidence] = useState<EvidenceCitation[]>([]);
  const [memo, setMemo] = useState<Memo | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [chat, setChat] = useState<ChatAnswer | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<EvidenceCitation | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void Promise.all([
      api.diff(ticker).catch(() => ({ changes: [] })),
      api.evidence(),
      api.memo(),
      api.metrics()
    ]).then(([diffResponse, evidenceResponse, memoResponse, metricsResponse]) => {
      setDiffs(buildDiffBlocks(diffResponse.changes));
      setEvidence(evidenceResponse.evidence);
      setMemo(memoResponse);
      setMetrics(metricsResponse);
    });
  }, [ticker]);

  useEffect(() => {
    if (!run || run.status === 'completed' || run.status === 'failed') return;
    const timer = setInterval(() => {
      void api.getRun(run.id).then(setRun);
    }, 350);
    return () => clearInterval(timer);
  }, [run]);

  const currentEvidence = run?.retrieved_evidence?.length ? run.retrieved_evidence : evidence;
  const evidenceByID = useMemo(() => evidenceMap(currentEvidence), [currentEvidence]);
  const currentMemo = run?.memo ?? memo;
  const stages = run?.stages ?? defaultStages;

  async function startRun() {
    setLoading(true);
    try {
      const created = await api.startRun(question);
      setRun(created);
    } finally {
      setLoading(false);
    }
  }

  async function ask() {
    const answer = await api.chat(`Why is ${ticker} supply-chain risk higher this year, and does customer concentration matter?`);
    setChat(answer);
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-6 py-6">
        <header className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-cobalt">Deep-Dive Agent Workspace</p>
            <h1 className="mt-1 text-3xl font-semibold">{ticker} Disclosure Analytics</h1>
          </div>
          <div className="flex gap-2">
            <Badge tone={ticker === 'AMD' ? 'risk' : 'neutral'}>{ticker === 'AMD' ? 'active fixture evidence' : 'limited fixture evidence'}</Badge>
            <Badge tone="good">citation audit enabled</Badge>
          </div>
        </header>
        <AgentStepper stages={stages} onRun={startRun} loading={loading} />
        <section className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.95fr)]">
          <div className="space-y-5">
            <Panel title="Disclosure Diff" icon={<FileDiff size={18} />}>
              <DisclosureDiffViewer blocks={diffs} />
            </Panel>
            <Panel title="Analyst Memo" icon={<FileText size={18} />}>
              <AnalystMemo memo={currentMemo} evidenceByID={evidenceByID} onOpenCitation={setSelectedCitation} />
            </Panel>
          </div>
          <aside className="xl:sticky xl:top-5 xl:h-[calc(100vh-2.5rem)] xl:overflow-y-auto">
            <ChatMetrics chat={chat} metrics={metrics} evidenceByID={evidenceByID} onAsk={ask} onOpenCitation={setSelectedCitation} />
          </aside>
        </section>
      </div>
      <AuditSheet citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </AppShell>
  );
}
