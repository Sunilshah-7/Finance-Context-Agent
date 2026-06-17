'use client';

import { X } from 'lucide-react';
import type { EvidenceCitation } from '../lib/types';
import { rawSectionText } from '../lib/view-models';
import { Badge } from './panel';

export function AuditSheet({ citation, onClose }: { citation: EvidenceCitation | null; onClose: () => void }) {
  const open = Boolean(citation);
  return (
    <div className={`fixed inset-0 z-50 transition ${open ? 'pointer-events-auto' : 'pointer-events-none'}`}>
      <div className={`absolute inset-0 bg-ink/35 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`} onClick={onClose} />
      <aside className={`absolute right-0 top-0 h-full w-full max-w-5xl transform border-l border-line bg-[#f9faf7] shadow-soft transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-cobalt">Audit trail</p>
              <h2 className="mt-1 text-xl font-semibold">{citation?.anchor || 'Citation'}</h2>
            </div>
            <button onClick={onClose} className="rounded border border-line bg-white p-2" aria-label="Close audit trail">
              <X size={18} />
            </button>
          </div>
          <div className="grid min-h-0 flex-1 gap-0 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="min-h-0 overflow-y-auto border-r border-line bg-white p-5">
              <p className="mb-3 text-sm font-semibold">Raw SEC Section Context</p>
              <pre className="whitespace-pre-wrap rounded border border-line bg-panel p-4 text-sm leading-6 text-slate-700">{rawSectionText(citation || undefined)}</pre>
            </div>
            <div className="min-h-0 overflow-y-auto p-5">
              <div className="mb-4 flex items-center gap-2">
                <Badge tone="good">fixture verified</Badge>
                <Badge>{citation?.ticker || '-'}</Badge>
              </div>
              <p className="text-sm font-semibold">Agent Extract</p>
              <p className="mt-3 rounded border border-line bg-white p-4 text-sm leading-6 text-slate-700">{citation?.excerpt || 'No extract selected.'}</p>
              <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded border border-line bg-white p-3">
                  <dt className="text-xs uppercase text-slate-500">Filing</dt>
                  <dd className="mt-1 font-semibold">{citation ? `${citation.year} ${citation.filing_type}` : '-'}</dd>
                </div>
                <div className="rounded border border-line bg-white p-3">
                  <dt className="text-xs uppercase text-slate-500">Section</dt>
                  <dd className="mt-1 font-semibold">{citation?.section || '-'}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
