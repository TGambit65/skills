---
name: piv-fix-review-findings
description: Triages code-review findings (file or list), fixes the chosen ones one at a time with tests, defers the rest, validates, and on a PR branch commits and pushes. Use after a review has produced issues.
argument-hint: "[code-review-file-or-issues] [scope / what to fix now vs defer]"
arguments: [review, scope]
---

# Fix Review Findings

A review produced findings — but a review is **input, not a work order.** You decide what happens to each one.

Code-review (file or description of issues): $review

Direction / scope (what to fix now vs defer): $scope

Review files live in **`.claude/code-reviews/`** — that is where `piv-review-changes` and `piv-review-pr` write
them. If `$review` is empty, use the newest file there and say which one you picked. If the Code-review is a
file, **read the entire file first** so you understand every finding before triaging. Findings marked
`Unverified` in the review are not confirmed bugs: verify them yourself before fixing, or route them to the
"needs a human look" group.

## 1. Triage first (the human's call)

Sort the findings before touching code. Honor any direction in the scope argument; if it's unclear, surface the
findings grouped and **ask** rather than fixing everything by default:

- **Fix now (this PR)** — real, in-scope, belongs with this change.
- **Defer / log as an issue** — real but later; don't bloat this PR. **Create a tracker issue** (`gh issue create`
  on GitHub, or your tracker's equivalent — or note it) instead of fixing it here.
- **Needs a human look / manual test** — anything you should inspect or test by hand before trusting it. Flag it,
  don't silently auto-fix.
- **Noise / won't-fix** — say why, then drop it.

Don't let the reviewer dictate scope — "real, but later" is a valid and common call; a clean small PR beats a
sprawling one.

## 2. Fix the "fix now" set — one at a time

For each:
1. Explain what was wrong.
2. Make the fix.
3. Create and run a test that proves it. If no test can prove it (a rename, a comment, a log line), say so
   explicitly instead of inventing one.

## 3. Validate

Run the `piv-validate` skill to finalize the fixes. Report its verdict as given (PASS / FAIL, or NOT RUN if it
could not run); don't proceed to commit on a FAIL.

## 4. If operating on a PR — commit and push

Check with `gh pr view --json number,url 2>/dev/null` (an open PR exists for the current branch). If these fixes
are on a PR branch, **commit them (use `piv-commit`) and push** so the PR reflects the fixes and `piv-review-pr`
can re-run on the updated PR. The review file itself is a local artifact — `piv-commit` will ask before staging
anything under `.claude/code-reviews/`; the default answer is no. If nothing was fixed (everything deferred),
there's nothing to push — just make sure the deferred items are logged as issues.

## Output

A short report: what was **fixed** (with its test, or why none applies), what was **deferred/logged** (with issue
refs), what needs a **manual look/test**, what was **dropped** and why — and, if on a PR, the **pushed commit** +
confirmation the PR is updated.
