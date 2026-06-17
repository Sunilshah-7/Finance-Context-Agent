'use client';

import type { EvidenceCitation } from '../lib/types';

export function CitationList({ ids, evidenceByID, onOpen }: { ids: string[]; evidenceByID: Map<string, EvidenceCitation>; onOpen: (citation: EvidenceCitation) => void }) {
  return (
    <div className="mt-3 space-y-2">
      {ids.map((id) => {
        const ev = evidenceByID.get(id);
        return (
          <button key={id} onClick={() => ev && onOpen(ev)} className="block w-full rounded border border-line bg-white p-2 text-left text-xs text-slate-700 transition hover:border-cobalt hover:bg-panel">
            <span className="font-semibold text-cobalt">{ev?.anchor || id}</span>
            {ev?.excerpt && <span className="mt-1 block leading-5">{ev.excerpt}</span>}
          </button>
        );
      })}
    </div>
  );
}
