# Risk Scoring

## Score Meaning

| Score | Meaning |
| --- | --- |
| 0-20 | Low observed document risk |
| 21-40 | Moderate risk, routine monitoring |
| 41-60 | Elevated risk, analyst review recommended |
| 61-80 | High risk, material exposure review recommended |
| 81-100 | Critical risk, urgent research review recommended |

## Inputs

- Latest filing evidence.
- Prior filing evidence.
- Disclosure change classifications.
- Extracted financial metrics.
- Portfolio holding weight.
- Sector concentration.
- Recency of disclosure.
- Model confidence and citation quality.

## Categories

```yaml
financial_health:
  signals: [cash decline, debt increase, negative operating cash flow, impairment]
liquidity:
  signals: [going concern, covenant, refinancing, maturity wall]
revenue_concentration:
  signals: [major customer, channel partner, geographic concentration]
margin_pressure:
  signals: [gross margin decline, pricing pressure, inventory write-down]
regulatory_legal:
  signals: [investigation, litigation, export controls, compliance]
supply_chain:
  signals: [single source, manufacturing constraint, logistics disruption]
guidance_credibility:
  signals: [guidance withdrawal, repeated misses, demand uncertainty]
disclosure_volatility:
  signals: [new risk factor, intensified language, removed mitigation]
```

## Formula

```text
raw_category_score =
  evidence_severity * 0.35
  + disclosure_delta * 0.25
  + metric_delta * 0.20
  + recency * 0.10
  + citation_confidence * 0.10

holding_adjusted_score =
  raw_category_score
  * (1 + min(portfolio_weight, 0.25))
  * sector_concentration_modifier
```

Clamp all scores to 0-100.

## Severity Levels

| Level | Numeric | Description |
| --- | ---: | --- |
| none | 0 | no signal |
| low | 20 | routine or boilerplate risk |
| medium | 45 | meaningful but not urgent |
| high | 70 | material risk with clear evidence |
| critical | 90 | severe risk with direct financial or legal impact |

## Output Schema

```json
{
  "ticker": "AMD",
  "overall_score": 58,
  "score_delta": 12,
  "confidence": 0.82,
  "drivers": [
    {
      "category": "supply_chain",
      "score": 70,
      "summary": "New or intensified supply-chain dependency language.",
      "citations": ["chunk_123", "chunk_456"]
    }
  ],
  "portfolio_impact": {
    "holding_weight": 0.18,
    "sector_weight": 0.34,
    "exposure_level": "high"
  }
}
```

## Calibration

For the hackathon demo:

- Manually label 20-50 disclosure changes.
- Compare model severity against labels.
- Adjust weights until scores align with analyst intuition.
- Show calibration table in the demo.

For production:

- Backtest against historical filing changes and subsequent volatility/drawdown.
- Separate predictive risk from explanatory document risk.
- Keep score explanations auditable.

