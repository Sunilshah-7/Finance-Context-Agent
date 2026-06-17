import type { ReactNode } from 'react';

export function Panel({ title, icon, action, children, className = '' }: { title: string; icon?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded border border-line bg-[#fdfefa] p-5 shadow-soft ${className}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2 text-ink">
          {icon}
          <h2 className="truncate text-lg font-semibold">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'risk' }) {
  const tones = {
    neutral: 'border-line bg-white text-slate-700',
    good: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    warn: 'border-amber-200 bg-amber-50 text-amber-800',
    risk: 'border-red-200 bg-red-50 text-red-800'
  };
  return <span className={`rounded border px-2 py-1 text-xs font-medium tabular ${tones[tone]}`}>{children}</span>;
}
