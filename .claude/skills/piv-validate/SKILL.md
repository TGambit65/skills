---
name: piv-validate
description: Runs the project's tests, type checks and lint and returns one PASS/FAIL verdict. Use before committing or opening a PR to confirm zero regressions. Use before committing, before opening a PR, or after finishing a chunk of work.
---

# Validate

Run every check this project has and report a single PASS/FAIL verdict.

## Where the commands come from

This is the one skill that cannot be generic: it wraps your stack's CLIs. Take the commands from the
**first** of these sources that has any, use only that source, and name it in the report:

1. **`.claude/references/conventions.md`, its `## validate` section.** One line per check:

   ```markdown
   ## validate
   - tests: `uv run pytest -q`
   - types: `uv run mypy`
   - lint: `uv run ruff check .`
   - smoke (optional): `./scripts/smoke.sh`
   ```

   Every listed check is required unless it says `(optional)`, and the list is the whole checker: a kind
   of check it leaves out is not required. Commands run from the repo root unless they `cd`. This is the
   route that works for every install, including the plugin, whose copy of this file is read-only.
2. **The command blocks below, once edited.** A copy installed as files can paste its commands into
   steps 1–5 instead. A block still holding its `REPLACE` placeholder is not a source.
3. **`CLAUDE.md`, then `AGENTS.md`**, only for a command it states verbatim as the project's test,
   type-check or lint command. Never infer one from a manifest, a CI file or the README. When both state
   a command for the same check and they differ, use `CLAUDE.md`'s and note the conflict in the report.

No source → do not guess a command. Report every check as `NOT RUN — piv-validate not configured`,
and say in the verdict how to configure it (source 1 above).

> **Three things to get right, because they are the usual reason a checker silently lies:**
> 1. **Working directory.** Many tools only discover their config from the current directory. If your
>    config lives in `backend/pyproject.toml`, the command is `cd backend && uv run pytest`, not
>    `uv run pytest` from the repo root.
> 2. **Cross-platform.** Avoid POSIX-only idioms if anyone on the team is on Windows — `lsof`,
>    `python3`, and background-then-`kill` are the common offenders.
> 3. **Lint your code, not the installed skills.** Skills installed as files put their own scripts under
>    `.claude/skills/`, and a repo-wide lint (`ruff check .`, `eslint .`) fails on them. Exclude `.claude/`
>    in the linter's config (for ruff, `extend-exclude = [".claude"]`) rather than narrowing the command.

Run the checks in order. Keep going after a failure so the report covers everything, and capture the
output of any command that fails or cannot run.

This skill asks nothing and is safe in a non-interactive run.

## 1. Tests

```bash
# REPLACE: your test command, run from the right directory
<your test command>
```

**Expected:** all tests pass.

## 2. Type check

```bash
# REPLACE: e.g. mypy, tsc --noEmit, go vet
<your type-check command>
```

**Expected:** no type errors.

## 3. Lint / format check

```bash
# REPLACE: e.g. ruff check, biome check, eslint
<your lint command>
```

**Expected:** clean.

## 4. Repeat per surface

A full-stack project has more than one of each. Add a section per surface — backend tests, backend
types, backend lint, frontend tests, frontend types, frontend lint — so a single command covers the
whole repo.

## 5. Optional — live smoke test

Only when the change touches routing, middleware, or startup; skip it when your test suite already
exercises the app in-process.

```bash
# REPLACE: start your app, hit one endpoint, confirm the status code, stop it
<your run command>
```

Prefer starting the server in a second shell over backgrounding and killing it from inside this
skill — the background-and-kill idiom is not portable.

## 6. Summary report

Start with the source the commands came from (`conventions.md`, `this skill`, `CLAUDE.md`, `AGENTS.md`,
or `none`). Then report each check with one of three statuses, and an overall verdict:

- **PASS** — the command ran and met its *Expected* line (for a `conventions.md` or `CLAUDE.md` command:
  it exited 0 and its output reports no failures).
- **FAIL** — the command ran and did not. Include the failing command and the relevant output.
- **NOT RUN** — the command did not run to a result: tool missing, wrong directory, placeholder never
  replaced or no source at all, timeout, or an optional check skipped by its own rule. Include the reason (and the error).
  A check that could not run is reported as NOT RUN, never as a pass.

Then:

- One line per check, with a pasted excerpt of the real output (counts), not a paraphrase
- **Overall: PASS** only when every required check is PASS. Any FAIL, or any required check NOT RUN,
  makes it **Overall: FAIL** — name which. An optional check skipped by its own rule does not block PASS.

Do not fix anything here — this skill reports; fixing is a separate step.

## Notes

- Keep this skill fast. It runs before every commit; if a step gets slow, that is a signal to fix the
  slow step, not to drop it from the checker.
- A checker that cannot fail is worthless. Once your commands are wired in, break something on
  purpose and confirm this skill reports FAIL.
