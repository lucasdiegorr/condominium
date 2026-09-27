## Context

The repository follows the OpenSpec workflow with git discipline directives recorded in AGENTS.md. See proposal.md - Why for the motivation. This change introduces the pre-commit framework as the single enforcement point for the local git directives.

## Goals / Non-Goals

**Goals:**
- Block commits on protected branches (`master`/`main`) locally.
- Validate OpenSpec artifacts on every commit, not just when working on a change.
- Provide code-quality gating that activates automatically once backend/frontend code exists.
- One install command per developer; zero server-side dependency.

**Non-Goals:**
- Server-side protection (branch protection rules on a remote host) — not configurable until a remote exists.
- Frontend lint/format hooks — deferred until the React scaffold exists.
- Hard enforcement of the English-only docs / i18n directives — language rules are review-based (automated detection would false-positive on quoted domain terms).

## Decisions

### D1: pre-commit framework over native git hooks / husky
Chosen because it is environment-managed (installs and pins hook tool versions per repo), supports both Python and, later, JS tooling, and runs the same command locally and in CI. Native `.git/hooks` scripts are not versioned and need manual Python/pip bootstrap; husky would only cover the JS side. The project already lives in a Python + React ecosystem, so a single framework covers both.

### D2: `no-commit-to-branch` as the master guard
The `pre-commit-hooks` `no-commit-to-branch` hook fails a commit when the current branch is `master` or `main`. This is a soft, per-developer guard — `--no-verify` bypasses it — so the AGENTS.md rule remains the contract and server-side branch protection should complement it later.

### D3: `openspec validate` as an always-on local hook
A local hook (`language: system`, `pass_filenames: false`, `always_run: true`) runs `openspec validate --all --no-interactive` on every commit. This catches broken artifacts (invalid specs, missing requirements) even when the author is committing unrelated files, and directly supports the "every feature starts as an OpenSpec change" rule.

### D4: Defer frontend hooks
There is no `package.json`/`package-lock.json` yet; adding eslint/prettier hooks now would fail on the empty repo. They are added in the `condominium-management` change alongside the React scaffold (task 1.5).

## Risks / Trade-offs

- [Hooks add friction to every commit] → Run them in CI too so behavior is consistent; keep the set lean (essential hygiene + lint/format + validate).
- [`no-commit-to-branch` can be bypassed with `--no-verify`] → Documented as a soft guard; server-side branch protection is the real enforcement when a remote exists.
- [Pin versions go stale] → `pre-commit autoupdate` at install and periodically.
- [`ruff` with `--fix` modifies files mid-commit] → Standard pre-commit behaviour; files are re-staged before commit, as with any auto-fixing hook.

## Migration Plan

- Right after merging this change, each developer runs `pre-commit install` once (hook lives in `.git/hooks/`, not in the repo).
- Rollback: remove `.pre-commit-config.yaml` and run `pre-commit uninstall` — no repo state beyond the config file; no data or DB changes.

## Open Questions

None — deferred items (frontend hooks, CI integration, branch protection) are explicitly out of scope and can be added in later changes.
