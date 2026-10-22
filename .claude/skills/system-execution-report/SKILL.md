---
name: system-execution-report
description: Reflects on a just-finished implementation: what diverged from the plan and why, and what was skipped. Extends piv-implement's report if one exists, otherwise writes its own. Use as the input to system-evolution-review.
---

# Execution Report

Review and deeply analyze the implementation you just completed. This is the **standalone / retrospective**
variant of the report: `piv-implement` already writes a short implementation report at the end of its run, so
the first job here is to find out whether one exists and build on it rather than write a second one.

## Context

You have just finished implementing a feature. Before moving on, reflect on:

- What you implemented
- How it aligns with the plan
- What challenges you encountered
- What diverged and why

## Where the report goes

1. Look for `.claude/reports/<slug>-report.md` (what `piv-implement` writes, where `<slug>` is the plan's slug).
   - **Exists:** extend that file in place. Keep its existing sections; append only the sections below that it
     does not already have, and reconcile anything it already covers (its `Deviations from the plan` is the same
     information as `Divergences from Plan`; expand it to the structured form rather than duplicating it).
   - **Does not exist:** write a new file to `.claude/execution-reports/[feature-name].md`.
2. Either way, print the final path. `system-evolution-review` reads from both locations.

## Report sections

Fill every bracket from evidence in this session (the plan file, the diff, the commands you actually ran). Do
not fill a result from memory: a check you did not run in this session is `NOT RUN`, not a guess.

### Meta Information

- Plan file: [path to plan that guided this implementation]
- Files added: [list with paths]
- Files modified: [list with paths]
- Lines changed: +X -Y (from `git diff --stat` against the base branch — detect it: `git symbolic-ref refs/remotes/origin/HEAD`, else `git remote show origin`, else `main` or `master` if
that branch exists locally (`git rev-parse --verify --quiet <name>`), else ask the user — or, unattended, write
"base branch not found" instead of a number)

### Validation results

One of `PASS | FAIL | NOT RUN` per line, with the command used. Never record a pass you did not observe.

- Syntax & Linting: [PASS | FAIL | NOT RUN] — `[command]` [details if failed]
- Type Checking: [PASS | FAIL | NOT RUN] — `[command]` [details if failed]
- Unit Tests: [PASS | FAIL | NOT RUN] — `[command]` [X passed, Y failed]
- Integration Tests: [PASS | FAIL | NOT RUN] — `[command]` [X passed, Y failed]

### What Went Well

List specific things that worked smoothly:

- [concrete examples]

### Challenges Encountered

List specific difficulties:

- [what was difficult and why]

### Divergences from Plan

For each divergence, document:

**[Divergence Title]**

- Planned: [what the plan specified]
- Actual: [what was implemented instead]
- Reason: [why this divergence occurred]
- Type: [Better approach found | Plan assumption wrong | Security concern | Performance issue | Other]

Write "none" if the implementation followed the plan.

### Skipped Items

List anything from the plan that was not implemented:

- [what was skipped]
- Reason: [why it was skipped]

### Recommendations

Based on this implementation, what should change for next time?

- Plan skill improvements: [suggestions]
- Execute skill improvements: [suggestions]
- CLAUDE.md additions: [suggestions]
