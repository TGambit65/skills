---
name: piv-implement-issue
description: Implements a GitHub issue fix from its piv-investigate-issue RCA: drift check, fix branch, regression test, validation, PASS/FAIL report. Use after the RCA exists to "fix issue N" or "implement the fix".
argument-hint: [github-issue-id]
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(git rev-parse:*), Bash(git branch --show-current:*), Bash(git symbolic-ref:*), Bash(git worktree list:*), Bash(git checkout -b:*), Bash(git switch -c:*), Bash(gh issue view:*), Bash(ruff:*), Bash(mypy:*), Bash(pytest:*), Bash(npm:*), Bash(bun:*), Bash(uv run:*)
---

# Implement Issue Fix: GitHub Issue #$ARGUMENTS

## Prerequisites

**This skill implements fixes for GitHub issues based on RCA documents:**
- Working in a local Git repository with GitHub origin
- RCA document exists at `docs/issues/issue-$ARGUMENTS.md`
- GitHub CLI installed and authenticated (optional, for context and status updates)

`allowed-tools` pre-approves read-only git, branch creation, `gh issue view`, and the common Python/JS runners
(ruff, mypy, pytest, npm, bun, uv). Other stacks' lint/type/test commands prompt the first time each runs — add them
to your project's permission settings before running this skill unattended. Anything with external side effects (`gh issue comment`/`edit`, pushes) prompts.

## RCA Document to Reference

Read RCA: `docs/issues/issue-$ARGUMENTS.md`

**Optional - View GitHub issue for context:**
```bash
gh issue view $ARGUMENTS --comments
```

## Implementation Instructions

### 1. Read and Understand RCA

- Read the ENTIRE RCA document thoroughly
- Review the GitHub issue details (issue #$ARGUMENTS)
- Understand the root cause
- Review the proposed fix strategy
- Note all files to modify
- Review testing requirements — its "Validation Commands" are what Step 5 runs

### 2. Verify Current State — and check for drift

Before making changes:
- **Confirm the issue still exists:** re-run the RCA's Reproduction command. If it no longer reproduces, stop and
  report — it may already be fixed, or the RCA's reproduction may be wrong. Don't implement a fix you can't see failing.
- **Drift check:** read each file the RCA names and compare against the RCA's "Code Location" snippets / line refs
  (`git diff --stat <investigated-at-commit>..HEAD -- <files>` shows what moved). If the code has **changed
  materially** since the RCA, **stop** — surface the drift and suggest re-running `piv-investigate-issue` for
  issue #$ARGUMENTS rather than implementing a stale plan.
- Confirm the proposed fix still addresses the root cause — don't silently deviate.

### 2b. Get on the right branch

Check `git status -sb`, `git branch --show-current`, `git worktree list`, then:

- **In a worktree?** Use it (it was created for this work).
- **On the base branch, clean tree?** Create a fix branch — `git checkout -b fix/issue-$ARGUMENTS-<slug>`. Detect the
  base branch — never hardcode `main`: `git symbolic-ref refs/remotes/origin/HEAD` (strip `refs/remotes/origin/`);
  if unset, the `HEAD branch` line of `git remote show origin`; if neither answers, ask (interactive) or use `main`
  and say so (non-interactive).
- **On the base branch, and the only uncommitted change is the RCA under `docs/issues/`?** Create the fix branch
  the same way; the RCA rides along and is committed with the fix.
- **Already on a feature/fix branch?** Use it (warn if its name doesn't reference #$ARGUMENTS).
- **Dirty tree on the base branch?** Stop — ask the user to commit or stash first. Never stash, reset, or check out
  over their changes yourself.

### 3. Implement the Fix

Following the "Proposed Fix" section of the RCA:

**For each file to modify:**

#### a. Read the existing file
- Understand current implementation
- Locate the specific code mentioned in RCA

#### b. Make the fix
- Implement the change as described in RCA
- Follow the fix strategy exactly
- Maintain code style and conventions
- Add comments if the fix is non-obvious

#### c. Handle related changes
- Update any related code affected by the fix
- Ensure consistency across the codebase
- Update imports if needed

**Stay on plan:** implement what the RCA specifies — don't refactor unrelated code or add unplanned
"improvements." If you must deviate, note what changed and why, and surface it in the report (and the PR).

### 4. Add/Update Tests

Following the "Testing Requirements" from RCA:

**Create test cases for:**
1. Verify the fix resolves the issue
2. Test edge cases related to the bug
3. Ensure no regression in related functionality
4. Test any new code paths introduced

**Test file location:**
- Follow the project's test structure and framework — co-located `*.test.ts`, a `tests/` tree mirroring `src/`, `_test.go` siblings, whatever it already does
- Use descriptive test names that reference the issue, e.g. `test_issue_$ARGUMENTS_<what>` or `it("fixes #$ARGUMENTS: <what>")`

**Test implementation** (any language): Arrange the exact scenario from the RCA's Reproduction · Act — execute the code
that previously failed · Assert the RCA's Expected Behavior.

**Prove it is a regression test:** where practical, write the fix-verification test before Step 3's change, run it, and
confirm it fails for the reason the RCA gives; then fix and confirm it passes. If you wrote it after the fix, say so in
the report — its red state is unverified.

### 5. Run Validation

Run the RCA's "Validation Commands" verbatim (lint, type check, tests — from the right working directory). If the RCA
has none, use the project's own (`package.json` scripts, `pyproject.toml`, `Makefile`, CI config); never invent one.

**If validation fails:**
- Fix the cause in the code under test, then re-run.
- **Never make a check pass by weakening it:** no deleting, skipping, `xfail`-ing or commenting out tests, no loosened
  assertions, no lint/type ignore pragmas, no lowered thresholds — unless the RCA itself says the test is wrong, and
  then record it under Deviations.
- **Retry cap: 3 fix-and-rerun attempts per failing check.** Fix the code, never the check. After the third
  failure stop working on it, record the failing command and its last real output under Validation Results, set
  `Status: PARTIAL`, and hand back — never move on as if it passed.
- Don't proceed while anything is failing.

### 6. Verify Fix

**Manually verify:**
- Follow reproduction steps from RCA — the same command as Step 2 — and capture its output
- Confirm issue no longer occurs
- Test edge cases
- Check for unintended side effects

### 7. Update Documentation

If needed:
- Update code comments
- Update API documentation
- Update README if user-facing
- Add notes about the fix

## Output Report

Write this report to `.claude/reports/issue-$ARGUMENTS-report.md` (and print it). `piv-create-pr` and
`piv-review-pr` read it for the PR body and the Deviations signal.

Every status below is **PASS / FAIL / NOT RUN**. PASS and FAIL need the command and its trimmed actual output beneath;
NOT RUN needs a reason. Never write a status you did not observe.

### Fix Implementation Summary

**GitHub Issue #$ARGUMENTS**: [Brief title]

**Issue URL**: [GitHub issue URL]

**Root Cause** (from RCA):
[One-line summary of root cause]

### Changes Made

**Files Modified:**
1. **[file-path]**
   - Change: [What was changed]
   - Lines: [Line numbers]

2. **[file-path]**
   - Change: [What was changed]
   - Lines: [Line numbers]

### Tests Added

**Test Files Created/Modified:**
1. **[test-file-path]**
   - Test cases: [List test functions added]

**Test Coverage:**
- Fix verification test: [name] — [PASS/FAIL/NOT RUN] — failed before the fix: [yes / Unverified]
- Edge case tests: [names] — [PASS/FAIL/NOT RUN]
- Regression prevention tests: [names] — [PASS/FAIL/NOT RUN]

### Validation Results

```
# Lint — [PASS/FAIL/NOT RUN]
$ [exact command]
[actual output, trimmed]

# Type check — [PASS/FAIL/NOT RUN]
$ [exact command]
[actual output, trimmed]

# Tests — [PASS/FAIL/NOT RUN]
$ [exact command]
[actual output, trimmed — keep the summary line with counts]
```

### Verification

**Manual Testing:**
- Reproduction steps re-run — [PASS (symptom gone) / FAIL / NOT RUN]: [command + what you observed]
- Edge cases — [PASS/FAIL/NOT RUN]: [which]
- Side effects checked — [PASS/FAIL/NOT RUN]: [what you checked]

### Deviations from the RCA

[None — implemented as specified | List each deviation from the RCA + why]

### Files Summary

**Total Changes** (from `git diff --stat`):
- X files modified
- Y files created (tests)
- Z lines added
- W lines removed

### Status

**Status: COMPLETE | PARTIAL** — COMPLETE only if every status above is PASS (NOT RUN only with a stated reason).
COMPLETE → ready for the `piv-commit` skill. PARTIAL → state what fails and what the user must decide.

**Suggested commit message:**
```
fix(scope): resolve GitHub issue #$ARGUMENTS - [brief description]

[Summary of what was fixed and how]

Fixes #$ARGUMENTS
```

**Note:** `Fixes #$ARGUMENTS` in the commit message closes the GitHub issue automatically when merged to the default branch — so don't close the issue from this skill; nothing is merged yet.

### Optional: Update GitHub Issue (after `piv-commit`, with the user's go-ahead)

**Add implementation comment to issue:**
```bash
gh issue comment $ARGUMENTS --body "Fix implemented in commit <hash from piv-commit> on branch <branch>. Ready for review."
```

**Update issue labels (if the project uses them):**
```bash
gh issue edit $ARGUMENTS --add-label "fixed" --remove-label "bug"
```

## Notes

- If the RCA document is missing or incomplete, request it be created first with the `piv-investigate-issue` skill for issue #$ARGUMENTS
- If you discover the RCA analysis was incorrect, document findings and update the RCA
- If additional issues are found during implementation, note them for separate GitHub issues and RCAs
- Follow project coding standards exactly
- Ensure all validation passes before declaring READY — a FAIL or an unexplained NOT RUN means PARTIAL
- The commit message `Fixes #$ARGUMENTS` will link the commit to the GitHub issue
