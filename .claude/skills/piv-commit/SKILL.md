---
name: piv-commit
description: Atomic, conventionally-tagged git commit of the uncommitted work. Use when work is complete and ready to be committed.
---

# Commit: Create a New Commit

Turn the uncommitted work into atomic commits: one logical change per commit, each with a conventional message.

## Process

0. **Read this project's conventions.** If `.claude/references/conventions.md` exists, read its `## commit`
   section and follow it — those rules win over the defaults below. That file is where a project's specifics
   live; this skill stays general.

1. **See what is uncommitted — paths first, contents second.** Run `git status --porcelain --untracked-files=all`
   (tracked and untracked paths, no contents). Nothing listed → say so and stop. Screen those paths against the
   secret list in step 2 **before reading any diff**, so a modified `.env` is never printed. Then read only the
   allowed paths: `git diff HEAD -- <allowed tracked paths>` for tracked changes, and for each allowed untracked
   file a content scan that prints only `file:line`, never the matching text
   (`grep -HnIE '<patterns from step 2>' -- <file> | cut -d: -f1,2`).

2. **Stage deliberately — by explicit path, never `git add -A` / `git add .` blindly.** Screen the paths from
   step 1 first:
   - **Secrets — refuse to stage** unless the user explicitly asks for that exact file: `.env*` (committed
     templates like `.env.example` are fine), `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `credentials*`, `*.p12`,
     `.netrc`. Also scan the allowed diffs and untracked files for secret-looking content
     (`-----BEGIN … PRIVATE KEY-----`, `AKIA…`, `ghp_…`, `sk-…`, long literals assigned to
     `*KEY`/`*TOKEN`/`*SECRET`/`*PASSWORD`). Name the file and stop for it. Never print, cat, echo, grep or quote
     the contents of an env or secret file — not even masked; name the file or the key, never the value.
   - **Junk — leave unstaged** unless explicitly asked: `node_modules/`, `dist/`, `build/`, `__pycache__/`,
     `*.pyc`, `.DS_Store`, `*.log`, coverage output. Suggest a `.gitignore` entry rather than adding one yourself.
   - **Agent-written folders.** Committed **with the work by default**: `.claude/plans/`, `.claude/reports/`,
     `.claude/execution-reports/`, `docs/tickets/`, `docs/issues/` — they document intent and later skills read
     them. **Asked about first, default no**: `.claude/code-reviews/`, `.claude/system-reviews/`, `.claude/scans/`
     — reviews live on the PR, not in the repo. In a non-interactive run, leave the ask-first folders unstaged and
     say so.

3. **One concern per commit.** If the diff mixes unrelated concerns (the feature plus a stray refactor, a
   dependency bump, a config fix), propose a split: list the groups with their files and, once the user agrees,
   stage and commit each group separately with its own message. A file that mixes concerns: say so, then commit
   it under the dominant concern or ask. **Non-interactive mode.** If the caller says the run is unattended (e.g.
   invoked by `piv-run-full-loop`), never stop to ask: make one commit under the dominant concern, list the mixed
   concerns in the body, leave the ask-first folders (step 2) unstaged, and say so.

4. **Write the message.** `<tag>: <atomic description>` — tag is `feat`, `fix`, `docs`, `refactor`, `test`,
   `chore`, etc., reflecting the work; the summary is specific and descriptive; add a body when the *why* isn't
   obvious. Run `git commit` normally — **never `--no-verify`**; if a hook fails, report its output and stop.
   Don't amend, force, or change git identity.

## Output

One commit per logical change, each with a conventional-commit-style message
(`<tag>: <atomic description>`) that accurately reflects the work done.

After the commit(s) succeed, print the hash(es) and two clearly labelled summaries:

### What Changed
One short paragraph (3–6 sentences) describing the feature/fix/refactor that was committed — what problem it solves and what files were the key touch points. Write for a developer skimming the git log.

### AI Layer Changes
Only include this section if any files under `.claude/` were modified or added (CLAUDE.md, `.claude/references/`, `.claude/skills/`, `.claude/agents/`, etc.).

List each changed AI-layer file with a one-line note on what evolved and why. If nothing in `.claude/` changed, omit this section entirely.

Also list anything you deliberately **did not stage** (secrets, junk, un-asked-for review files) and why, so
nothing is silently dropped.
