---
name: worktree-merge
description: Integrates parallel worktree branches into the current branch via one throwaway integration branch, testing after each merge and running the full suite before the main line moves. Local solo use only; it bypasses PR review. Use when the user says "merge my worktrees", "integrate these branches", or invokes /worktree-merge.
argument-hint: "[branch ...]  (two or more branch names; blank = ask)"
---

# Worktree Merge

Integrate **any number** of feature branches into your working branch through a single throwaway integration
branch, so nothing lands on the main line until every branch is merged and the whole suite passes. Validation
commands are **detected from the repo**, never assumed.

## Input

`$ARGUMENTS` is the list of branches to integrate.

- **Fewer than two** → ask which branches to integrate. Don't guess.
- **Two or more** → integrate them in the given order.

## Detect the validation commands ONCE

Find the commands that prove this project works, preferring **what CI already runs**: read `.github/workflows/*`, a
`Makefile`, or the manifest's test/lint scripts, and reuse those exact commands (test runner, type checker,
linter). Do not hardcode `pytest`/`mypy`/`pyright` — use whatever this repo actually uses.

## Steps

1. **Preconditions.** Abort early with a clear message if any check fails:
   - **Main worktree, not a linked one:** `git rev-parse --git-dir` and `git rev-parse --git-common-dir` must print
     the same path (inside `worktrees/<branch>` they differ). Plain git, so it works in any shell — no bash-only
     pattern tests.
   - **Clean tree:** `git status --porcelain --untracked-files=no` must print nothing. Uncommitted changes would be
     carried into the integration branch and lost on rollback; ask the user to commit or stash first.
   - Store the current branch; it must not be one of the branches to merge.
   - Every branch in the list exists: `git rev-parse --verify <branch>`.

2. **Create one integration branch** off the current branch, named for the set (e.g. `integration-<first>`, with a
   short suffix if there are several — keep it filesystem-safe). This is where merges are tested; the main line
   stays untouched until the end. (Already on an `integration-*` branch from an interrupted run? Reuse it and
   continue with the branches not yet merged instead of creating another.)

3. **Merge each branch in order**, `--no-ff`. After **each** merge, run the detected **test** command so a break
   is localized to the branch that caused it.
   - **On conflict:** stop, name the conflicting branch and files, and give resolution steps (resolve →
     `git add` → `git commit` → re-run the skill with the remaining branches). Don't attempt automatic resolution.
   - **On test failure:** stop, report which tests failed, and give the rollback (`git checkout <original>` →
     `git branch -D <integration>`).

4. **Full validation** once all branches are merged: run the project's complete detected suite (tests + type
   checks + lint). Any failure → report it and roll back; nothing reaches the main line red.

5. **Merge the integration branch into the original branch** (`--no-ff`), then delete the integration branch
   (`git branch -d`).

6. **Offer cleanup** — ask the user (AskUserQuestion where available; otherwise a plain question, and wait for the
   answer): remove the N worktrees and delete their feature branches, or keep them. On yes, for each branch:
   `git worktree remove worktrees/<branch>` and `git branch -d <branch>` — never `-D`, and never `--force` on the
   worktree: if git refuses because a worktree is dirty or a branch is unmerged, report it and leave it.

## Report

- **Success:** the integration branch used, each branch merged (with its post-merge test result), the full
  validation result, the merge into `<original>`, and cleanup status (worktrees kept or removed, with the manual
  cleanup commands if kept).
- **Failure:** the step and branch that failed, the current branch state, and exact rollback commands
  (`git checkout <original>` → `git branch -D <integration>`), plus how to continue after fixing (re-run with the
  same branch list).

## Notes

- `--no-ff` preserves each feature branch's history.
- The integration branch is disposable — the original branch only moves after every merge and the full suite pass.
- **This skill bypasses the PR gate.** Merging locally into the current branch means nothing goes through
  `piv-create-pr` → `piv-review-pr` → human review, which is the gate the rest of the loop relies on. Use it only
  when you own the merge outright (solo project, local integration branch, throwaway experiment). On a team, open
  a PR per branch instead and let the gate run.
