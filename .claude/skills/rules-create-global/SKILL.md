---
name: rules-create-global
description: "Derives a lean root CLAUDE.md or AGENTS.md from an architecture doc (greenfield) or the primed codebase / a codebase-analysis doc (brownfield), backing up any existing rules file first. The customizable /init. Use when the user says \"create CLAUDE.md\", \"set up project rules\", \"derive our global rules\", onboards a codebase, or invokes /rules-create-global."
argument-hint: "[prd-path] [architecture-path]  (greenfield; brownfield: blank + prime first, or pass a codebase-analysis)"
arguments: [path1, path2]
---

# Create Rules: Set Up Your Project's Global Rules

## Inputs and lane

Up to two optional paths: `$path1` and `$path2`. Classify each **by its content**, not its position, then pick the
lane from what was passed **and** what is on disk:

| You were given... | Lane | Rules derive from |
|---|---|---|
| an **architecture / spec doc** (the *how*, from `plan-architecture`; may be the PRD's own `## Architecture` section) | greenfield | the architecture decisions — *what should be* |
| a **PRD** only (intent, what/why, from `plan-create-prd`) | depends | product context for "what this is", **never** technical rules. Bare scaffold → ask for the architecture doc, or settle it now with `plan-architecture`. Existing code → brownfield, PRD kept as context |
| a **codebase-analysis doc** (a saved `prime-codebase` report, or any file:line-cited analysis of the repo) | brownfield | the doc, with its file:line citations — *what is* |
| **nothing** | depends | existing code → brownfield: the codebase primed in this conversation (not primed? run **`/prime-codebase`** first, or offer to). **Bare scaffold with no real code → greenfield:** ask for the architecture doc, or settle the decisions now with `plan-architecture` first — never derive rules from an empty tree |
| an architecture doc **and** an existing codebase (an extension) | brownfield | the code for everything that exists; the doc only for the new seams, labelled as decided, not observed |

Never invent rules from nothing: rules come from technical decisions or real files — a product spec is context,
not a source.

## Protect existing rules — this skill does it

Before writing anything, check for `CLAUDE.md` / `AGENTS.md` at the root (and the target package, in a monorepo):

- **Exists** → read it first and treat it as the starting point, then copy it to `<file>.bak` (if that exists,
  `<file>.<YYYYMMDD-HHMM>.bak`) and tell the user the backup path. **Never overwrite a rules file without a
  backup written first**; if the copy fails, stop and ask.
- **Which file to write:** `CLAUDE.md` only → write it. `AGENTS.md` only, or `CLAUDE.md` is just `@AGENTS.md` →
  write `AGENTS.md` (one source of truth). Neither → `CLAUDE.md` for a Claude-Code-only project, `AGENTS.md` if
  the team is multi-tool.
- Read the matching guidance rather than a snapshot: `CLAUDE.md` → https://code.claude.com/docs/en/memory and
  https://code.claude.com/docs/en/best-practices · `AGENTS.md` → https://agents.md. Everything below says "your
  rules file".

## What earns the always-on slot

Your rules file is read on every task. Four kinds of content earn that slot:

1. **A map of the codebase** — the dirs/files that matter, each with a one-line *what it is + why it lives there*.
2. **Ground rules** — the *specific conventions* this project follows (how you do type safety, your error
   philosophy, your git workflow). State the choice, not a slogan.
3. **Commands the agent runs itself** — the real lint / type-check / test / tooling CLIs with their flags. (Not
   slash-commands — those are skills.)
4. **Working principles (agent steering)** — how you want the agent to *operate* here: reasoning posture (plan
   before non-trivial work, ask when ambiguous, keep scope tight) and the engineering primitives you hold (fail
   fast, explicit errors, single responsibility, simplest thing that works). **These are elicited, not derived**:
   **ask the user**, and keep only the ones that actually change behavior and reflect *their* stance, not a
   lecture the model already follows.

Sort every candidate line into one of four destinations:

- **Keep always-on** → map / ground rules / working principles — true project-wide, every task.
- **Push to on-demand** → recurring but task-*type*-specific → `.claude/references/<topic>.md` (or wherever your
  tool looks — `.agent/`, etc.) or a skill.
- **Move to a plan** → task-specific "what to build next" → it was never a rule.
- **Delete** → redundant, or a slogan the model already follows.

**Brownfield = "what is", not "what should be":** every rule points to the file that proves it; if it can't,
leave it out. **Lean:** no magic line count; the test is in step 5.

## Workflow

### 1. Read the inputs
- **Greenfield:** read the architecture / spec doc (`$path2`, or `$path1` if that is where the decisions live):
  stack, patterns, directory structure, conventions, security choices, plus any scaffold files.
- **Brownfield:** derive from the primed codebase, or from the `codebase-analysis.md` passed in. Spot-check the
  actual code either way. This skill does **not** explore the codebase for you.

### 2. Derive the root rules file
Fill these sections from the input. Don't dump the PRD or the analysis in — link to them.
- **What this is** — one paragraph + the stack in one line.
- **Architecture map** — the tree of dirs/files that matter, one-line what/why each.
- **Ground rules** — the specific conventions (greenfield: decided in the architecture spec; brownfield:
  observed in the code, each traceable to a file).
- **Working principles (agent steering)** — **ask the user** now (see above); state the project's actual stance,
  lean.
- **Commands** — the few you actually run (install / test / type-check / lint / run).
- **On-demand pointers** — where detail loads when needed.

### 3. Extract on-demand context
Pull recurring, task-type-specific patterns out into `.claude/references/<topic>.md` **stubs** (a paragraph each,
not full docs). Test: *does it recur every time you touch that area?* → guide. One-off → leave in the source doc.

### 4. Find the seams
Add a short **"where new code goes"** section — the interfaces/folders where new work plugs in. (Greenfield: the seams are *designed* from the architecture, not
discovered.)

### 5. Prune to lean
Delete generic advice, restated defaults, and anything that can't point to its
evidence. Per line: *would removing this cause a mistake? If not, cut it.*

### 6. Check, then report
Before reporting, confirm each of these against the file you wrote; fix anything that fails:
- it is a **map + ground rules + working principles**, not documentation or a PRD/analysis copy;
- every ground rule is a **specific choice** (brownfield: traceable to a file) — no slogans;
- the working-principles section was **elicited from the user**, lean and behavior-changing;
- recurring task-type detail lives in `.claude/references/`, not always-on;
- nothing is left that wouldn't cause a mistake if removed.

Then report: files created/changed (including the backup path), a 3–5 line summary of what went into the rules
file and why, what was pushed to on-demand context (and where), and the next step — start the first PIV loop.

## Notes

- Rules **evolve** — revisit after the project grows and after major model releases, and run
  `/rules-check-drift` before merges so the map never drifts.
