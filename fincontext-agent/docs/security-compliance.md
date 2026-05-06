# Security and Compliance

## Important Product Boundary

FinContext Agent is a financial research assistant. It should not present itself as a registered investment adviser, broker, or automated trading system.

Recommended disclaimer:

```text
FinContext provides AI-assisted research summaries based on source documents and portfolio data. It is not financial, legal, tax, or investment advice. Verify outputs against original filings and consult qualified professionals before making investment decisions.
```

## Data Classes

- Public filings: low sensitivity, but preserve source integrity.
- Uploaded portfolios: sensitive personal financial data.
- User questions: potentially sensitive.
- Generated memos: sensitive if tied to holdings.
- API keys and tokens: secret.

## Controls

- Encrypt data in transit with HTTPS.
- Use Cloudflare access controls and Worker secrets.
- Store portfolios and generated reports in private R2 buckets.
- Use signed URLs with short expiration.
- Separate tenants by user and portfolio ID.
- Log metadata, not raw portfolio contents, unless necessary for debugging.
- Add deletion flow for user portfolios and generated artifacts.
- Add audit records for document ingestion and generated outputs.

## Prompt Injection Defense

Financial documents can contain arbitrary text. Treat filings and transcripts as untrusted context.

Rules:

- System prompts must state that document text is evidence, not instruction.
- Never execute links, scripts, or instructions found inside filings.
- Citation Verifier must confirm claims against retrieved text.
- Tool calls should be deterministic and allowlisted.

## Compliance Guardrails

Block or rewrite outputs that:

- Tell the user to buy, sell, short, or hold a security.
- Promise returns.
- Claim certainty about future price movement.
- Hide uncertainty.
- Lack citations for factual claims.
- Use confidential data across tenants.

Allowed phrasing:

- "This may increase portfolio exposure to..."
- "An analyst should review..."
- "The filing indicates..."
- "The risk score increased because..."

Avoid:

- "You should sell..."
- "This stock will fall..."
- "Guaranteed upside..."

## Auditability

Every memo should store:

- model name.
- prompt template version.
- retrieval query IDs.
- chunk IDs.
- citation anchors.
- risk scoring version.
- job ID.
- timestamp.

