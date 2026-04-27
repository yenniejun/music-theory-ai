---
name: incremental-commit
description: Commit the current working tree as a focused, well-scoped commit and push it to origin. Use after any meaningful unit of work.
---

# incremental-commit

Standing preference for this project: **commit and push incrementally** — small, focused commits pushed to origin as work progresses, not one giant push at the end.

## When to invoke

Invoke this skill (or just follow it inline) at every natural boundary:
- A backend scaffold lands and imports cleanly
- A feature is implemented + its tests pass
- A bug is fixed
- A docs / README update is done
- A frontend route or component is wired up end-to-end

Don't invoke it mid-flight: if tests are red or the change is half-finished, fix first.

## What it does

1. `git status` — check what's changed; stop if nothing.
2. `git diff` (and `git diff --staged`) — read the actual changes.
3. `git log -5 --oneline` — match the existing commit-message style.
4. Stage the relevant files **by name** (never `git add -A` / `git add .` — too easy to slurp `.env` or `node_modules`).
5. Commit with a tight, conventional-style subject (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`) describing *why*, not *what*.
6. `git push` — to the current upstream. If the branch has no upstream yet, surface that and ask before pushing.

## Guardrails

- Never `--no-verify`, never `--amend` a pushed commit, never force-push without an explicit ask.
- Never commit `.env`, credentials, or anything matching `*.key` / `*.pem`.
- Don't push to `main` from someone else's PR branch.
- If a hook fails, fix the underlying issue and commit fresh — don't bypass.

## Example commit messages

```
feat(omr): add Oemer adapter as default OMR provider

backend: 19 analyzer unit tests covering RN, tritone, tension scoring

frontend: wire 6 toggleable SVG overlay layers + tooltip
```
