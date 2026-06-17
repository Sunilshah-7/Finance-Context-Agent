import { AnalyticsWorkspace } from './workspace';

export function generateStaticParams() {
  return ['AMD', 'NVDA', 'MSFT', 'JPM', 'TSLA'].map((ticker) => ({ ticker }));
}

export default async function AnalyticsPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  return <AnalyticsWorkspace ticker={ticker.toUpperCase()} />;
}
