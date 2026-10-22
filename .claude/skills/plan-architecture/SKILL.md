---
name: plan-architecture
description: Interactive session deciding HOW to build a PRD, epic, brief, or idea: a CTO/staff-engineer advisor asks questions, proposes 2–3 approaches with trade-offs, recommends stack, data shape and boundaries, and flags spikes for risky calls. Writes a high-level architecture decision doc (tracker page linked to the epic, Architecture section in the PRD, or architecture.md), not a per-ticket plan (piv-plan-implementation). Needs a human in the loop.
argument-hint: "[path to PRD / epic / brief — or free-form idea] · [optional: paths to reference docs to ground in]"
---

# Architect: Explore the Approach, Decide the Architecture

**Input intent**: $ARGUMENTS — a PRD, an epic, a brief, or a free-form idea. If it is a tracker reference (a
Confluence / Jira / Linear / GitHub URL or key), fetch it from the source first, with whatever tool reaches that
tracker (e.g. the Atlassian MCP for Jira/Confluence).

**Reference docs (optional):** if any paths were passed alongside the intent — API docs, product/engineering
docs, ADRs, prior research, a competitor teardown, a wiki page — **read them first.** If none were passed, **ask
whether any exist** before you start.

## What this skill is

This skill decides **how to approach** the intent: the eng-lead-level calls it left open. **It is a high-level
decision doc, not an implementation plan.** The per-ticket, task-by-task plan comes later with
`piv-plan-implementation`. If you start listing file edits or step-by-step tasks, you've gone too deep — pull
back up to the decisions.

## Interactive only — not for non-interactive runs

The conversation **is** the deliverable. Don't one-shot a document. Run this loop, out loud, with the user:

```
investigate → surface 2–3 options with trade-offs → recommend + reasoning → ask → wait for their call → go deeper
```

Ask sharp clarifying questions whenever the intent or the user's goals are unclear. Never converge on a single
answer silently. If the caller says the run is unattended (`piv-run-full-loop`, a factory, a scheduled job), stop and say so rather than deciding alone
rather than deciding alone.

## Your role

A pragmatic **CTO / staff-engineer advisor**. You **propose, you don't dictate.** Optimize for:

- **The user's goals** — keep pulling every option back to what the user (and their users) actually need.
- **Familiarity** — a stack they know beats a "better" one they don't, especially for a first version.
- **Leanness** — decide only what's needed to move forward; don't over-architect.
- **Reversibility** — cheap, reversible calls don't need deliberation; spend the thinking on the expensive ones.
- **More than one option** — a good problem has >1 viable answer. Show the alternatives, then recommend.

## Greenfield vs brownfield (branch on the input)

**Know which mode you're in first.** Infer it from the input and the workspace — a PRD with no real codebase yet
= greenfield; an epic/brief on a product with a codebase = brownfield. Genuinely unclear? **Ask** ("Is this a
brand-new build, or building on an existing codebase?"). It changes how you explore:

- **Greenfield**: explore the *solution space* — approaches, the web for current best practices and stack
  options, first principles.
- **Brownfield**: explore *how this lands in the existing system* — where it plugs in, what it reuses, what it
  must not break. **Exploring the codebase is your first move** — read the relevant surfaces yourself; a prior
  `prime-codebase` is optional. Keep the read high-level, not a file-by-file audit.

## What to explore (interactively)

Work through these *with* the user, running the loop above. They map one-to-one onto the sections of the output
doc:

- **Approaches** — 2–3 genuinely different ways to solve it, from different angles, with trade-offs.
- **Key decisions** — the calls an engineering lead owns *before* implementation:
  - **Stack & libraries** — what to build it with, and *why* (fit, maturity, familiarity) — with alternatives.
  - **Data model** — the main entities, their relationships, and how they're stored — the shape, not columns
    and migrations.
  - **Boundaries & contracts** — security/auth posture, secrets, external services, the major API/integration
    boundaries the new work crosses — flag these, don't gloss them.
  - **Other** — key patterns, a major build-vs-buy, a significant trade-off. The shape, not the task list.
- **First principles** — what fundamentally has to be true for this to work.
- **Missing pieces** — what doesn't exist yet that the chosen approach needs.
- **Spikes & experiments** — anything uncertain or expensive-to-reverse → recommend a small spike to learn
  *before* committing, rather than guessing:

  ```
  Question:      [what we're unsure about]
  Spike:         [the smallest thing we can build or test to learn] over [timebox]
  Decision rule: go with [X] if [signal] / [Y] if [counter-signal]
  ```

  Reversible, low-cost calls → just decide and move on.

Skip what doesn't apply — and say so, don't silently omit it.

## The output: a high-level architecture decision doc

Only after the calls are made — and **ask the user where it should live before you write anything.** If the
intent lives in a **tracker** (a Confluence/Jira epic, a Linear project, a GitHub issue), the strong default is a
**separate page linked to the epic, both ways**, so `piv-slice-epic` and `piv-plan-implementation` can read
intent and architecture separately later. The options:

- **A separate linked page in your tracker** (recommended when the epic lives there): create it as a child of
  the epic and link both ways, with the tracker's tool (e.g. the Atlassian MCP for Confluence/Jira). Confirm the
  space/parent — and that you may edit the epic to add the back-link — before creating anything.
- **Folded into the PRD/epic**: add an `## Architecture` section so intent and approach travel together (fine for
  a local PRD or a solo/greenfield doc with no tracker). If one already exists, show the change and ask before
  replacing it.
- **A standalone `architecture.md`**: a local repo doc when there's no tracker — beside the PRD (`docs/` if it
  exists, else the repo root). Don't overwrite an existing one without asking.

Either way keep it high-level and fill this shape:

```markdown
# Architecture — <intent name>

## Problem & goals
One paragraph: the user goal this serves (from the intent) — the lens every decision below is judged against.

## Approaches considered
The 2–3 directions weighed, each with its trade-offs — and which one we recommend, and why.

## Recommended approach
The chosen direction in a few sentences — the shape of the solution, not the task list.
(Brownfield: where it plugs into the existing system and what it reuses, at a high level.)

## Key decisions
The eng-lead-level calls made here, *before* the implementation plan:
- **Stack & libraries** — what, and why (with the alternatives considered).
- **Data model** — the main entities/relationships and storage, at the shape level.
- **Boundaries & contracts** — security/auth posture, secrets, external services, major API/integration boundaries.
- **Other** — any further architectural decision worth recording (key pattern, build-vs-buy, major trade-off).
- (skip any that don't apply — note that you did)

## Missing pieces
What has to exist that doesn't yet — the building blocks this approach depends on.

## Spikes & experiments
The uncertain / expensive calls to de-risk first, each with its decision rule.

## Open questions
Decisions deliberately deferred — named, not hidden — and what would settle each.
```

## After this

Confirm where you wrote it, summarize the recommended approach + the key calls in a few lines, then offer the
natural next moves and let the user pick — **don't force a pipeline**:

- **Slice it into tickets** — feed the doc to `piv-slice-epic` to break the epic into PIV-sized tickets and
  create them (GitHub issues, Jira tickets, or a local file).
- **Keep going here** — refine the decisions, or create the tickets directly (show the list, get a yes first).
- **Small epic? Plan it in one go** — skip slicing and go straight to `piv-plan-implementation`.
- **Spike something now** — if an open risk is blocking, go build the spike/experiment we flagged.
- Durable conventions this surfaced → `rules-create-global` / `rules-check-drift`.

## Success criteria

Check each before handing off; don't tick what you didn't check:

- [ ] **Ran as a conversation** — the user weighed in on the options before anything was written.
- [ ] **More than one approach explored** — not one foregone conclusion; recommended with reasoning.
- [ ] **Stack & libraries recommended with the *why*** and the alternatives.
- [ ] **High-level, not a task plan** — no file-by-file edits or step lists (that's `piv-plan-implementation`).
- [ ] **Risky / one-way calls get a spike**, not a guess.
- [ ] **Stays anchored to the user's goals.**
