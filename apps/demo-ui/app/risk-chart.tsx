'use client';

import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { RiskScore } from '../lib/types';

type ChartClickEvent = {
  activePayload?: Array<{ payload?: RiskScore }>;
};

export function RiskChart({ scores, onSelect }: { scores: RiskScore[]; onSelect?: (ticker: string) => void }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  function handleClick(event: ChartClickEvent) {
    const ticker = event.activePayload?.[0]?.payload?.ticker;
    if (ticker) onSelect?.(ticker);
  }

  if (!mounted) return <div className="h-64 min-h-64 rounded bg-panel" />;

  return (
    <div className="h-64 min-h-64 min-w-0">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart data={scores} onClick={(event) => handleClick(event as ChartClickEvent)}>
          <CartesianGrid strokeDasharray="3 3" stroke="#d8ded7" />
          <XAxis dataKey="ticker" />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Bar dataKey="score" fill="#315f72" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
