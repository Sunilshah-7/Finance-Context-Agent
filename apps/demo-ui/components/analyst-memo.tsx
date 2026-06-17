'use client';

import type { AnalystMemo as Memo, EvidenceCitation } from '../lib/types';
import { CitationList } from './citation-list';
import { Badge } from './panel';

export function AnalystMemo({ memo, evidenceByID, onOpenCitation }: { memo?: Memo | null; evidenceByID: Map<string, EvidenceCitation>; onOpenCitation: (citation: EvidenceCitation) => void }) {
  if (!memo) return <p className="text-sm text-slate-600">Run the analysis to generate the citation-backed memo.</p>;
  return (
    <div className="space-y-5 text-sm">
      <p className="text-lg font-medium leading-7">{memo.executive_summary}</p>
      <div className="flex flex-wrap gap-2">
        <Badge tone="good">{Math.round(memo.confidence * 100)}% memo confidence</Badge>
        <Badge>research only</Badge>
      </div>
      <div className="grid gap-3">
        {memo.top_changes.map((change) => (
          <div key={`${change.ticker}-${change.summary}`} className="rounded border border-line bg-panel p-3">
            <p className="font-semibold">{change.ticker} · {change.section}</p>
            <p className="mt-1 leading-6 text-slate-700">{change.summary}</p>
            <CitationList ids={change.citation_ids} evidenceByID={evidenceByID} onOpen={onOpenCitation} />
          </div>
        ))}
      </div>
      <div>
        <p className="font-semibold">Watchlist questions</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
          {memo.watchlist.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>
      <p className="rounded border border-line bg-white p-3 text-xs leading-5 text-slate-600">{memo.disclaimer}</p>
    </div>
  );
}
