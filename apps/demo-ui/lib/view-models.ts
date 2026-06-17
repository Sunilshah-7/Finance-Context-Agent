import type { AgentStage, DiffBlock, DisclosureChange, EvidenceCitation, Holding, LogEvent, PortfolioItem, RiskScore } from './types';

const phraseMap: Record<string, string[]> = {
  change_amd_supply_chain_intensified: ['significant concentration', 'third-party manufacturers', 'advanced process nodes'],
  change_amd_export_controls_new: ['export restrictions', 'advanced AI accelerators', 'restricted markets']
};

export function buildPortfolioItems(holdings: Holding[], scores: RiskScore[]): PortfolioItem[] {
  return holdings.map((holding) => {
    const risk = scores.find((score) => score.ticker === holding.ticker);
    return {
      ...holding,
      risk_score: risk?.score,
      risk_delta: risk?.delta,
      drift_state: risk && risk.delta > 2 ? 'up' : risk && risk.delta < 0 ? 'down' : 'flat'
    };
  });
}

export function buildDiffBlocks(changes: DisclosureChange[]): DiffBlock[] {
  return changes.map((change) => ({
    ...change,
    risk_label: change.id.includes('export') ? 'Export Control Risk' : 'Supply Chain Risk',
    changed_phrases: phraseMap[change.id] ?? []
  }));
}

export function evidenceMap(evidence: EvidenceCitation[]): Map<string, EvidenceCitation> {
  return new Map(evidence.map((item) => [item.id, item]));
}

export function rawSectionText(evidence?: EvidenceCitation): string {
  if (!evidence) return 'Source text is unavailable for this fixture citation.';
  return [
    `${evidence.ticker} ${evidence.year} ${evidence.filing_type} ${evidence.section}`,
    '',
    'The following fixture section represents the surrounding SEC filing context used by the agent during citation validation.',
    '',
    'Risk factors in this section discuss supply chain dependency, regulatory restrictions, customer concentration, capital intensity, and other operating risks that may affect financial performance.',
    '',
    evidence.excerpt,
    '',
    'Management notes that these risks may interact with market demand, manufacturing capacity, product transitions, and compliance requirements. Analysts should verify material claims against the original EDGAR filing before using the output for research decisions.'
  ].join('\n');
}

export function stageLogs(stages: AgentStage[]): LogEvent[] {
  return stages.flatMap((stage, index) => [
    {
      id: `${stage.id}-start`,
      stage_id: stage.id,
      timestamp: `T+${(index * 340).toString().padStart(4, '0')}ms`,
      level: stage.status === 'queued' ? 'info' : 'ok',
      message: `${stage.label}: dispatch from Go runner`
    },
    {
      id: `${stage.id}-summary`,
      stage_id: stage.id,
      timestamp: `T+${(index * 340 + 210).toString().padStart(4, '0')}ms`,
      level: stage.status === 'completed' ? 'ok' : 'info',
      message: stage.summary || `${stage.label}: waiting for fixture-backed evidence state`
    }
  ]);
}

export function riskTone(score?: number): 'neutral' | 'good' | 'warn' | 'risk' {
  if (score == null) return 'neutral';
  if (score >= 55) return 'risk';
  if (score >= 35) return 'warn';
  return 'good';
}
