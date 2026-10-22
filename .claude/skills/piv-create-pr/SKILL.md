---
name: piv-create-pr
description: Pushes the feature branch and opens a pull request with a real body (summary · changes · validation · reviewer notes); returns the URL. Use after a ticket is committed on its own branch.
argument-hint: "[--base <branch>] (default: auto-detected)"
---

# Create PR: Open the Pull Request, Hand Off for Review

This is the **ship** step of the PIV loop: the implementation is committed on a feature branch; now open the PR
so it can be reviewed (by the `piv-review-pr` agentic gate, then a human).

## Phase 0 — Detect the base branch

Don't hardcode `main`. Resolve it:
1. If `$ARGUMENTS` contains `--base <branch>`, use that.
2. Else: `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'`
3. Fallback: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name` (works without `sed`/`awk`,
   e.g. on Windows outside Git Bash), or `git remote show origin 2>/dev/null | grep 'HEAD branch' | awk '{print $NF}'`
4. Last resort: `main` — say so. Store as `{base}`.

## Phase 1 — Validate git state

```bash
git fetch origin                      # so origin/{base} is current before comparing
git branch --show-current
git status --short
git log origin/{base}..HEAD --oneline
```

| State | Action |
|-------|--------|
| On `{base}` | STOP: "Create a feature branch first (the ticket should be on its own branch)." |
| Uncommitted changes (untracked `.claude/code-reviews/` files excepted — those are local review artifacts unless the user chose to commit them) | STOP: "Commit (`piv-commit`) or stash before opening the PR." |
| No commits ahead of `origin/{base}` | STOP: "Nothing to PR." |
| Existing PR for this branch (`gh pr list --head $(git branch --show-current) --json url`) | STOP and print the URL. |
| Clean, commits ahead, no PR | PROCEED |

## Phase 2 — Gather context for the body

- **Project conventions:** if `.claude/references/conventions.md` exists, read its `## pr` section — its rules
  win over the default template below (sections, tone, what must be stated). That file is where a project's
  specifics live; this skill stays general.
- Commits: `git log origin/{base}..HEAD --pretty=format:"- %s"`
- Files: `git diff --stat origin/{base}..HEAD`
- **Implementation report** (if `piv-implement` wrote one — `.claude/reports/<slug>-report.md` (feature branches) or `.claude/reports/issue-<N>-report.md` (fix branches; the `issue-<N>-report.md`): pull the summary,
  its **Validation results**, and the **Deviations from the plan** (these belong in the PR body — they tell the
  reviewer what was intentional). No report → say so in the body; don't invent validation results.
- Linked ticket / issue: look for `ACC-…`, `#123`, `Fixes #…` in the commits/branch name.
- PR template: if `.github/PULL_REQUEST_TEMPLATE.md` exists, fill it; else use the default below.

## Phase 3 — Push and open the PR

```bash
git push -u origin HEAD
```

```bash
gh pr create --base "{base}" --title "{type}: {concise description}" --body "$(cat <<'EOF'
## Summary
{1-2 sentences: what this ticket delivers}

## What changed
{commit summaries}

## Validation
- Tests / type-check / lint: {PASS / FAIL / NOT RUN — from the implementation report or a fresh run; say which}
- Manual check: {what was exercised, or "pending review"}

## Notes for the reviewer
{documented deviations from the plan — intentional decisions — or "none"}

## Linked
{ticket / issue refs, or "none"}

_Ready for review._
EOF
)"
```

(`{type}` = feat/fix/refactor/… from the work. Use `--draft` if the work isn't ready for a real review. The
heredoc is bash; in a shell without it, write the body to a temp file and pass `--body-file <file>`.)

## Output

```bash
gh pr view --json number,url,title,baseRefName,headRefName
```

Report the PR number + URL, the base ← head branches, and **"Ready for review → run `piv-review-pr <number>`, then a
human approves."** This is the handoff point: the agent's loop ends at an open PR; review and merge are the gates.

## Notes

- Tool-agnostic in spirit: this skill uses GitHub (`gh`); the same motion is "open a merge request" on GitLab
  (`glab mr create`), or "mark ready for review" wherever your team works. Solo with no remote? Skip the PR —
  commit on `{base}` and review your own diff (`piv-review-changes`) before moving on.
- Sets up parallel work: one branch per ticket → one PR per ticket is exactly what makes worktree parallelism
  (running independent tickets at once) clean.
