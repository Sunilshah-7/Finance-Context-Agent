## Summary

Describe what changed and why it matters.

## Scope

- Target branch: `dev`
- Branch owner:
- Files or service areas touched:

## Test Plan

List exact commands and results.

```text
python -m pytest <path> -x
python -m compileall -q <path>
```

## Contract Impact

Check all that apply:

- [ ] No shared schema changes
- [ ] No API response shape changes
- [ ] No SQLite schema changes
- [ ] No Qdrant payload/vector contract changes
- [ ] No Gateway endpoint contract changes
- [ ] Contract changes are documented and coordinated

## Safety Checklist

- [ ] PR targets `dev`, not `main`
- [ ] No `.env`, secrets, database files, model caches, or Qdrant storage committed
- [ ] No buy/sell/hold recommendations added
- [ ] No live demo ingestion path added to UI
- [ ] No emoji added to docs, code, commits, or PR text
- [ ] At least one teammate review requested

## Notes For Reviewers

Call out any specific files, risks, or decisions that need careful review.
