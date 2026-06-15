import type { AgentRun, ChatAnswer, DisclosureChange, Metrics, Portfolio } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {})
    }
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  portfolio: () => request<Portfolio>('/api/demo/portfolio'),
  startRun: (question: string) =>
    request<AgentRun>('/api/agent-runs', { method: 'POST', body: JSON.stringify({ question }) }),
  getRun: (id: string) => request<AgentRun>(`/api/agent-runs/${id}`),
  diff: () =>
    request<{ changes: DisclosureChange[] }>('/api/diff?ticker=AMD&section=Item%201A&from=2022&to=2025'),
  chat: (question: string) =>
    request<ChatAnswer>('/api/chat', { method: 'POST', body: JSON.stringify({ question }) }),
  metrics: () => request<Metrics>('/api/metrics')
};
