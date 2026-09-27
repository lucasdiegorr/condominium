## Why

Without git hooks, the AGENTS.md directives (never commit to master, only valid OpenSpec changes, code quality) rely on manual discipline and drift easily. This change installs the pre-commit framework, with hooks that block commits on master/main and automatically validate the repository on every commit.

## What Changes

- Add `.pre-commit-config.yaml` with:
  - `no-commit-to-branch`: blocks commits on `master`/`main`, enforcing the "never commit to master" directive (local guard; can be complemented later with server-side branch protection).
  - Repository hygiene hooks: trailing-whitespace, end-of-file-fixer, check-yaml, check-json, check-added-large-files, check-merge-conflict, check-case-conflict, detect-private-key, debug-statements, mixed-line-ending.
  - Python quality hooks via `ruff-pre-commit`: `ruff` (lint with `--fix`) and `ruff-format` — harmless on the current empty repo until the backend scaffold exists.
  - Local hook `openspec validate --all --no-interactive` running on every commit (`always_run`), enforcing the "every feature starts as a valid OpenSpec change" directive.
- Install the git hook via `pre-commit install`.
- Pin hook revisions with `pre-commit autoupdate` at install time.
- Frontend hooks (eslint/prettier) are explicitly deferred until the React scaffold exists (task 1.5 of `condominium-management`), avoiding broken commits with no `package.json`.
- Add a note to AGENTS.md: run `pre-commit install` after cloning.

No spec-level behavior change: this is developer tooling only (`skip_specs: true`).

## Capabilities

### New Capabilities

None — tooling change only (`skip_specs: true`).

### Modified Capabilities

None.

## Impact

- New file `.pre-commit-config.yaml`.
- Per-developer local git hook via `pre-commit install`; CI can later run `pre-commit run --all-files`.
- AGENTS.md: one-line developer convention ("run `pre-commit install` after cloning").
