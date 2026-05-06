# apps/web

Next.js frontend deployed to Cloudflare Pages.

## Build Responsibilities

- Portfolio upload UI.
- Dashboard with holdings, sector exposure, and risk deltas.
- Filing explorer with source citations.
- Disclosure diff view.
- Analyst memo view.
- Benchmark panel for AMD GPU metrics.

## Suggested Stack

- Next.js App Router.
- TypeScript.
- Tailwind CSS.
- shadcn/ui.
- Recharts.
- TanStack Query.

## Key Screens

```text
app/
  page.tsx
  portfolio/page.tsx
  documents/page.tsx
  documents/[documentId]/page.tsx
  diff/[ticker]/page.tsx
  memo/[jobId]/page.tsx
  api/health/route.ts
components/
  portfolio-upload.tsx
  exposure-heatmap.tsx
  risk-score-card.tsx
  citation-card.tsx
  disclosure-diff.tsx
  memo-viewer.tsx
```

