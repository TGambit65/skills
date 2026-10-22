---
name: prime-frontend
description: Primes the agent on the frontend only (components, routing, state, styling), not the backend. Use at session start for UI or client-side work ("prime the frontend"). Optionally loads Jira/Confluence context first.
argument-hint: "[ticket keys/URLs] [doc page ids/URLs]"
---

# Prime Frontend: Load Frontend Context

## Objective

Build targeted understanding of the frontend — structure, components, conventions — keeping the context window light on full-stack codebases. This is `prime-codebase` scoped to the frontend: Step 0 and the report discipline are identical; below is only what differs. Do **not** also run `prime-codebase` — its whole-repo map is the context this skill exists to avoid.

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

As in `prime-codebase`, BEFORE the codebase analysis. If `$ARGUMENTS` is empty, skip to Step 1. Otherwise fetch each reference with the tool the table above names. Tickets are the task context for everything that follows; pages are supporting context. No tool reaches it → say so and ask for a paste; never guess. Summarize what was loaded in a few lines.

### 1. Locate the Frontend

Only the repo outline loads automatically:

!`git ls-files | wc -l`

!`git ls-tree --name-only HEAD`

Directories to depth 3 (first 150), so a nested root such as `apps/web` or `packages/ui` is visible:

!`git ls-tree -r -d --name-only HEAD | cut -d/ -f1-3 | sort -u | head -150`

Common frontend roots: `frontend/`, `client/`, `web/`, `src/` (frontend-only project), `app/` (Next.js), or a package under `apps/`/`packages/` in a monorepo. Pick the root from the outline and Step 0 context; if several fit, ask. Then list only that root, bounded:

```bash
git ls-tree -r -d --name-only HEAD <frontend-root> | cut -d/ -f1-4 | sort -u | head -150   # directories, a few levels
git ls-files -- <frontend-root>/<subdir> | head -100                                # drill in only where needed
```

Never run a bare `git ls-files` or `tree` over the whole repository. (`tree -L 3 <frontend-root>` is fine where `tree` exists — not on Windows or minimal images.)

### 2. Read Frontend Documentation

- The project rules file (CLAUDE.md, AGENTS.md or similar) — skip if already in your context
- Any README inside the frontend root
- `.claude/references/frontend-component-best-practices.md` if it exists — it contains project-specific component conventions

### 3. Identify Key Frontend Files

Based on the structure, read a few representative files, not whole directories:

- Main entry point (`main.tsx`, `index.tsx`, `app/layout.tsx`, `pages/_app.tsx`, `main.ts` for Vue/Angular, etc.)
- Routing configuration (`router.tsx`, `routes.ts`, `app/` directory for Next.js, `pages/` for Nuxt)
- Global state setup (store, context providers)
- Shared component library root (`components/`, `ui/`)
- Core configuration (`package.json`, `tsconfig.json`, `vite.config.ts`, `next.config.ts`)
- One or two representative feature components to internalize the established patterns

Skip files outside the frontend root unless they define a shared type or contract the frontend depends on.

### 4. Understand Current Frontend State

!`git log -10 --oneline`

!`git status -sb | head -30`

Once the root is known, also `git log -10 --oneline -- <frontend-root>` for frontend-only history.

Note any open changes in the frontend directory.

## Output Report

Provide a concise summary covering:

### External Task Context (if loaded)
- Ticket(s) (Jira/Linear/GitHub): key, title, one-line goal, acceptance criteria
- Doc page(s) (Confluence/Notion): title and what they specify

### Frontend Overview
- Framework and major libraries (React, Vue, Svelte, Next.js, Tailwind, etc.)
- Component patterns observed (atomic design, feature folders, etc.)
- State management approach

### Directory Map
- Frontend root and key sub-directories with one-line purpose each

### Conventions
- Naming conventions, file co-location rules
- Styling approach
- Testing framework and conventions observed

### Current State
- Active branch, recent frontend changes
- Any immediate concerns (missing types, deprecated patterns, etc.)

Report only what you read or ran; label anything inferred from file names as an inference.

**Make this summary easy to scan - use bullet points and clear headers.**
