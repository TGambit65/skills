---
name: piv-slice-epic
description: Slices an epic plus its architecture decisions (or a PRD if greenfield) into AI-sized PIV tickets with per-ticket context and a dependency graph, then creates them in the tracker (Jira, Linear, GitHub…) or docs/tickets/. Use after plan-architecture, before piv-plan-implementation.
argument-hint: "[epic + its linked architecture page (paths or Confluence/Jira URLs); a PRD for greenfield]"
---

# /piv-slice-epic — Slice an Epic into PIV-Sized Tickets

The bridge between a strategic doc and the PIV loop: the epic doc is the destination, the PIV loop is the unit of
motion, **tickets are the bridge.**

**Vs `plan-create-stories`:** that skill turns a bare PRD into a flat, human-sized backlog and needs no
architecture. This one needs the architecture and produces AI-sized tickets with a dependency graph. If you ran
`plan-architecture`, use this.

## Input

`$ARGUMENTS` — the **epic** to slice **and its architecture decisions**, as **one doc or two**: a single
architected epic carrying its own `## Architecture` section, **or** an epic plus a separate, linked architecture
page (the common case — e.g. a Confluence epic page and its linked architecture page, both passed as URLs).
Greenfield: a PRD stands in for the epic. Tracker references (Confluence / Jira / Linear / GitHub URLs or keys)
→ fetch them with whatever tool reaches that tracker (e.g. the Atlassian MCP for Jira/Confluence).

**The architecture is the load-bearing input:** it names the seams, data model, and missing pieces the slices
must respect.

## Process

### Step 1 — Read the sources

Read **both** fully: the epic (goal, user stories, acceptance criteria, out-of-scope) and its architecture
decisions (approach, stack, data model, missing pieces, spikes), fetching the separate page when there is one.
The slicing has to respect those calls.

### Step 2 — Orient on the code surface (if not already primed)

Slicing needs enough codebase awareness to judge what's independent vs dependent — file overlap, shared seams.
**Not prime-dependent:** if the session is already oriented, skip this. Otherwise **explore it yourself — don't
depend on a prior `/prime-codebase`**: starting from the architecture's named seams, data model, and missing
pieces, read the relevant files/dirs (e.g. the adapter interface, the orchestrator, the ingestion pipeline) to see
what exists, what's reused, and where new code lands. Just enough to slice confidently — not a full re-derivation.

### Step 3 — Decompose into PIV-sized slices

Break the epic into tickets. **Scope these for AI, not for a human backlog** — an agent loop carries far more than
a traditional ticket: a small-to-medium implementation *phase*, ~8–10 subtasks, often several hundred to ~1500
lines of change (20–50% tests). A small epic might even be a single ticket. A well-sized ticket:

- Is **one testable concern** — easy to **test, review, and prove** on its own.
- Is one coherent unit — a vertical slice of behavior, not a horizontal layer.
- Has clear acceptance criteria of its own.
- Is small enough that **one focused loop can one-shot it without context rot** — not so large the agent loses
  the thread and returns diminish.

**The binding rule is reviewability, not the line count.** If a slice can't be tested and reviewed in one honest
pass, split it — by **dependency**, by **concern**, or as a **slim end-to-end slice** (prove the whole flow
thinly, then fatten it next loop), whichever makes each ticket easiest to prove. The *planning detail* stays high
regardless — it's the *scope* that's larger.

### Step 4 — Slice for parallelizability

Map dependencies between tickets. **Independent tickets** — ones that don't touch the same files or rely on each
other's output — can run in **parallel worktrees** (see `/worktree-create`). Mark which tickets are independent
and which form a dependency chain. Slicing along vertical-slice-architecture seams maximizes independence.

**Plan just-in-time:** a dependent ticket waits until its dependency is *implemented*, not just sliced — building
the dependency informs the dependent's plan, so planning it early plans against a guess. Independent tickets can
be planned and run in parallel; dependent ones wait their turn.

### Step 5 — Confirm, then write the ticket breakdown

Draft the breakdown in the shape below and **show it to the user — titles, sizes, dependency graph, waves — before
creating anything in a tracker.** Wait for the go-ahead. Then write the tickets to your tracker (Jira, Linear,
GitHub Issues, Notion, Archon's tasks — through its CLI/MCP), linked to or parented under the epic — or to a
local `docs/tickets/<epic-slug>.md` if you're solo or have no tracker (ask before overwriting an existing file).
Either way, **every ticket carries its own context** — that's what lets a loop pick it up later without re-reading
the whole epic:

```
# Ticket Breakdown — <epic name>

## Epic summary — goal in 2-3 lines
## Tickets
   ### TICKET-1 — <title>
   - Scope / acceptance criteria — one testable concern
   - Per-ticket context: the doc sections, guides, and seams this ticket needs
     (e.g. "source-adapter guide · seam: adapter interface · AC #2 + #4 from the epic")
   - Files touched (estimate) · rough size (lines of change incl. tests)
   - Depends on: <none / TICKET-x>
   ### TICKET-2 — ...
## Dependency graph
   <text or mermaid graph showing the order + parallel groups>
## Suggested execution order
   Wave 1 (parallel): TICKET-1, TICKET-3
   Wave 2: TICKET-2 (after TICKET-1 is implemented)
```

After creating in a tracker, replace the `TICKET-n` placeholders in *Depends on* with the real keys/links (and add
the tracker's own blocks/depends-on relation where it has one).

## Output

A ticket breakdown in your tracker (or `docs/tickets/<epic-slug>.md`). Each ticket then enters its own PIV loop:
`/piv-plan-implementation` with the ticket key/URL (or that ticket's section of the local file). It primes what it
needs, so `/prime-codebase` first is optional — the per-ticket context above is what makes that possible.

## Notes

- Issue management is **tool-agnostic**. The tracker doesn't matter; the goal is to **split the work just enough
  that each loop has the highest chance of one-shot success, so you can automate the loop.**
- Greenfield: the same slicing applies to MVP phases instead of epic tickets.
