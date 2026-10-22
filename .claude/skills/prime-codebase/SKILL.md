---
name: prime-codebase
description: Orients the agent in a codebase before planning or implementing: bounded structure map, core docs, key files, git state. Use at session start or when asked to "prime" or "load context". Optionally loads Jira issues and Confluence pages first.
argument-hint: "[ticket keys/URLs] [doc page ids/URLs]"
---

# Prime: Load Project Context

## Objective

Build a working understanding of the codebase — structure, documentation, key files, current state — loading only what orientation needs. If `$ARGUMENTS` names external task references, load them first so the analysis is anchored to the actual work.

`$ARGUMENTS` (all optional): task references, space- or comma-separated. Recognized forms, each with where it is
fetched from:

| Reference | Example | Fetch with |
|---|---|---|
| Jira issue key or URL | `ACC-2`, `https://x.atlassian.net/browse/ACC-2` | Atlassian/Jira MCP "get issue" (cloud id first if the server needs one; markdown where offered) |
| Confluence page id or URL | `123456`, `https://x.atlassian.net/wiki/.../pages/123456/...` | Atlassian MCP "get page" |
| GitHub issue or PR | `owner/repo#12`, `#12`, a `github.com/.../issues/12` or `/pull/12` URL | `gh issue view <ref>` / `gh pr view <ref>` |
| Linear issue URL | `https://linear.app/<team>/issue/ENG-12/...` | a Linear MCP "get issue" tool |
| Notion page URL | `https://www.notion.so/...` | a Notion MCP "fetch" tool |

A bare `KEY-n` is a Jira key unless only a Linear tool is connected; if both are, ask. Anything else: say you do
not recognize it and ask what it is.

## Process

### Step 0: Load External Context

**Run this step BEFORE the codebase analysis.** If `$ARGUMENTS` is empty, skip to Step 1.

- **Tickets** (Jira, GitHub, Linear): fetch each with the tool in the table above. Treat summary, description, and acceptance criteria as the task context for everything that follows.
- **Pages** (Confluence, Notion): fetch each the same way. Treat the content as supporting context (specs, design docs, requirements).
- **No tool reaches it**: say so and ask the user to paste the text. Never guess at what a ticket or page says.

Briefly summarize any external context loaded before continuing — this frames the rest of the priming.

### 1. Map the Structure (bounded)

Tracked file count:
!`git ls-files | wc -l`

Top-level entries:
!`git ls-tree --name-only HEAD`

Directories to depth 2 (first 150):
!`git ls-tree -r -d --name-only HEAD | cut -d/ -f1-2 | sort -u | head -150`

That is all the structure that loads automatically — do **not** list every tracked file. Drill in only where the task needs it: `git ls-files -- <dir> | head -100`. `tree -L 3 -I 'node_modules|__pycache__|.git|dist|build' <dir>` is a readable view of one subtree where `tree` exists (not on Windows or minimal images); the git commands need nothing beyond git.

In a monorepo (several apps/packages at depth 2), pick the package the task touches — from Step 0 context, or ask; in a non-interactive run (e.g. invoked by
`piv-run-full-loop`) take the package the feature description names, else the largest, and say so — and focus the
remaining steps there.

### 2. Read Core Documentation

- The project rules file (CLAUDE.md, AGENTS.md or similar) — skip if already in your context
- README files at project root and major directories
- Any architecture documentation

### 3. Identify Key Files

Based on the structure, identify and read a few representative files, not whole directories:
- Main entry points (main.py, index.ts, app.py, cmd/, etc.)
- Core configuration files (pyproject.toml, package.json, tsconfig.json, go.mod, Cargo.toml, etc.)
- Key model/schema definitions
- Important service or controller files

### 4. Understand Current State

Check recent activity:
!`git log -10 --oneline`

Check current branch and status (first 30 lines):
!`git status -sb | head -30`

## Output Report

Provide a concise summary covering:

### External Task Context (if loaded)
- Ticket(s) (Jira/Linear/GitHub): key, title, one-line goal, acceptance criteria
- Doc page(s) (Confluence/Notion): title and what they specify

### Project Overview
- Purpose and type of application
- Primary technologies and frameworks
- Current version/state

### Architecture
- Overall structure and organization
- Key architectural patterns identified
- Important directories and their purposes

### Tech Stack
- Languages and versions
- Frameworks and major libraries
- Build tools and package managers
- Testing frameworks

### Core Principles
- Code style and conventions observed
- Documentation standards
- Testing approach

### Current State
- Active branch
- Recent changes or development focus
- Any immediate observations or concerns

Report only what you read or ran; label anything inferred from file names as an inference.

**Make this summary easy to scan - use bullet points and clear headers.**
