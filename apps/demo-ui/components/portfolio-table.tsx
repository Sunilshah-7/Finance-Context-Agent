'use client';

import type { PortfolioItem } from '../lib/types';

export function PortfolioTable({ items, onSelect }: { items: PortfolioItem[]; onSelect: (ticker: string) => void }) {
  return (
    <div className="overflow-hidden rounded border border-line">
      <table className="w-full text-left text-sm">
        <thead className="bg-panel text-xs uppercase text-slate-600">
          <tr>
            <th className="px-3 py-2">Ticker</th>
            <th className="px-3 py-2">Sector</th>
            <th className="px-3 py-2 text-right">Value</th>
            <th className="px-3 py-2 text-right">Weight</th>
            <th className="px-3 py-2 text-right">Risk</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line bg-white">
          {items.map((holding) => (
            <tr key={holding.ticker} onClick={() => onSelect(holding.ticker)} className="cursor-pointer transition hover:bg-panel">
              <td className="px-3 py-2 font-semibold">
                <span className="inline-flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${holding.drift_state === 'up' ? 'bg-signal' : holding.drift_state === 'down' ? 'bg-moss' : 'bg-slate-300'}`} />
                  {holding.ticker}
                </span>
              </td>
              <td className="px-3 py-2 text-slate-600">{holding.sector}</td>
              <td className="px-3 py-2 text-right tabular">${holding.market_value.toLocaleString()}</td>
              <td className="px-3 py-2 text-right tabular">{(holding.weight * 100).toFixed(1)}%</td>
              <td className="px-3 py-2 text-right tabular">{holding.risk_score ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
