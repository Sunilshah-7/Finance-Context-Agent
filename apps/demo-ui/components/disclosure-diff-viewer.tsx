'use client';

import { useMemo, useState } from 'react';
import type { DiffBlock } from '../lib/types';
import { Badge } from './panel';

function highlight(text: string, phrases: string[], tone: 'old' | 'new') {
  if (!text) return <span className="text-slate-500">No matching prior language found.</span>;
  const matches = phrases.filter((phrase) => text.toLowerCase().includes(phrase.toLowerCase()));
  if (matches.length === 0) return text;
  const pattern = new RegExp(`(${matches.map((phrase) => phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi');
  return text.split(pattern).map((part, index) => {
    const hit = matches.some((phrase) => phrase.toLowerCase() === part.toLowerCase());
    if (!hit) return <span key={`${part}-${index}`}>{part}</span>;
    return (
      <mark key={`${part}-${index}`} className={tone === 'old' ? 'bg-red-100 text-red-800 line-through' : 'bg-emerald-100 text-emerald-800'}>
        {part}
      </mark>
    );
  });
}

export function DisclosureDiffViewer({ blocks }: { blocks: DiffBlock[] }) {
  const [activeID, setActiveID] = useState(blocks[0]?.id ?? '');
  const [mode, setMode] = useState<'side' | 'inline'>('side');
  const active = useMemo(() => blocks.find((block) => block.id === activeID) ?? blocks[0], [activeID, blocks]);

  if (!active) {
    return <p className="text-sm text-slate-600">No disclosure changes are available for this ticker in the fixture set.</p>;
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2 overflow-x-auto">
          {blocks.map((block) => (
            <button key={block.id} onClick={() => setActiveID(block.id)} className={`rounded border px-3 py-2 text-sm font-medium transition ${active.id === block.id ? 'border-cobalt bg-cobalt text-white' : 'border-line bg-white text-slate-700'}`}>
              {block.risk_label}
            </button>
          ))}
        </div>
        <div className="flex rounded border border-line bg-white p-1 text-sm">
          <button onClick={() => setMode('side')} className={`rounded px-3 py-1 ${mode === 'side' ? 'bg-ink text-white' : 'text-slate-600'}`}>Side-by-side</button>
          <button onClick={() => setMode('inline')} className={`rounded px-3 py-1 ${mode === 'inline' ? 'bg-ink text-white' : 'text-slate-600'}`}>Inline split</button>
        </div>
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge tone="risk">{active.materiality} materiality</Badge>
        <Badge tone="warn">{Math.round(active.confidence * 100)}% confidence</Badge>
        <Badge>{active.change_type}</Badge>
      </div>
      {mode === 'side' ? (
        <div className="grid gap-3 md:grid-cols-2">
          <TextBlock label={`${active.from_year}`} tone="old">{highlight(active.old_text, active.changed_phrases, 'old')}</TextBlock>
          <TextBlock label={`${active.to_year}`} tone="new">{highlight(active.new_text, active.changed_phrases, 'new')}</TextBlock>
        </div>
      ) : (
        <div className="rounded border border-line bg-white p-4 text-sm leading-7">
          <p><span className="mr-2 font-semibold text-red-700">-</span>{highlight(active.old_text, active.changed_phrases, 'old')}</p>
          <p className="mt-3"><span className="mr-2 font-semibold text-emerald-700">+</span>{highlight(active.new_text, active.changed_phrases, 'new')}</p>
        </div>
      )}
      <p className="mt-4 text-sm leading-6 text-slate-700">{active.summary}</p>
    </div>
  );
}

function TextBlock({ label, tone, children }: { label: string; tone: 'old' | 'new'; children: React.ReactNode }) {
  return (
    <div className={`rounded border p-4 text-sm leading-7 ${tone === 'old' ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'}`}>
      <p className="mb-2 text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p>{children}</p>
    </div>
  );
}
