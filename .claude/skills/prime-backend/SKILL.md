---
name: prime-backend
description: Primes the agent on the backend only (API routes, services, data models, database), not the frontend. Use at session start for work on endpoints, business logic or data access ("prime the backend"). Optionally loads Jira/Confluence context first.
argument-hint: "[ticket keys/URLs] [doc page ids/URLs]"
---

# Prime Backend: Load Backend Context

## Objective

Build targeted understanding of the backend — structure, routes, services, data layer — keeping the context window light on full-stack codebases. This is `prime-codebase` scoped to the backend: Step 0 and the report discipline are identical; below is only what differs. Do **not** also run `prime-codebase` — its whole-repo map is the context this skill exists to avoid.

`$ARGUMENTS` (all optional): Jira issue keys (`ACC-2` or comma-separated `ACC-2,ACC-3`) and/or numeric Confluence page ids.

## Process

### Step 0: Load External Context

As in `prime-codebase`, BEFORE the codebase analysis. If `$ARGUMENTS` is empty, skip to Step 1. Otherwise fetch each Jira issue / Confluence page via your Atlassian/Jira MCP tools (a "get issue" / "get page" tool; cloud id first if the server needs one; markdown where offered). Issues are the task context for everything that follows; pages are supporting context. No Atlassian tool → say so and ask for a paste; never guess. Summarize what was loaded in a few lines.

### 1. Locate the Backend

Only the repo outline loads automatically:

!`git ls-files | wc -l`

!`git ls-tree --name-only HEAD`

Common backend roots: `backend/`, `server/`, `api/`, `app/` (FastAPI/Django), `src/` (backend-only project), or a package under `apps/`/`packages/`/`services/` in a monorepo. Pick the root from the outline and Step 0 context; if several fit, ask. Then list only that root, bounded:

```bash
git ls-tree -r -d --name-only HEAD <backend-root> | cut -d/ -f1-4 | sort -u | head -150   # directories, a few levels
git ls-files -- <backend-root>/<subdir> | head -100                                 # drill in only where needed
```

Never run a bare `git ls-files` or `tree` over the whole repository. (`tree -L 3 <backend-root>` is fine where `tree` exists — not on Windows or minimal images.)

### 2. Read Backend Documentation

- The project rules file (CLAUDE.md, AGENTS.md or similar) — skip if already in your context
- Any README inside the backend root
- `.claude/references/backend-api-best-practices.md` if it exists — it contains project-specific API conventions

### 3. Identify Key Backend Files

Based on the structure, read a few representative files, not whole directories:

- Main entry point (`main.py`, `app.py`, `server.ts`, `index.ts`, `main.go`, etc.)
- Route registration / router index (`routes/`, `api/`, `routers/`, `controllers/`)
- Core configuration (`pyproject.toml`, `package.json`, `tsconfig.json`, `go.mod`, etc.)
- Database configuration and ORM setup (`database.py`, `db.ts`, `alembic.ini`, `prisma/schema.prisma`, etc.)
- Core data models or schemas (`models/`, `schemas/`, `entities/`)
- One or two representative feature slices (route + service + model) to internalize established patterns
- Middleware and dependency injection setup

Skip files outside the backend root unless they define a shared type or contract the backend exposes.

### 4. Understand Current Backend State

!`git log -10 --oneline`

!`git status -sb | head -30`

Once the root is known, also `git log -10 --oneline -- <backend-root>` for backend-only history.

Note any open migrations, pending schema changes, or in-progress API changes.

## Output Report

Provide a concise summary covering:

### External Task Context (if loaded)
- Ticket(s) (Jira/Linear/GitHub): key, title, one-line goal, acceptance criteria
- Doc page(s) (Confluence/Notion): title and what they specify

### Backend Overview
- Framework and major libraries (FastAPI, Django, Express, NestJS, Spring, etc.)
- Language and runtime version
- Database and ORM (PostgreSQL + SQLAlchemy, MongoDB + Mongoose, etc.)

### Directory Map
- Backend root and key sub-directories with one-line purpose each

### Architecture Patterns
- How routes, services, and data access are layered
- Dependency injection or middleware patterns observed
- Error handling approach

### Conventions
- Naming conventions, module organization
- Migration tooling and current migration state
- Testing framework and conventions observed

### Current State
- Active branch, recent backend changes
- Any pending migrations or schema changes
- Any immediate concerns (missing validation, unhandled errors, etc.)

Report only what you read or ran; label anything inferred from file names as an inference.

**Make this summary easy to scan - use bullet points and clear headers.**
