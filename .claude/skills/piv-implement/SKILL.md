---
name: piv-implement
description: Executes a finished feature plan task-by-task, validating every step. Use to implement a plan in one pass.
argument-hint: [path-to-plan]
---

# Execute: Implement from Plan

## Plan to Execute

Read plan file: `$ARGUMENTS`

Plans written by `piv-plan-implementation` live in `.claude/plans/<plan-slug>.md`; given only a slug, look there.
`<plan-slug>` below is the plan file's basename without `.md` — it names the branch and the report.

**Non-interactive mode.** If the caller says the run is unattended (e.g. `piv-run-full-loop`), never stop to
ask: wherever this skill says STOP, write the report with `Status: PARTIAL` and the reason, and return.

## Before you start — work on a feature branch

A ticket gets built on its own branch, so it can become one PR. Ideally you're already on that branch — cut it
before planning — so a committed plan rides into the PR; a plan committed on the base branch won't be in this
branch's PR. If you're still on base, create the branch now. Detect the base branch — never hardcode `main`: `git symbolic-ref refs/remotes/origin/HEAD` (strip
`refs/remotes/origin/`); if unset, the `HEAD branch` line of `git remote show origin`; if neither answers, use
`main` and say so.

- **On the base branch, clean** → create one: `git checkout -b feature/<plan-slug>`.
- **On the base branch, and the only uncommitted changes are plan files under `.claude/plans/`** → create the
  branch the same way; the plan rides along uncommitted.
- **Already on a feature branch or in a worktree** → use it.
- **On the base branch with any other uncommitted changes** → STOP: commit or stash first.

(One branch per ticket is also what makes parallel worktrees clean later.)

## Execution Instructions

### 1. Read and Understand

- Read the ENTIRE plan carefully
- Understand all tasks and their dependencies
- Note the validation commands to run
- Review the testing strategy

### 2. Execute Tasks in Order

For EACH task in "Step by Step Tasks":

#### a. Navigate to the task
- Identify the file and action required
- Read existing related files if modifying

#### b. Implement the task
- Follow the detailed specifications exactly
- Maintain consistency with existing code patterns
- Include proper types/annotations and documentation, as the language and project allow
- Add structured logging where appropriate

#### c. Verify as you go
- After each file change, check syntax
- Ensure imports are correct
- Verify types are properly defined
- **Run the task's own `VALIDATE` command before starting the next task.** Every task in the plan carries one.
  A task is not done until its check passes — if it fails, fix it now (under the fix rules in step 4) rather than
  carrying the failure forward. The full suite still runs at step 4; this is the per-task gate that keeps step 4
  from becoming a pile-up.

### 3. Implement Testing Strategy

After completing implementation tasks:

- Create all test files specified in the plan
- Implement all test cases mentioned
- Follow the testing approach outlined
- Ensure tests cover edge cases

### 4. Run Validation Commands

Execute ALL validation commands from the plan in order, each exactly as the plan specifies.

If a command fails, fix the implementation, re-run it, and continue only when it passes — under these rules:

- **Fix the code, never the check.** Never skip, delete, weaken or mark-skip a test, loosen an assertion, or add
  a lint/type ignore to make a check pass. Changing a test is a deviation: allowed only when the plan's spec shows
  the test itself is wrong, and always recorded under *Deviations* with the reason — never quietly edited away.
- **Retry cap: 3 fix-and-rerun attempts per failing check.** After the third failure stop working on it, record
  the failing command and its last real output under *Issues encountered*, set `Status: PARTIAL`, and hand back —
  never move on as if it passed.
- **Real output only.** Every result in the report is a pasted excerpt of the command's actual output (final
  summary lines with counts), not a paraphrase. A command that could not run — missing tool, wrong directory,
  placeholder command — is `NOT RUN` with its error, never a pass.

### 5. Final Verification

Before completing, confirm each of these and record the result — tick nothing you did not check:

- [ ] All tasks from plan completed
- [ ] All tests created and passing
- [ ] All validation commands pass
- [ ] Code follows project conventions
- [ ] Documentation added/updated as needed

## Output — write an implementation report

Write a short report to `.claude/reports/<plan-slug>-report.md` (and print the summary). This is what the PR body
and the `piv-review-pr` gate read — especially the **deviations** (a documented deviation is an *intentional*
decision the reviewer should not flag). **`Status: COMPLETE` only when every required check is `PASS`**; any
required check that is `FAIL` or `NOT RUN` (missing tool, wrong directory, timeout, retry cap) makes it
`Status: PARTIAL`, with the reason under *Issues encountered*:

```markdown
# Implementation Report — <feature>

**Plan**: <path>   **Branch**: <feature/...>   **Status**: COMPLETE | PARTIAL

## Summary
{What was built, 2-4 sentences.}

## Tasks completed
- [task] → `path/to/file` (CREATE/UPDATE)

## Tests added
{Test files + cases + results.}

## Validation results
{One line per check — PASS / FAIL / NOT RUN — with the command and a pasted excerpt of its real output (counts).}

## Deviations from the plan
{What changed vs the plan and WHY — or "none". This is the reviewer's signal of intent.}

## Issues encountered
{Anything notable, including any retry cap hit with the failing command and output, or "none".}
```

### Ready for the next step
- Confirm all changes are complete and validations pass.
- Next: `piv-validate` for the full suite, `piv-commit` the work, then `piv-create-pr` to open the PR (the report
  fills the PR body), then `piv-review-pr`.

## Notes

- If you encounter issues not addressed in the plan, document them
- If you need to deviate from the plan, explain why
- Don't skip validation steps
