---
name: worktree-create
description: Creates git worktrees under worktrees/<branch>, each on its own branch off the detected base, with gitignored config copied in, dependencies installed, and a health check. Use when the user says "set up worktrees", "create a worktree", "spin up parallel branches", or invokes /worktree-create.
argument-hint: "[branch ...]  (one or more branch names; blank = ask)"
---

# Worktree Create

Stand up **any number** of isolated git worktrees from a list of branches — each created off the right base, given
its gitignored config, its dependencies, and a health check — by fanning out one setup subagent per worktree so
they run in parallel. The per-worktree work is app-agnostic and **detected from the repo**, never hardcoded.

## Input

`$ARGUMENTS` is the list of branches to create.

- **None given** → ask which branches to create (or offer to derive them from the tickets in play). Don't guess.
- **One** → set up a single worktree inline (a fan-out of one is unnecessary).
- **Two or more** → fan out one subagent per branch, in parallel.

## Detect the project setup ONCE, before fanning out

Read `references/worktree-setup.md`, then determine from **this** repo (not from assumptions), one time:

- the **base branch** — the repo's default branch: `git symbolic-ref refs/remotes/origin/HEAD` (strip
  `refs/remotes/origin/` to get `<name>`); if that fails, the `HEAD branch` line of `git remote show origin`.
  Use `origin/<name>` as BASE after a `git fetch origin`, so new branches match the remote; no remote → the
  current branch. Use the current `HEAD` instead only when the user asks to carry in-progress work into the
  worktrees. Never hardcode `main`.
- the **install command(s)** (monorepo → one per package),
- the **gitignored env/config files to copy** (or the repo's `.worktreeinclude`), each confirmed with
  `git check-ignore`,
- the **verification/health-check command** (a health endpoint if the app exposes one, else a build/test smoke —
  prefer whatever CI runs),
- a **base port**, only if the health check starts a service,
- **database isolation**, only if the health check writes to a local database: how the app picks its database
  (a `DATABASE_URL`, a schema or name variable, a SQLite path) so each worktree gets its own — a per-worktree
  database name or file. If no safe per-worktree setting exists, health checks that write to it must not run in
  parallel: run those checks one at a time, or mark them NOT RUN,
- per branch, whether it **already exists** (`git rev-parse --verify --quiet refs/heads/<branch>`), so the
  subagent gets the right create command.

The worktree root is `worktrees/<branch>`; confirm `worktrees/` is gitignored (`git check-ignore worktrees`) and
add it to `.gitignore` if not. If services get started, assign each worktree a distinct port = `base + index` so
parallel servers don't collide.

## Fan out one setup subagent per branch (parallel)

Spawn all subagents at once (the Task tool in Claude Code; elsewhere, the agent's own parallel-subagent mechanism,
or run the branches one after another). Each subagent gets a copy of the prompt below with the UPPERCASE slots
filled in from the detection above — the subagent sees **only this prompt**, not this skill or its references,
so everything it needs must be in it:

```
Set up a git worktree for branch: BRANCH   (assigned port: PORT, only relevant if you start a service)
Database isolation: DB_ISOLATION   (env settings that give this worktree its own database, or NONE)

1. Create the worktree off the base branch BASE:
   - branch does not exist yet:  git worktree add worktrees/BRANCH -b BRANCH BASE
   - branch already exists:      git worktree add worktrees/BRANCH BRANCH
   If git refuses (path already exists, branch checked out elsewhere), stop and report the error. Do not force,
   delete, or rename anything.
2. Copy these gitignored files from the main checkout into worktrees/BRANCH at the same relative paths:
   ENV_FILES
   Run `git check-ignore` on each first and skip any that is not ignored. Never print, cat, echo, or quote the
   contents of these files — not in the health check, not in the report. Names only.
3. Install dependencies inside the worktree:  INSTALL_COMMANDS   (every package, for a monorepo).
4. Run the generate/build step the app needs to boot, if any:  BUILD_COMMAND
5. Verify:  HEALTH_CHECK   (if it starts a service, use PORT and DB_ISOLATION; stop any server you started
   afterwards). If the check writes to a shared database and DB_ISOLATION is NONE, do not run it: report NOT RUN,
   "no per-worktree database".

Report exactly: worktree path · branch · deps installed (yes/no) · health check (PASS / FAIL / NOT RUN — with the reason) · any errors
(error messages only, never file contents).
```

For a single branch, run the same steps directly instead of spawning.

## Aggregate and report

If adding `worktrees/` changed the tracked `.gitignore`, say so and tell the user to commit it (or stash it)
before `worktree-merge`, which requires a clean tracked tree.

Collect the reports and print a per-worktree summary (path · branch · deps · health · port), a combined
`N worktree(s) ready` line, the next step (open each worktree / start a PIV loop in it), and the cleanup reminder:
`git worktree remove worktrees/<branch>` once a branch is merged.

If any worktree failed its health check, surface it clearly and do **not** report it ready. Leave it in place for
inspection and give the removal command.

## Resources

- `references/worktree-setup.md` — what a fresh worktree needs and how to detect each piece per repo. Read it
  before the detection step.
