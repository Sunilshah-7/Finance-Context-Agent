'use client';

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { RiskScore } from '../lib/types';

export function RiskChart({ scores }: { scores: RiskScore[] }) {
  return (
    <div className="h-64 min-h-64 min-w-0">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart data={scores}>
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
