'use client';

import { Terminal, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { AgentStage, LogEvent } from '../lib/types';
import { stageLogs } from '../lib/view-models';
import { Badge } from './panel';

export function AgentStepper({ stages, onRun, loading }: { stages: AgentStage[]; onRun: () => void; loading: boolean }) {
  const [selected, setSelected] = useState<AgentStage | null>(null);
  const logs = useMemo(() => stageLogs(stages), [stages]);
  const completed = stages.length > 0 && stages.every((stage) => stage.status === 'completed');
  const selectedLogs = logs.filter((log) => log.stage_id === selected?.id);

  return (
    <>
      <section className="rounded border border-line bg-[#fdfefa] p-4 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-cobalt">Agent run</p>
            <h2 className="mt-1 text-lg font-semibold">Evidence workflow</h2>
          </div>
          <button onClick={onRun} disabled={loading} className="rounded bg-ink px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            {loading ? 'Running' : 'Run agent'}
          </button>
        </div>
        <div className={`mt-4 grid gap-2 transition-all ${completed ? 'grid-cols-2 md:grid-cols-5' : 'grid-cols-1 md:grid-cols-5'}`}>
          {stages.map((stage, index) => (
            <button key={stage.id} onClick={() => setSelected(stage)} className={`rounded border p-3 text-left transition hover:border-cobalt ${stage.status === 'completed' ? 'border-emerald-200 bg-emerald-50' : stage.status === 'running' ? 'border-amber-200 bg-amber-50' : 'border-line bg-white'}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-slate-500">0{index + 1}</span>
                <Badge tone={stage.status === 'completed' ? 'good' : stage.status === 'running' ? 'warn' : 'neutral'}>{stage.status}</Badge>
              </div>
              <p className={`${completed ? 'mt-2 text-xs' : 'mt-3 text-sm'} font-semibold`}>{stage.label}</p>
              {!completed && stage.summary && <p className="mt-2 text-xs leading-5 text-slate-600">{stage.summary}</p>}
            </button>
          ))}
        </div>
      </section>
      <div className={`fixed inset-x-0 bottom-0 z-40 transform border-t border-line bg-[#111827] text-slate-100 shadow-soft transition-transform duration-300 ${selected ? 'translate-y-0' : 'translate-y-full'}`}>
        <div className="mx-auto max-w-6xl px-5 py-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal size={17} className="text-emerald-300" />
              <p className="font-semibold">{selected?.label || 'Logs'}</p>
            </div>
            <button onClick={() => setSelected(null)} className="rounded border border-slate-700 p-2" aria-label="Close logs">
              <X size={16} />
            </button>
          </div>
          <pre className="max-h-64 overflow-y-auto rounded border border-slate-800 bg-black p-4 text-xs leading-6">
            {selectedLogs.map((log: LogEvent) => `[${log.timestamp}] ${log.level.toUpperCase()} ${log.message}`).join('\n') || 'No logs emitted yet.'}
          </pre>
        </div>
      </div>
    </>
  );
}
