# GitHub CI And Branch Rules

This document explains the lightweight CI checks and the recommended GitHub
branch rules for FinContext Agent. The goal is to protect `dev` and `main`
without blocking hackathon velocity or requiring live hosted inference in CI.

## What CI Checks

The CI workflow in `.github/workflows/ci.yml` runs on pull requests to `dev`
and `main`, plus pushes to `dev` and `main`.

It has two jobs.

### Python Tests

This job uses Python 3.12 because the shared schema package requires Python
3.12 or newer.

It runs:

```bash
python -m pip install -e packages/schemas
python -m pip install -r services/ingestion-worker/requirements.txt
python -m pip install -r services/inference-gateway/requirements.txt
python -m pytest services/ingestion-worker/tests -x
python -m pytest services/inference-gateway/tests -x
python -m pytest infra/tests -x
python -m compileall -q packages/schemas/python services/ingestion-worker services/inference-gateway infra
```

It also runs eval tests when `packages/evals/tests` exists on a branch.

### Repository Policy

This job blocks common accidental commits:

- `.env` files;
- SQLite database files;
- `__pycache__` and `.pyc` files;
- `.pytest_cache`;
- Qdrant storage;
- model cache directories;
- emoji added in changed tracked text files.

## What CI Does Not Check

CI does not call NVIDIA NIM. It does not run live EDGAR ingestion, live Qdrant
integration, or HuggingFace Spaces deployment.

Those checks belong in the backend smoke playbook and validation CLI because
they require secrets, network access, and live services.

## Recommended Branch Rules

After the CI PR merges and the workflow has run at least once, configure branch
protection in GitHub repository settings.

For `dev`:

- Require a pull request before merging.
- Require at least one approval.
- Dismiss stale approvals when new commits are pushed.
- Require status checks to pass before merging.
- Require these checks:
  - `Python Tests`
  - `Repository Policy`
- Require branches to be up to date before merging if GitHub offers the option.
- Do not allow force pushes.
- Do not allow deletions.

For `main`:

- Require a pull request before merging.
- Require at least one approval.
- Require status checks to pass before merging.
- Require these checks:
  - `Python Tests`
  - `Repository Policy`
- Do not allow force pushes.
- Do not allow deletions.

Do not enable a rule that forces every branch name to use one exact prefix.
The project intentionally uses multiple prefixes: `feat/`, `fix/`, `docs/`,
`infra/`, `test/`, and `eval/`.

## Review Order During Hackathon

Use CI as the first filter, then review the code:

1. CI must pass.
2. Confirm the PR targets `dev`.
3. Confirm the changed files match the branch owner.
4. Review contract changes if the PR touches schemas, API payloads, SQLite, or
   Qdrant payloads.
5. Merge only after at least one teammate approval.

CI is not a replacement for review. It catches basic breakage so reviewers can
spend their time on design, contracts, and demo risk.
