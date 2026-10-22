---
name: piv-review-pr
description: Reviews an open pull request with fresh eyes: fetches it, runs validation, ranks issues by severity, posts the review to GitHub, saves a report. The agentic gate before a human approves. Use after piv-create-pr.
argument-hint: "<pr-number | pr-url | branch> [--approve | --request-changes]"
---

# Review PR: The Agentic Gate Before the Human

**Input**: $ARGUMENTS

The point of this skill is **fresh eyes**: it reviews the PR in a clean context — *not* the session that wrote
the code, which rationalizes instead of scrutinizing — so **start it in a new session**. It posts its verdict on
the PR, then a **human** makes the final call.

## Phase 1 — Fetch the PR

Resolve the input to a PR number (a number, a URL, or a branch via
`gh pr list --head <branch> --json number -q '.[0].number'`). Then:

```bash
gh pr view {N} --json number,url,title,body,author,headRefName,baseRefName,state,isDraft,additions,deletions,changedFiles,files
gh pr diff {N}
```

**State guard:** `state` is `MERGED`/`CLOSED` → stop ("nothing to review"). `isDraft` true → review direction
only; don't approve/block.

**Dirty-tree guard — before checking out.** `gh pr checkout` switches branches and would carry or clobber local
edits. If `git status --porcelain` lists anything (untracked `.claude/code-reviews/` files excepted), STOP:
"Commit or stash first" — or, if the user prefers, review from `gh pr diff` alone and mark validation `NOT RUN`.
When clean, note the current branch (`git branch --show-current`) so you can say how to get back, then:

```bash
gh pr checkout {N}
```

## Phase 2 — Load the context (so you review against the right bar)

- **`CLAUDE.md`** + any `.claude/references/` — the project's standards are the review rubric.
- **The implementation report** (if `piv-implement` wrote one — `.claude/reports/<slug>-report.md` (feature branches) or `.claude/reports/issue-<N>-report.md` (fix branches; the `issue-<N>-report.md`, where
  `<slug>` is the head branch minus its `feature/` prefix; otherwise list `.claude/reports/` and pick the match)
  + its plan: read the **`## Deviations from the plan`** section. A documented deviation is an *intentional
  decision*, **not** an issue — only flag *undocumented* divergences. (No report? Review normally and note its
  absence.)
- The PR's own intent (title/body): what problem it claims to solve.

## Phase 3 — Run validation

Run the project's real suite (the **`piv-validate`** skill, or the plan's validation commands) — tests,
type-check, lint, build. Record each check as `PASS` / `FAIL` / `NOT RUN` with counts. A red suite is a finding
in itself; a check you could not run is reported as `NOT RUN`, never assumed green.

## Phase 4 — Review the diff

These skills ship no subagents. If the project defines `.claude/agents/code-reviewer.md`, dispatch it for the deep
pass; otherwise dispatch a built-in general-purpose subagent with the same brief; with no subagent mechanism at all,
**do the review yourself, here** (the new-session rule is what keeps the inline pass clean). Either way: review against the project's standards and report **high-confidence issues only** — anything
unconfirmed is listed as `Unverified` and does not drive the verdict. Read every changed file *in full* (not just
the diff). Cover: correctness · type safety · pattern/standards compliance · security · performance · tests
present · maintainability.

**Categorize every issue by severity** (the same table `piv-review-changes` uses):

| Severity | Meaning |
|----------|---------|
| **Critical** | Blocking — security flaw (exploitable or unverified), data loss, crashes |
| **High** | Should fix before merge — type-safety holes, missing error handling, logic errors |
| **Medium** | Pattern inconsistencies, missing edge cases, hardening gaps, *undocumented* deviations from the plan |
| **Low** | Suggestions, minor polish |

Acknowledge what's done well, too — review is constructive, not just a defect list.

## Phase 5 — Decide

- **Approve** — no critical/high issues, validation passes, matches intent.
- **Request changes** — high issues, or fixable validation failures, or any Medium finding the project's standards make blocking.
- **Block** (request-changes, strongly) — critical security/data issues, or wrong fundamental approach.
- Honor an explicit `--approve` / `--request-changes` flag, but never approve over an unresolved critical issue,
  and never approve when validation is `FAIL` or wholly `NOT RUN`.

## Phase 6 — Post to GitHub + save the report

Write the report to `.claude/code-reviews/pr-{N}-review.md` (summary · issues by severity with `file:line` + fix ·
validation table, PASS / FAIL / NOT RUN · what's good · recommendation). **Local artifact:** the review lives on
the PR, so don't commit this file into the PR branch unless the project keeps reviews in-repo (`piv-commit` asks
before staging anything under `.claude/code-reviews/`).

**Self-review check.** GitHub rejects `--approve` and `--request-changes` from the PR's own author — the normal
case when the same account ran `piv-create-pr`. If `gh pr view {N} --json author -q .author.login` equals
`gh api user -q .login` (or `gh pr review` errors with "your own pull request"), post with `gh pr comment` and
put the verdict in the first line (`**Recommendation: APPROVE | REQUEST CHANGES | BLOCK**`). Otherwise:

```bash
# approve
gh pr review {N} --approve --body-file .claude/code-reviews/pr-{N}-review.md
# request changes
gh pr review {N} --request-changes --body-file .claude/code-reviews/pr-{N}-review.md
# comment only (draft PRs / advisory / own PR)
gh pr comment {N} --body-file .claude/code-reviews/pr-{N}-review.md
```

## Output + hand off

Print: PR number/URL · issue counts by severity (+ Unverified) · validation results · the recommendation · how
it was posted (review or comment) · the branch you are on now and the one you came from (`git checkout
<original>` to return). Then hand off: **"Posted on the PR. A human now reviews the code + this review and
merges."** If there are issues, the natural next step is **`piv-fix-review-findings`** on the report (you are
already on the PR branch), then re-run validation and this review.

## Notes

- This is the *agentic* gate; it does not replace the human — it gives the human a validated, triaged PR to
  approve. Going deeper means multiple review agents, tuning the reviewer to your stack, and a validation
  pyramid behind it.
- GitHub-specific (`gh`). On GitLab the same motion is `glab mr view/diff/checkout` and `glab mr note`; adapt
  the commands, keep the phases.
