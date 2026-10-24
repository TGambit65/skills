---
name: piv-run-full-loop
description: "Runs the whole PIV loop unattended from one feature description: prime, plan, implement, validate, review, commit. Use for a hands-off build."
argument-hint: [feature-description]
---

# End-to-End Feature Development

**Feature Description**: $ARGUMENTS

Chains the core PIV-loop skills in order. Invoke each **by name** as your agent invokes skills (`/piv-implement
<args>` in Claude Code, `/skills:piv-implement` under a plugin install) — never by file path; skill locations
differ between project, global and plugin installs.

## Non-interactive contract

The loop runs unattended, so no step may stop and wait for a human. Tell every skill it is running
**non-interactively, invoked by piv-run-full-loop**, and hold it to this:

- **No questions.** Where a skill would normally ask (the clarifying GATE in `piv-plan-implementation`), it
  records each open item as an `Assumed — <assumption>, confirm before execution` line and continues. A silent
  guess is a defect; every assumption appears in the plan and again in the final summary.
- **A red step stops the loop before commit.** Validation FAIL, `piv-implement` Status: PARTIAL (retry cap or
  STOP), or Critical/High review findings → go straight to the Final Summary with where and why. Never commit
  work that is red or unreviewed.
- **Bounded retries only.** The single re-entry allowed is in Step 4. Never loop a step until it goes green.
- **Local only.** The loop ends at a local commit: no push, force-push, rebase, reset or branch deletion, and
  never weaken a test or check to get green.
- **A refused write is a stop.** The plan, report and review live under `.claude/`, which Claude Code protects;
  headless, the `default`, `acceptEdits` and `dontAsk` modes refuse those writes (`auto` sends them to its
  classifier; `bypassPermissions` allows them). Stop at that step and report the refusal; never write
  the file another way, and never move it out of `.claude/`, where the next step reads it.

---

## Step 1: Prime — load codebase context

Run the `prime-codebase` skill.

## Step 2: Plan — create the implementation plan

Run the `piv-plan-implementation` skill, non-interactively, with the feature description: **$ARGUMENTS**.

Record the plan path it reports — `.claude/plans/<feature-name>.md` — and every `Assumed — ` line in its
`OPEN QUESTIONS / ASSUMPTIONS` section. `<feature-name>` is the plan's slug; the next steps key off it.

## Step 3: Implement — build from the plan

Run the `piv-implement` skill with the plan path from Step 2. It writes
`.claude/reports/<feature-name>-report.md`; read its **Status**: `COMPLETE` → continue, `PARTIAL` → stop the loop.

## Step 4: Validate — run the project suite

Run the `piv-validate` skill. Record each check as PASS / FAIL / NOT RUN and the overall verdict.

On an overall FAIL, apply `piv-implement`'s step-4 fix rules to the failing check **once** (fix the code, never
the check; its 3-attempt cap applies; append the outcome to the implementation report), then re-run
`piv-validate`. Still FAIL → stop the loop.

## Step 5: Review — pre-commit technical review

Run the `piv-review-changes` skill. It must **complete and write** `.claude/code-reviews/<name>.md`; a review that
did not run, errored, or left no file is a stop, never "no findings". Any **Critical or High** finding → stop the
loop and point at the review file (the human's next step is `piv-fix-review-findings`). Medium/Low findings go in
the summary and do not block the commit.

## Step 6: Commit — save the work

Reached only when Step 4 is PASS, Step 5 completed and its review file exists, and that review has no
Critical/High finding. Run the `piv-commit` skill.

---

## Final Summary

Fill from actual results. A step that did not run is `NOT RUN`; leave a field blank rather than invent a value.

### Feature Implementation Run

**Original Request**: $ARGUMENTS

**Feature Name**: <feature-name from Step 2>

**Steps executed** (each PASS / FAIL / NOT RUN):

1. Prime: ___
2. Plan: ___ — `.claude/plans/<feature-name>.md`
3. Implement: ___ — `.claude/reports/<feature-name>-report.md`, Status: ___
4. Validate: ___ — per check: ___
5. Review: ___ — `.claude/code-reviews/<name>.md`, findings: Critical _ / High _ / Medium _ / Low _
6. Commit: ___ — hash: ___ (or "not committed: <reason>")

**Stopped early?** <step and reason, or "no">

**Assumptions to confirm**: <copy every `Assumed — ` line from the plan, or "none">

**Outputs:**
- Files created/modified: <list>
- Tests added: <list>

**Next steps:**
- Confirm the assumptions above; amend the plan's `AMENDMENTS` section if any was wrong
- If stopped: fix what stopped it (`piv-fix-review-findings` for review findings), then `piv-validate` →
  `piv-review-changes` (a fresh review of the fixed tree) → `piv-commit`
- If committed: `piv-create-pr` to push and open the PR
- Continue with the next feature
