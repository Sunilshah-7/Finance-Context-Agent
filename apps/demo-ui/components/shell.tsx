'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, BarChart3, FileSearch, LayoutDashboard } from 'lucide-react';
import type { ReactNode } from 'react';

const nav = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/analytics/AMD', label: 'Analytics', icon: FileSearch },
  { href: '/system', label: 'System', icon: Activity }
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen bg-[#eef1ed] text-ink">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-line bg-[#f9faf7] px-4 py-5 lg:block">
        <div className="mb-8 px-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-cobalt">FinContext Agent</p>
          <h1 className="mt-2 text-2xl font-semibold leading-tight">Disclosure Drift</h1>
        </div>
        <nav className="space-y-1">
          {nav.map((item) => {
            const active = pathname === item.href || (item.href.startsWith('/analytics') && pathname.startsWith('/analytics'));
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className={`flex items-center gap-3 rounded px-3 py-2 text-sm font-medium transition ${active ? 'bg-ink text-white' : 'text-slate-700 hover:bg-white'}`}>
                <Icon size={17} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-5 left-4 right-4 rounded border border-line bg-white p-3 text-xs text-slate-600">
          <div className="mb-2 flex items-center gap-2 font-semibold text-ink">
            <BarChart3 size={15} className="text-moss" />
            Go core pipeline
          </div>
          Fixture mode with citation validation enabled.
        </div>
      </aside>
      <main className="lg:pl-64">
        <div className="border-b border-line bg-[#f9faf7] px-5 py-4 lg:hidden">
          <p className="text-sm font-semibold text-cobalt">FinContext Agent</p>
          <div className="mt-3 flex gap-2 overflow-x-auto">
            {nav.map((item) => (
              <Link key={item.href} href={item.href} className="rounded border border-line bg-white px-3 py-2 text-sm">
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}
