'use client';

import { MessageSquare } from 'lucide-react';
import type { ChatAnswer, EvidenceCitation, Metrics } from '../lib/types';
import { CitationList } from './citation-list';
import { Badge, Panel } from './panel';

export function ChatMetrics({
  chat,
  metrics,
  evidenceByID,
  onAsk,
  onOpenCitation
}: {
  chat: ChatAnswer | null;
  metrics: Metrics | null;
  evidenceByID: Map<string, EvidenceCitation>;
  onAsk: () => void;
  onOpenCitation: (citation: EvidenceCitation) => void;
}) {
  return (
    <Panel title="Chat and Metrics" icon={<MessageSquare size={18} />}>
      <button onClick={onAsk} className="mb-4 w-full rounded bg-cobalt px-4 py-2 text-sm font-medium text-white">Ask AMD risk question</button>
      {chat ? (
        <div className="rounded border border-line bg-white p-4 text-sm">
          <p className="leading-6">{chat.answer}</p>
          <CitationList ids={chat.citations.map((c) => c.id)} evidenceByID={evidenceByID} onOpen={onOpenCitation} />
          <p className="mt-3 text-xs text-slate-500">{chat.disclaimer}</p>
        </div>
      ) : (
        <p className="rounded border border-line bg-white p-4 text-sm text-slate-600">Ask a question to inspect citation-backed chat behavior.</p>
      )}
      {metrics && (
        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <Metric label="Provider" value={metrics.provider} />
          <Metric label="Citation pass" value={`${(metrics.citation_pass_rate * 100).toFixed(0)}%`} />
          <Metric label="TTFT" value={`${metrics.time_to_first_token_ms}ms`} />
          <Metric label="Tokens/sec" value={`${metrics.tokens_per_second}`} />
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        <Badge tone="good">Go API healthy</Badge>
        <Badge tone="warn">fixture mode</Badge>
      </div>
    </Panel>
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
